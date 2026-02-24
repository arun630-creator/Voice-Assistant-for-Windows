; Nova Voice Assistant — Inno Setup Installer Script
; Compile with: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
;
; Assumes PyInstaller has already built dist\Nova\ via:
;   .\build.ps1
;
; To compile this installer:
;   1. Install Inno Setup 6 from https://jrsoftware.org/isdl.php
;   2. Open this .iss file in Inno Setup Compiler
;   3. Click Build → Compile
;   4. Output: installer\NovaSetup.exe

#define MyAppName "Nova Voice Assistant"
#define MyAppVersion "1.2"
#define MyAppPublisher "Nova"
#define MyAppExeName "Nova.exe"
#define MyAppURL "https://github.com/nova-voice-assistant"

[Setup]
AppId={{E7B3F2A1-9C4D-4E8F-B6A2-1D3E5F7A8B9C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=NovaSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
; App icon
SetupIconFile=assets\nova.ico
UninstallDisplayIcon={app}\Nova.exe
; Require 64-bit Windows
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Uninstall info
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startupentry"; Description: "&Start Nova with Windows (recommended)"; GroupDescription: "Windows integration:"

[Files]
; Bundle the entire PyInstaller output folder
Source: "dist\Nova\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\assets\nova.ico"; Comment: "Launch Nova Voice Assistant"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop (optional)
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\assets\nova.ico"; Tasks: desktopicon; Comment: "Launch Nova Voice Assistant"

[Registry]
; Start with Windows (if user checked the task)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "NovaVoiceAssistant"; \
    ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: startupentry

[Run]
; Offer to launch after install
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch {#MyAppName}"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
; Clean up on uninstall — kill any running Nova process
Filename: "taskkill.exe"; Parameters: "/f /im {#MyAppExeName}"; \
    Flags: runhidden; RunOnceId: "KillNova"

[UninstallDelete]
; Clean up logs and runtime data
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\data\memory.db"
Type: filesandordirs; Name: "{app}\data\memory.db-shm"
Type: filesandordirs; Name: "{app}\data\memory.db-wal"
