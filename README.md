# nsShellExecAsUser NSIS Plugin

**Personal modified version**

---

## Original Description

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

## ⚠️ Differences in the Personal Version

### Supported Architectures

The project supports all configurations:
- **amd64-unicode** (x64)
- **x86-ansi**
- **x86-unicode**

### Visual Studio Project

The project has been updated and reorganized:
- `Contrib/ShellExecAsUser/ShellExecAsUser.sln` - VS2022 Solution
- `Contrib/ShellExecAsUser/ShellExecAsUser.vcxproj` - Updated VS2022 Project

### Added Files

- `build_plugin.py` - Python script to compile the plugin for all supported architectures.
- `nsis/` - NSIS headers included to facilitate compilation.

### Code Changes

- **Deprecation Warning Removal**: Replaced the deprecated `GetVersionEx` call in `VistaTools.cxx` with the modern `VerifyVersionInfo` API to avoid C4996 warnings when compiling with modern toolsets.
- **Build Update**: Configuration updated to use the **v143** toolset (Visual Studio 2022).

### Build

```cmd
cd nsShellExecAsUser
python build_plugin.py
```

DLLs are copied to `plugins/{platform}/ShellExecAsUser.dll`.

### Build Options

```powershell
python build_plugin.py --config x86-unicode      # Single architecture (x86-ansi|x86-unicode|amd64-unicode|all)
python build_plugin.py --toolset 2026            # Specific toolset (2022|2026|auto)
python build_plugin.py --jobs 4                  # Number of parallel MSBuild jobs (default: CPU count)
python build_plugin.py --clean                   # Clean dist/ before build
python build_plugin.py --install-dir "C:\NSIS\Plugins"  # Copy to additional NSIS directory
python build_plugin.py --verbose                 # Extended MSBuild output
python build_plugin.py --version                 # Print version and exit
```

---

*See [README_IT.md](README_IT.md) for the Italian version.*
