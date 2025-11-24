; -------------------------------------------------------------
; Instalador para Estoque Max - versão OneFile do PyInstaller
; -------------------------------------------------------------

[Setup]
AppName=Estoque Max
AppVersion=1.0
DefaultDirName={pf}\Estoque Max
DefaultGroupName=Estoque Max
OutputDir=C:\AQUI
OutputBaseFilename=EstoqueMax_Instalador
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
; Copia o único executável gerado
Source: "C:\Users\Quarto\Desktop\estoque\dist\estoqueMax.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Atalho no Menu Iniciar
Name: "{group}\Estoque Max"; Filename: "{app}\estoqueMax.exe"

; Atalho na Área de Trabalho
Name: "{commondesktop}\Estoque Max"; Filename: "{app}\estoqueMax.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Opções adicionais:"
