# Launcher used by the scheduled task. Runs train.py (which resumes automatically)
# and appends all output to outputs\train_stdout.log.
$py = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
New-Item -ItemType Directory -Force -Path "outputs" | Out-Null
"`n=== start $(Get-Date -Format s) ===" | Out-File -Append -Encoding utf8 "outputs\train_stdout.log"
cmd /c "`"$py`" -u train.py >> outputs\train_stdout.log 2>&1"
"=== exit $LASTEXITCODE $(Get-Date -Format s) ===" | Out-File -Append -Encoding utf8 "outputs\train_stdout.log"
