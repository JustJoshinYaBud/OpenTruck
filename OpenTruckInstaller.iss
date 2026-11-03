; OpenTruck installer script (Inno Setup 6)
;
; Build with ISCC.exe (compiler), e.g.:
;   "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" OpenTruckInstaller.iss
;
; Bundles the PyInstaller --onedir output in dist\OpenTruck\ (OpenTruck.exe +
; _internal\ DLLs, MainWindow.ui extracted to _MEIPASS at runtime) plus the
; Microsoft Visual C++ 2015-2022 Redistributable, so the target PC needs no
; internet connection and no pre-installed Python / VC++ runtime.
;
; Fully offline: Python (python312.dll + stdlib), Qt/PySide6, reportlab, OpenSSL
; and the VC++ runtime are all bundled. The installer runs elevated (required to
; install the VC++ runtime). The app installs to Program Files and writes its
; config + log folders to per-user dirs (%%APPDATA%% / %%LOCALAPPDATA%%), so
; nothing needs post-install elevation.
;
; User preferences (config.json) live in %APPDATA%\OpenTruck and logs/captures in
; %LOCALAPPDATA%\OpenTruck -- both OUTSIDE {app}. A newer installer run (in-place
; upgrade) therefore preserves all user settings. Keep it that way: never add an
; InstallDelete / UninstallDelete entry for those per-user paths.

#define MyAppName "OpenTruck"
#define MyAppVersion "0.3.0.146"
#define MyAppPublisher "OpenTruck"
#define MyAppExeName "OpenTruck.exe"

[Setup]
; A stable unique ID: the app's name hashed/mangled so upgrades overwrite, and
; re-installs do not create a second uninstall entry.
AppId={{6C5B6C8E-3A2F-4E91-9D2F-1E0B7A3C9F4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Program Files (admin). App writes config + logs to per-user dirs.
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Admin required to install the bundled VC++ runtime (silent /install /quiet).
PrivilegesRequired=admin
; This is a 64-bit application only.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
; Versioned filename (matches the About-box version) so release assets on
; GitHub are never ambiguous; bump_version.py keeps this in sync.
OutputBaseFilename=OpenTruckSetup-{#MyAppVersion}
; Use modern, compact compression (LZMA2/solid).
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Icon for the self-extracting setup executable itself.
SetupIconFile=icon.ico
; Show the license terms before installing.
LicenseFile=LICENSE
UninstallDisplayIcon={app}\{#MyAppExeName}
; No Python / internet required; everything is bundled.
DisableProgramGroupPage=yes
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; The built app directory (this must be produced by PyInstaller --onedir first).
Source: "dist\OpenTruck\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Install folder contains only what the app needs to run, plus the license
; text (distributed with the binaries so the terms travel with every copy).
; Developer docs (README/ARCHITECTURE/ROADMAP) live on GitHub, not here.
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
; Microsoft Visual C++ 2015-2022 Redistributable (x64) — extracted to the temp
; dir and installed silently; deleted afterwards.
Source: "redist\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Install the VC++ runtime BEFORE launching the app (skipped if already present).
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; \
    StatusMsg: "Installing Microsoft Visual C++ Redistributable..."; \
    Flags: runhidden waituntilterminated; Check: not IsVCppRedistInstalled
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
; Silent (self-)update installs have no finish page, so relaunch the app
; directly, de-elevated, when the update finishes.
Filename: "{app}\{#MyAppExeName}"; Flags: runasoriginaluser nowait skipifnotsilent

[Code]
function IsVCppRedistInstalled: Boolean;
var
  Installed: Cardinal;
begin
  // VC++ 2015-2022 x64 writes Installed=1 here when present.
  Result := RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed)
            and (Installed = 1);
end;


// --- SmartScreen: strip the "downloaded from the internet" mark ------------
// A file carrying the Mark-of-the-Web (a Zone.Identifier stream) is treated as
// downloaded, which is what makes Windows show "Windows protected your PC" for
// the INSTALLED program as well as for this installer. The installer unpacks
// fresh files, but the mark can be propagated from the running package, so
// clear it from everything just installed. Harmless where there is none.
//
// This does NOT help Windows 11 "Smart App Control", which blocks unsigned
// programs outright with no "run anyway" option - only a code-signing
// certificate (or turning that feature off) does that.
procedure RemoveZoneIdentifiers(const Dir: String);
var
  FindRec: TFindRec;
  ItemPath: String;
begin
  if FindFirst(AddBackslash(Dir) + '*', FindRec) then
  try
    repeat
      if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
      begin
        ItemPath := AddBackslash(Dir) + FindRec.Name;
        if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
          RemoveZoneIdentifiers(ItemPath)
        else
          DeleteFile(ItemPath + ':Zone.Identifier');
      end;
    until not FindNext(FindRec);
  finally
    FindClose(FindRec);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RemoveZoneIdentifiers(ExpandConstant('{app}'));
end;
