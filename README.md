# nsShellExecAsUser NSIS Plugin

**Versione personale modificata**

---

## Descrizione Originale

**ShellExecAsUser plug-in**

Execute the specified program using ShellExecute.
Useful when the installer process is running with elevated privileges (UAC) but you want to launch an application as the standard logged-in user (e.g., launching the application after installation).

## Features

- Launches applications as the current desktop user
- Bypasses UAC elevation if the installer is running as Administrator
- Supports standard ShellExecute verbs (open, runas, print, etc.)
- Supports window show modes (SW_SHOWNORMAL, SW_HIDE, etc.)
- Win95/98/ME/NT/2000/XP/Vista/7/8/10/11 support
- NSIS UNICODE support

## Usage

```nsis
ShellExecAsUser::ShellExecAsUser "action" "command" "parameters" "show_mode"
```

**Parameters:**

1. `action` - The verb to use (e.g., "open", "runas", "print"). Can be empty `""` for default action.
2. `command` - Path to the executable or file to open.
3. `parameters` - Command line arguments.
4. `show_mode` - Window display mode.

**Supported Show Modes:**

- `SW_SHOWDEFAULT`
- `SW_SHOWNORMAL` (default)
- `SW_SHOWMAXIMIZED`
- `SW_SHOWMINIMIZED`
- `SW_HIDE`

**Working Directory:**

The plugin uses the current NSIS output directory (`$OUTDIR`) as the working directory for the launched process.

## Example

```nsis
Section "Launch Application"
    SetOutPath "$INSTDIR"
    ShellExecAsUser::ShellExecAsUser "open" "$INSTDIR\MyApp.exe" "" "SW_SHOWNORMAL"
SectionEnd
```

To launch a URL in the default browser as the user:
```nsis
ShellExecAsUser::ShellExecAsUser "open" "https://example.com" "" "SW_SHOWNORMAL"
```

## Include file

There is no wrapper macros file for this plugin. Call the plugin directly as shown in the usage section.

---

## ⚠️ Differenze nella versione personale

### Architetture supportate

Il progetto supporta le configurazioni già presenti nell'originale:
- **amd64-unicode** (x64)
- **x86-ansi**
- **x86-unicode**

### Progetto Visual Studio

Il progetto è stato aggiornato e riorganizzato:
- `Contrib/ShellExecAsUser/ShellExecAsUser.sln` - Solution VS2022
- `Contrib/ShellExecAsUser/ShellExecAsUser.vcxproj` - Progetto VS2022 aggiornato

### File aggiunti

- `build_plugin.py` - Script Python per compilare il plugin per tutte le architetture supportate.
- `nsis/` - Header NSIS inclusi per facilitare la compilazione.

### Modifiche al Codice

- **Rimozione Warning Deprecazione**: Sostituita la chiamata deprecata `GetVersionEx` in `VistaTools.cxx` con la moderna API `VerifyVersionInfo` per evitare warning C4996 durante la compilazione con i toolset moderni.
- **Aggiornamento Build**: Configurazione aggiornata per utilizzare il toolset **v143** (Visual Studio 2022).

### Compilazione

```cmd
cd nsShellExecAsUser
python build_plugin.py
```

I DLL vengono copiati in `plugins/{platform}/ShellExecAsUser.dll`.

### Opzioni build

```powershell
python build_plugin.py --config x86-unicode      # Solo un'architettura (x86-ansi|x86-unicode|amd64-unicode|all)
python build_plugin.py --toolset 2026            # Toolset specifico (2022|2026|auto)
python build_plugin.py --jobs 4                  # Numero di job MSBuild paralleli (default: CPU count)
python build_plugin.py --clean                   # Pulizia dist/ prima della build
python build_plugin.py --install-dir "C:\NSIS\Plugins"  # Copia in directory NSIS aggiuntiva
python build_plugin.py --verbose                 # Output MSBuild esteso
python build_plugin.py --version                 # Stampa versione ed esce
```
