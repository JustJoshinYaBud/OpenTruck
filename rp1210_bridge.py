"""OpenTruck - RP1210 bridge (runs under a 32-bit Python interpreter).

A 64-bit process cannot load a 32-bit DLL, so adapters whose driver only ships
a 32-bit DLL (e.g. some legacy adapter drivers) are driven by this
small out-of-process helper. The 64-bit `BridgedRP1210Source` spawns this
process and exchanges newline-delimited JSON over stdin/stdout; this process
does the real ctypes calls into the 32-bit DLL.

Built as a standalone 32-bit exe via PyInstaller (see build.bat) and bundled
next to OpenTruck.exe as ``OpenTruckBridge32.exe``.

Protocol (one JSON object per line, both directions):
  -> {"op":"client_connect","dll":"...","device_id":N,"protocol":"..."}
  <- {"rc":R}                       # R<=0 means error
  -> {"op":"send_command","number":N,"data":"<hex or empty>"}
  <- {"rc":R}
  -> {"op":"send_message","data":"<hex>"}
  <- {"rc":R}
  -> {"op":"read_message"}
  <- {"n":N,"raw":"<hex of first N bytes>"}   # N<0 = error (link lost)
  -> {"op":"client_disconnect"}
  <- {"rc":R}
  -> {"op":"shutdown"}
  <- {"ok":true}   (then exits)

The bridge is deliberately J1939-agnostic: it mirrors the raw RP1210 C API 1:1
and leaves TX layout, filters, address-claim and J1708 parsing to the 64-bit
side, which shares that logic with the in-process `RP1210Source`.
"""
import ctypes
import json
import sys
from ctypes import wintypes, c_char, c_short, POINTER


def _bind(dll) -> None:
    dll.RP1210_ClientConnect.restype = c_short
    dll.RP1210_ClientConnect.argtypes = [
        wintypes.HWND, c_short, ctypes.c_char_p, ctypes.c_long, ctypes.c_long, c_short]
    dll.RP1210_ClientDisconnect.restype = c_short
    dll.RP1210_ClientDisconnect.argtypes = [c_short]
    dll.RP1210_ReadMessage.restype = c_short
    dll.RP1210_ReadMessage.argtypes = [c_short, POINTER(c_char), c_short, c_short]
    dll.RP1210_SendMessage.restype = c_short
    dll.RP1210_SendMessage.argtypes = [c_short, POINTER(c_char), c_short, c_short, c_short]
    dll.RP1210_SendCommand.restype = c_short
    dll.RP1210_SendCommand.argtypes = [c_short, c_short, POINTER(c_char), c_short]
    dll.RP1210_GetErrorMsg.restype = c_short
    dll.RP1210_GetErrorMsg.argtypes = [c_short, POINTER(c_char)]
    # Optional: not every driver exports ReadDetailedVersion (CA3 does).
    if hasattr(dll, "RP1210_ReadDetailedVersion"):
        dll.RP1210_ReadDetailedVersion.restype = c_short
        dll.RP1210_ReadDetailedVersion.argtypes = [
            c_short, POINTER(c_char), POINTER(c_char), POINTER(c_char)]
    if hasattr(dll, "RP1210_GetHardwareStatus"):
        dll.RP1210_GetHardwareStatus.restype = c_short
        dll.RP1210_GetHardwareStatus.argtypes = [
            c_short, POINTER(c_char), c_short, c_short]


