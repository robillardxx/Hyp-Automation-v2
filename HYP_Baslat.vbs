' HYP Otomasyon - Konsolsuz Baslatici
' Bu dosyaya cift tiklayin - konsol penceresi ACILMAZ

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strScriptPath = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strScriptPath

' Python tam yolu
strPythonPath = "C:\Users\pc\AppData\Local\Programs\Python\Python314\pythonw.exe"
strCommand = """" & strPythonPath & """ """ & strScriptPath & "\start_hyp.pyw"""

WshShell.Run strCommand, 0, False
