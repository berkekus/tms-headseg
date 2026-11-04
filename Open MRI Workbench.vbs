Option Explicit

Dim files, shell, root, python, launcher, command, result
Set files = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = files.GetParentFolderName(WScript.ScriptFullName)
python = files.BuildPath(root, "tools\mri_prototype\.venv\Scripts\pythonw.exe")
launcher = files.BuildPath(root, "tools\mri_prototype\launch.py")

If Not files.FileExists(python) Then
    MsgBox "The MRI Workbench environment is missing." & vbCrLf & vbCrLf & _
        "Complete the Windows setup in tools\mri_prototype\README.md first.", _
        vbExclamation, "MRI Workbench"
    WScript.Quit 1
End If
If Not files.FileExists(launcher) Then
    MsgBox "The Workbench launcher is missing. Keep this file in the project root.", _
        vbExclamation, "MRI Workbench"
    WScript.Quit 1
End If

shell.CurrentDirectory = root
command = Chr(34) & python & Chr(34) & " " & Chr(34) & launcher & Chr(34)
If WScript.Arguments.Named.Exists("smoke-test") Then command = command & " --smoke-test"
On Error Resume Next
result = shell.Run(command, 1, True)
If Err.Number <> 0 Then
    MsgBox "MRI Workbench could not start." & vbCrLf & Err.Description, vbCritical, "MRI Workbench"
    WScript.Quit 1
End If
On Error GoTo 0
WScript.Quit result