def _reply(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _errmsg(dll, code: int) -> str:
    """Vendor text for a return code, via the 32-bit DLL's GetErrorMsg.

    Without this every bridged failure reached the 64-bit side as a bare
    number, while the same failure in-process carried the driver's text - so a
    32-bit-driven adapter was undiagnosable from a field report ("err code not
    found" style placeholders never even appeared).
    """
    # 0..127 is a CLIENT ID (a success value, not an error); anything else is
    # an error code. The old test (`code >= 0`) skipped exactly the range the
    # spec uses for errors - 128..255 - so every failing ClientConnect in a
    # 32-bit driver came back as a bare number with no vendor text.
    if dll is None or 0 <= code < 128:
        return ""
    try:
        buf = ctypes.create_string_buffer(80)
        dll.RP1210_GetErrorMsg(c_short(code), buf)
        return buf.raw.split(b"\x00")[0].decode("ascii", "ignore").strip()
    except Exception:                      # noqa: BLE001 - never fail a reply
        return ""


def main() -> None:
    TX = RX = 8192
    dll = None
    # -1 (NOT 0) is the "no client" sentinel: the CA3 driver assigns 0 to its
    # FIRST client (live 2026-11-13), so 0 must stay a usable id here too.
    client = -1

    def valid_client(rc: int) -> bool:
        """RP1210: client ids are 0..127 (including 0), errors 128..255."""
        return 0 <= rc < 128

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            _reply({"ok": False, "error": "bad json"})
            continue
        op = req.get("op")

        if op == "client_connect":
            try:
                dll = ctypes.WinDLL(req["dll"])
                _bind(dll)
            except OSError as e:
                _reply({"rc": -1, "error": f"load dll: {e}"})
                continue
            try:
                rc = int(dll.RP1210_ClientConnect(
                    None, req["device_id"], req["protocol"].encode("ascii"),
                    req.get("tx", TX), req.get("rx", RX), 0))
            except Exception as e:              # noqa: BLE001 - driver raised
                # Some drivers (e.g. .NET ones) raise instead of returning an
                # error code. Never let that kill the bridge process - report
                # it so the 64-bit side sees a clean failure and keeps going.
                client = -1
                _reply({"rc": -1, "msg": f"ClientConnect raised: {e}"})
                continue
            # Never keep an error code as the client id: every later call would
            # answer ERR_INVALID_CLIENT_ID and hide the real reason.
            client = rc if valid_client(rc) else -1
            _reply({"rc": rc, "msg": _errmsg(dll, rc)})

        elif op == "client_disconnect":
            rc = (dll.RP1210_ClientDisconnect(client)
                  if dll is not None and valid_client(client) else 0)
            _reply({"rc": int(rc)})

        elif op == "send_command":
            data = bytes.fromhex(req.get("data", ""))
            buf = ctypes.create_string_buffer(data if data else b"\x00")
            rc = dll.RP1210_SendCommand(req["number"], client, buf, len(data))
            _reply({"rc": int(rc), "msg": _errmsg(dll, int(rc))})

        elif op == "send_message":
            data = bytes.fromhex(req.get("data", ""))
            buf = ctypes.create_string_buffer(data)
            rc = dll.RP1210_SendMessage(client, buf, len(data), 0, 0)
            _reply({"rc": int(rc), "msg": _errmsg(dll, int(rc))})

        elif op == "read_message":
            buf = ctypes.create_string_buffer(RX)
            n = dll.RP1210_ReadMessage(client, buf, RX, 0)   # 0 = non-blocking
            _reply({"n": int(n), "raw": buf.raw[:max(n, 0)].hex(),
                    "msg": _errmsg(dll, int(n))})

        elif op == "detailed_version":
            # Adapter / driver / firmware description strings. Works without a
            # client; load the DLL on demand if connect has not run yet.
            if dll is None and req.get("dll"):
                try:
                    dll = ctypes.WinDLL(req["dll"])
                except OSError as e:
                    _reply({"detail": [], "error": f"load dll: {e}"})
                    continue
            detail = []
            fn = getattr(dll, "RP1210_ReadDetailedVersion", None) if dll else None
            if fn is not None:
                try:
                    fn.restype = c_short
                    fn.argtypes = [c_short, POINTER(c_char), POINTER(c_char),
                                   POINTER(c_char)]
                    bufs = [ctypes.create_string_buffer(80) for _ in range(3)]
                    rc = int(fn(ctypes.c_short(req.get("device_id", 1)),
                                ctypes.cast(bufs[0], POINTER(c_char)),
                                ctypes.cast(bufs[1], POINTER(c_char)),
                                ctypes.cast(bufs[2], POINTER(c_char))))
                    if rc == 0:
                        detail = [b.raw.split(b"\x00")[0].decode("ascii", "ignore").strip()
                                  for b in bufs]
                except Exception:          # noqa: BLE001 - diagnostics only
                    detail = []
            _reply({"detail": [s for s in detail if s]})

        elif op == "hardware_status":
            if dll is None and req.get("dll"):
                try:
                    dll = ctypes.WinDLL(req["dll"])
                except OSError as e:
                    _reply({"rc": -1, "msg": f"load dll: {e}"})
                    continue
            rc = -1
            msg = ""
            fn = getattr(dll, "RP1210_GetHardwareStatus", None) if dll else None
            if fn is not None:
                try:
                    fn.restype = c_short
                    fn.argtypes = [c_short, POINTER(c_char), c_short, c_short]
                    # GetHardwareStatus(clientId, info, infoSize, blocking).
                    # The last arg is a BLOCKING flag, not a timeout - pass 0 so
                    # a dead adapter cannot block the bridge (and the GUI). The
                    # info block is 64 bytes.
                    buf = ctypes.create_string_buffer(64)
                    rc = int(fn(ctypes.c_short(client),
                                ctypes.cast(buf, POINTER(c_char)),
                                ctypes.c_short(64), ctypes.c_short(0)))
                    msg = buf.raw.split(b"\x00")[0].decode("ascii", "ignore").strip()
                    if not msg and rc != 0:
                        msg = _errmsg(dll, rc)
                except Exception as e:          # noqa: BLE001
                    rc, msg = -1, f"call failed: {e}"
            _reply({"rc": rc, "msg": msg})

        elif op == "shutdown":
            if dll is not None and valid_client(client):
                dll.RP1210_ClientDisconnect(client)
            _reply({"ok": True})
            return

        else:
            _reply({"ok": False, "error": "unknown op"})


if __name__ == "__main__":
    main()
