Set-Location $PSScriptRoot
$env:PYTHONDONTWRITEBYTECODE = "1"
& "$PSScriptRoot\.venv\Scripts\python.exe" app.py
