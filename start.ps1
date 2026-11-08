$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$action = if ($args.Count -gt 0) { $args[0] } else { 'start' }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw 'Docker or WSL 2 is required.' }
    $linuxPath = (& wsl.exe --exec wslpath -a $PSScriptRoot).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $linuxPath) { throw 'Cannot translate project path to WSL.' }
    & wsl.exe --exec bash "$linuxPath/start.sh" $action
    exit $LASTEXITCODE
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Install Python 3.' }
python scripts/setup.py $action
exit $LASTEXITCODE
