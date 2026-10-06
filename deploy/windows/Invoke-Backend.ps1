[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ProjectPath,
    [Parameter(Mandatory=$true)][string]$StatePath,
    [ValidateSet('Initialize','VerifyDatabase','Backup','VerifyBackup','Admin')][string]$Operation = 'Backup',
    [string]$ExternalBackupPath,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$AdminArguments
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath $ProjectPath).Path
$state = (Resolve-Path -LiteralPath $StatePath).Path
$python = Join-Path $project '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Prepare primeiro o ambiente Python .venv.' }
if (-not (Test-Path -LiteralPath (Join-Path $state 'config\app.env') -PathType Leaf)) {
    throw 'Prepare primeiro a configuração externa de produção.'
}
function Invoke-Flask([string[]]$Arguments) {
    & $python -B -m flask --app main @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Comando de produção falhou; confira configuração e permissões.' }
}
if ($ExternalBackupPath -and $Operation -ne 'Backup') {
    throw 'ExternalBackupPath é usado somente pela operação Backup.'
}
$originalEnvironmentFile = $env:FINANCEHUB_ENV_FILE
Push-Location -LiteralPath (Join-Path $project 'backend')
try {
    $env:FINANCEHUB_ENV_FILE = Join-Path $state 'config\app.env'
    switch ($Operation) {
        'Initialize' { Invoke-Flask -Arguments @('init-db'); Invoke-Flask -Arguments @('verify-encrypted-data') }
        'VerifyDatabase' { Invoke-Flask -Arguments @('verify-encrypted-data') }
        'VerifyBackup' { Invoke-Flask -Arguments @('verify-backup') }
        'Admin' {
            if (-not $AdminArguments) { throw 'Informe o comando administrativo.' }
            Invoke-Flask -Arguments $AdminArguments
        }
        'Backup' {
            # A mesma rotina atende execução manual, agendador e futuras instalações Linux.
            $arguments = @('-B', (Join-Path $project 'deploy\run_backup.py'), '--state-dir', $state)
            if ($ExternalBackupPath) {
                $arguments += @('--external-directory', (Resolve-Path -LiteralPath $ExternalBackupPath).Path)
            }
            & $python @arguments
            if ($LASTEXITCODE -ne 0) { throw 'O backup falhou; consulte logs/backup-status.json e verifique o destino.' }
        }
    }
} finally {
    $env:FINANCEHUB_ENV_FILE = $originalEnvironmentFile
    Pop-Location
}
