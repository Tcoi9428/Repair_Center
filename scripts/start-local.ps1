$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location $projectRoot
$pgCtl = Join-Path $projectRoot '.local/postgresql/pgsql/bin/pg_ctl.exe'
$pgData = Join-Path $projectRoot '.local/pgdata'
if (Test-Path -LiteralPath $pgCtl) {
    & $pgCtl -D $pgData status 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        & $pgCtl -D $pgData -l (Join-Path $projectRoot '.local/postgres.log') start -w
        if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL не запущен. Проверьте .local/postgres.log.' }
    }
}
& .\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

