; ShellExecAsUser Example
; Executes notepad.exe as standard user from an elevated installer

!include "LogicLib.nsh"

; Add plugin dir if needed
; !addplugindir "plugins\x86-unicode"

Name "ShellExecAsUser Example"
OutFile "example_output.exe"
RequestExecutionLevel admin
ShowInstDetails show

Section "Test"
    ; Run notepad as the logged-on user (even from elevated context)
    ShellExecAsUser::ShellExecAsUser "open" "notepad.exe" ""
    Pop $0
    DetailPrint "Return: $0"
SectionEnd
