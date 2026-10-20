# Live status of a running eval: finished result files, whether it's running, and the model's state.
# Run from the repo root: & .\scripts\watch-eval.ps1   (Ctrl+C to stop)
$results = Join-Path $PSScriptRoot "..\eval\express\results"
while ($true) {
    Clear-Host
    Write-Host "Cartograph eval status   $(Get-Date -Format 'HH:mm:ss')   (refreshes every 15 s, Ctrl+C to stop)`n"
    $running = @(Get-Process cartograph -ErrorAction SilentlyContinue).Count -gt 0
    Write-Host ("Eval running: " + $(if ($running) { "yes" } else { "no" }))
    Write-Host "`nFinished result files (newest first):"
    Get-ChildItem $results -Filter *.json | Sort-Object LastWriteTime -Descending | ForEach-Object {
        $s = (Get-Content $_.FullName -Raw | ConvertFrom-Json).summary.all
        $line = "  {0,-42} {1:HH:mm}  n={2,-4} acc@1={3,-6} acc@5={4,-6}" -f $_.BaseName, $_.LastWriteTime, $s.n, $s.'acc@1', $s.'acc@5'
        if ($s.'acc@answer' -ne $null) { $line += " answer={0}" -f $s.'acc@answer' }
        Write-Host $line
    }
    Write-Host "`nLocal AI model (Ollama):"
    & "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" ps
    Start-Sleep -Seconds 15
}
