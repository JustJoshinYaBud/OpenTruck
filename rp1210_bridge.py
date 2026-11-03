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


def _reply(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> None:
    TX = RX = 8192
    dll = None
    client = 0

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
            client = dll.RP1210_ClientConnect(
                None, req["device_id"], req["protocol"].encode("ascii"),
                req.get("tx", TX), req.get("rx", RX), 0)
            _reply({"rc": int(client)})

        elif op == "client_disconnect":
            rc = dll.RP1210_ClientDisconnect(client) if dll is not None and client > 0 else 0
            _reply({"rc": int(rc)})

        elif op == "send_command":
            data = bytes.fromhex(req.get("data", ""))
            buf = ctypes.create_string_buffer(data if data else b"\x00")
            rc = dll.RP1210_SendCommand(req["number"], client, buf, len(data))
            _reply({"rc": int(rc)})

        elif op == "send_message":
            data = bytes.fromhex(req.get("data", ""))
            buf = ctypes.create_string_buffer(data)
            rc = dll.RP1210_SendMessage(client, buf, len(data), 0, 0)
            _reply({"rc": int(rc)})

        elif op == "read_message":
            buf = ctypes.create_string_buffer(RX)
            n = dll.RP1210_ReadMessage(client, buf, RX, 0)   # 0 = non-blocking
            _reply({"n": int(n), "raw": buf.raw[:max(n, 0)].hex()})

        elif op == "shutdown":
            if dll is not None and client > 0:
                dll.RP1210_ClientDisconnect(client)
            _reply({"ok": True})
            return

        else:
            _reply({"ok": False, "error": "unknown op"})


if __name__ == "__main__":
    main()
