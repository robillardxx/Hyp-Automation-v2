' HYP Otomasyon - Konsolsuz Baslatici
' Bu dosyaya cift tiklayin - konsol penceresi ACILMAZ

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strScriptPath = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strScriptPath

' Python tam yolu
strPythonPath = "C:\Users\osman\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
strCommand = """" & strPythonPath & """ """ & strScriptPath & "\start_hyp.pyw"""

WshShell.Run strCommand, 0, False
