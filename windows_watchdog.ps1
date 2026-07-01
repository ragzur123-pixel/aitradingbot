# AiTradingBot: Windows Watchdog Script
# Purpose: Ensures Ollama and the Trading Bot stay active 24/7.
# Usage: Run this in a dedicated PowerShell window.

Write-Host "--- 🛡️ INITIALIZING WINDOWS WATCHDOG ---" -ForegroundColor Cyan

while($true) {
    # 1. Check if Ollama is running
    $ollama = Get-Process ollama -ErrorAction SilentlyContinue
    if (!$ollama) {
        Write-Host "⚠️ Ollama is down. Restarting..." -ForegroundColor Yellow
        Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 10
    }

    # 2. Check if the Orchestrator is running
    $bot = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*master_orchestrator.py*" }
    if (!$bot) {
        Write-Host "⚠️ Trading Bot is down. Restarting..." -ForegroundColor Yellow
        Start-Process "python" -ArgumentList "master_orchestrator.py"
    }

    # 3. Prevent Sleep
    # This simulated keystroke keeps Windows from entering sleep mode
    $wsh = New-Object -ComObject WScript.Shell
    $wsh.SendKeys('{SCROLLLOCK}')
    $wsh.SendKeys('{SCROLLLOCK}')

    Start-Sleep -Seconds 60
}
