# nsShellExecAsUser NSIS Plugin

**Versione personale modificata**

---

## Descrizione Originale

**ShellExecAsUser plug-in**

Esegue il programma specificato tramite ShellExecute.
Utile quando il processo installer è in esecuzione con privilegi elevati (UAC) ma si vuole avviare un'applicazione come l'utente standard connesso (es. avvio dell'applicazione dopo l'installazione).

## Funzionalità

- Avvia applicazioni come l'utente desktop corrente
- Bypassa l'elevazione UAC se l'installer è in esecuzione come Amministratore
- Supporta i verbi standard di ShellExecute (open, runas, print, ecc.)
- Supporta le modalità di visualizzazione finestra (SW_SHOWNORMAL, SW_HIDE, ecc.)
- Supporto Win95/98/ME/NT/2000/XP/Vista/7/8/10/11
- Supporto NSIS UNICODE

## Utilizzo

```nsis
ShellExecAsUser::ShellExecAsUser "azione" "comando" "parametri" "modalità_finestra"
```

**Parametri:**

1. `azione` - Il verbo da usare (es. "open", "runas", "print"). Può essere vuoto `""` per l'azione default.
2. `comando` - Percorso all'eseguibile o file da aprire.
3. `parametri` - Argomenti della riga di comando.
4. `modalità_finestra` - Modalità di visualizzazione della finestra.

**Modalità Finestra Supportate:**

- `SW_SHOWDEFAULT`
- `SW_SHOWNORMAL` (default)
- `SW_SHOWMAXIMIZED`
- `SW_SHOWMINIMIZED`
- `SW_HIDE`

**Directory di Lavoro:**

Il plugin usa la directory di output NSIS corrente (`$OUTDIR`) come directory di lavoro per il processo avviato.

## Esempio

```nsis
Section "Avvia Applicazione"
    SetOutPath "$INSTDIR"
    ShellExecAsUser::ShellExecAsUser "open" "$INSTDIR\MyApp.exe" "" "SW_SHOWNORMAL"
SectionEnd
```

Per aprire un URL nel browser predefinito come utente:
```nsis
ShellExecAsUser::ShellExecAsUser "open" "https://example.com" "" "SW_SHOWNORMAL"
```

## File include

Non esiste un file di macro wrapper per questo plugin. Chiama il plugin direttamente come mostrato nella sezione utilizzo.

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

---

*See [README.md](README.md) for the English version.*
