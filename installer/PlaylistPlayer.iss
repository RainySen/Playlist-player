#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "Playlist Player"
#define AppExe "PlaylistPlayer.exe"
#define VlcUrl "https://get.videolan.org/vlc/3.0.21/win64/vlc-3.0.21-win64.exe"
#define VlcSha256 "9742689a50e96ddc04d80ceff046b28da2beefd617be18166f8c5e715ec60c59"

; appid fijo = actualizaciones sobre la misma instalacion
[Setup]
AppId={{305883F2-3C4B-4702-9A4D-B7A7B172E326}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=RainySen
DefaultDirName={autopf}\PlaylistPlayer
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
OutputDir=..\release
OutputBaseFilename=PlaylistPlayer-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\release\PlaylistPlayer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\vlc-setup.exe"; Parameters: "/L=1033 /S"; Verb: "runas"; Flags: shellexec waituntilterminated; StatusMsg: "Instalando VLC (pide permisos de administrador)..."; Check: VlcDownloaded
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"

[Code]
var
  DownloadPage: TDownloadWizardPage;
  VlcFetched: Boolean;

{ vlc instalado 64 bits }
function VlcInstalled: Boolean;
var
  Dir: String;
begin
  Result := RegQueryStringValue(HKLM64, 'SOFTWARE\VideoLAN\VLC', 'InstallDir', Dir)
    and FileExists(AddBackslash(Dir) + 'libvlc.dll');
end;

function VlcDownloaded: Boolean;
begin
  Result := VlcFetched;
end;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  Result := True;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), @OnDownloadProgress);
end;

{ vlc descargar }
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpReady) and (not VlcInstalled) then
  begin
    DownloadPage.Clear;
    DownloadPage.Add('{#VlcUrl}', 'vlc-setup.exe', '{#VlcSha256}');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
        VlcFetched := True;
      except
        if DownloadPage.AbortedByUser then
          Result := False
        else
          SuppressibleMsgBox('No se pudo descargar VLC:' + #13#10 + GetExceptionMessage + #13#10#13#10 +
            'La app se instalara igual, pero necesitas instalar VLC de 64 bits manualmente (videolan.org).',
            mbError, MB_OK, IDOK);
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
end;
