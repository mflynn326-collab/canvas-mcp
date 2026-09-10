# Waits for the Claude Desktop app to fully exit, then re-inserts MCP server
# entries into claude_desktop_config.json so the next launch loads them.
# Logs to scripts\register.log.
#   scripts\watch_and_register.ps1                            # canvas (default)
#   scripts\watch_and_register.ps1 -Servers canvas,overleaf
param([string[]]$Servers = @("canvas"))
$Servers = $Servers -split ","
$log = Join-Path $PSScriptRoot "register.log"
"$(Get-Date -Format o) watcher started for $($Servers -join ', '), waiting for Claude to exit..." | Out-File $log -Encoding utf8

while (Get-Process -Name "Claude" -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 2
}
Start-Sleep -Seconds 3  # let the app finish flushing its config on shutdown

foreach ($server in $Servers) {
    $py = Join-Path $PSScriptRoot "register_$($server.Trim()).py"
    $result = & python $py 2>&1
    "$(Get-Date -Format o) Claude exited; $server patch result: $result" | Out-File $log -Append -Encoding utf8
}
