$ws = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')
$sc = $ws.CreateShortcut("$desktop\Hackathon AI Studio.lnk")
$sc.TargetPath = "C:\Users\user\Desktop\Start_Hackathon_Hub.bat"
$sc.WorkingDirectory = "C:\Users\user\.gemini\antigravity\scratch\hackathon_ai_hub"
$ico = "C:\Users\user\.gemini\antigravity\scratch\hackathon_ai_hub\app_icon.ico"
if (Test-Path $ico) {
    $sc.IconLocation = $ico
}
$sc.Save()
Write-Output "Shortcut created and verified on Desktop."
