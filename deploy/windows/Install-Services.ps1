[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ProjectPath,
    [Parameter(Mandatory=$true)][string]$StatePath,
    [Parameter(Mandatory=$true)][string]$AppHost,
    [Parameter(Mandatory=$true)][string]$WinSWPath,
    [Parameter(Mandatory=$true)][string]$CaddyPath,
    [string]$ExternalBackupPath,
    [switch]$Install
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath $ProjectPath).Path.TrimEnd('\')
$state = (Resolve-Path -LiteralPath $StatePath).Path.TrimEnd('\')
$python = Join-Path $project '.venv\Scripts\python.exe'
$wrapper = (Resolve-Path -LiteralPath $WinSWPath).Path
$caddy = (Resolve-Path -LiteralPath $CaddyPath).Path
$envFile = Join-Path $state 'config\app.env'
$external = $null
if ($ExternalBackupPath) {
    $external = (Resolve-Path -LiteralPath $ExternalBackupPath).Path.TrimEnd('\')
    if (-not (Test-Path -LiteralPath $external -PathType Container)) { throw 'O destino externo precisa ser uma pasta disponível.' }
    if ($external -eq (Join-Path $state 'backups')) { throw 'Escolha um destino externo diferente do backup local.' }
}
if ($AppHost -notmatch '^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+ts\.net$') {
    throw 'Informe o hostname HTTPS real do Tailscale.'
}
if ($project -eq $state -or $project.StartsWith($state + '\', [StringComparison]::OrdinalIgnoreCase) -or $state.StartsWith($project + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Use pastas distintas para o projeto e o estado persistente, sem uma dentro da outra.'
}
foreach ($path in @($project, $state, $wrapper, $caddy)) {
    if ($path.Contains('%') -or $path -eq [IO.Path]::GetPathRoot($path).TrimEnd('\')) {
        throw 'Use pastas dedicadas sem caracteres de expansão de variáveis.'
    }
}
foreach ($path in @($python, $wrapper, $caddy, $envFile, (Join-Path $project 'backend\server.py'), (Join-Path $project 'deploy\Caddyfile'), (Join-Path $project 'deploy\run_backup.py'), (Join-Path $state 'www\index.html'))) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'Prepare primeiro o ambiente Python, configuração e build de produção.' }
}
foreach ($directory in @('config', 'keys', 'data', 'backups', 'logs', 'services', 'www')) {
    if (-not (Test-Path -LiteralPath (Join-Path $state $directory) -PathType Container)) { throw 'O estado de produção está incompleto; use prepare_state.py.' }
}
if ($Install -and -not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Execute a instalação em PowerShell elevado no home server.'
}
foreach ($name in @('Api', 'Web')) {
    if (Get-Service -Name ('FinanceHub' + $name) -ErrorAction SilentlyContinue) {
        throw 'Um serviço já existe. Use o procedimento de atualização documentado.'
    }
}
if ($Install -and (Get-ScheduledTask -TaskName 'FinanceHubBackup' -ErrorAction SilentlyContinue)) {
    throw 'A tarefa FinanceHubBackup já existe; não será substituída.'
}

# Não importa a aplicação nem imprime valores: valida somente os vínculos de produção.
$validateState = @'
import sys
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import dotenv_values
from dotenv.parser import parse_stream

root = Path(sys.argv[1]).resolve()
host = sys.argv[2].lower()
configuration = root / 'config/app.env'
with configuration.open(encoding='utf-8') as stream:
    if any(binding.error for binding in parse_stream(stream)):
        raise SystemExit(1)
settings = dotenv_values(configuration, interpolate=False)
origins = [urlsplit(value.strip()) for value in (settings.get('AUTH_ALLOWED_ORIGINS') or '').split(',')]
if settings.get('APP_ENV') != 'production' or settings.get('AUTH_COOKIE_SECURE', '').lower() != 'true':
    raise SystemExit(1)
if len(origins) != 1 or origins[0].scheme != 'https' or origins[0].hostname != host or origins[0].netloc.lower() != host or origins[0].path or origins[0].query or origins[0].fragment:
    raise SystemExit(1)
if settings.get('SERVER_HOST', '127.0.0.1') != '127.0.0.1' or settings.get('SERVER_PORT', '8000') != '8000' or settings.get('TRUSTED_PROXY', '127.0.0.1') != '127.0.0.1':
    raise SystemExit(1)
database = settings.get('DATABASE_URI') or ''
if not database.startswith('sqlite:///') or Path(database[10:]).resolve() != root / 'data/financehub.db':
    raise SystemExit(1)
for name, relative in [('DATA_ENCRYPTION_KEY_FILE', 'keys/financial-data-keys.json'), ('BACKUP_DIRECTORY', 'backups')]:
    if not settings.get(name) or Path(settings[name]).resolve() != root / relative:
        raise SystemExit(1)
if not (root / 'keys/financial-data-keys.json').is_file():
    raise SystemExit(1)
'@
& $python -B -c $validateState $state $AppHost
if ($LASTEXITCODE -ne 0) { throw 'Configuração incompatível com o hostname, caminhos ou portas de produção; nenhum serviço foi instalado.' }

function Xml([string]$Value) { [System.Security.SecurityElement]::Escape($Value) }
function Write-Utf8([string]$Path, [string]$Content) {
    [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
}
foreach ($name in @('Api', 'Web')) {
    $servicePath = Join-Path $state ('services\' + $name)
    New-Item -ItemType Directory -Path $servicePath -Force | Out-Null
    $logPath = Join-Path $state ('logs\' + $name)
    New-Item -ItemType Directory -Path $logPath -Force | Out-Null
    Copy-Item -LiteralPath $wrapper -Destination (Join-Path $servicePath ('FinanceHub' + $name + '.exe'))
    if ($name -eq 'Api') {
        $executable = $python
        $arguments = '-B -u server.py'
        $working = Join-Path $project 'backend'
        $environment = '<env name="FINANCEHUB_ENV_FILE" value="' + (Xml $envFile) + '"/>'
        $dependencies = ''
    } else {
        Copy-Item -LiteralPath $caddy -Destination (Join-Path $servicePath 'caddy.exe')
        $executable = Join-Path $servicePath 'caddy.exe'
        $arguments = 'run --config "' + (Join-Path $project 'deploy\Caddyfile') + '" --adapter caddyfile'
        $working = $project
        $environment = '<env name="APP_HOST" value="' + (Xml $AppHost) + '"/>' +
            '<env name="FRONTEND_ROOT" value="' + (Xml ((Join-Path $state 'www').Replace('\', '/'))) + '"/>' +
            '<env name="APPDATA" value="' + (Xml $logPath) + '"/>'
        $dependencies = '<depend>FinanceHubApi</depend>'
    }
    $serviceXml = @"
<service>
  <id>FinanceHub$name</id><name>FinanceHub $name</name>
  <description>FinanceHub - serviço de produção</description>
  <executable>$(Xml $executable)</executable><arguments>$(Xml $arguments)</arguments>
  <workingdirectory>$(Xml $working)</workingdirectory>$environment
  <serviceaccount><domain>NT SERVICE</domain><user>FinanceHub$name</user></serviceaccount>
  <startmode>Automatic</startmode><delayedAutoStart>true</delayedAutoStart>
  <stoptimeout>30 sec</stoptimeout><onfailure action="restart" delay="15 sec"/>
  <logpath>$(Xml $logPath)</logpath><log mode="roll-by-size"><sizeThreshold>10240</sizeThreshold><keepFiles>7</keepFiles></log>
  $dependencies
</service>
"@
    Write-Utf8 (Join-Path $servicePath ('FinanceHub' + $name + '.xml')) $serviceXml
}
$originalAppHost = $env:APP_HOST
$originalFrontendRoot = $env:FRONTEND_ROOT
try {
    $env:APP_HOST = $AppHost
    $env:FRONTEND_ROOT = (Join-Path $state 'www').Replace('\', '/')
    & $caddy validate --config (Join-Path $project 'deploy\Caddyfile') --adapter caddyfile
    if ($LASTEXITCODE -ne 0) { throw 'Configuração do proxy inválida.' }
} finally {
    $env:APP_HOST = $originalAppHost
    $env:FRONTEND_ROOT = $originalFrontendRoot
}
if (-not $Install) {
    Write-Output 'Arquivos preparados e proxy validado; use -Install no home server para registrar serviços e tarefas.'
    return
}

function Set-PrivateAcl([string]$Path, [hashtable]$Grants, [switch]$Recursive, [switch]$NoServiceInheritance) {
    $target = Get-Item -LiteralPath $Path -Force
    if ($target.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Permissões não serão aplicadas a links ou junções.' }
    $items = @($target)
    if ($Recursive) { $items += @(Get-ChildItem -LiteralPath $Path -Recurse -Force) }
    if ($items | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
        throw 'Remova links ou junções antes da instalação.'
    }
    foreach ($item in $items) {
        $acl = if ($item.PSIsContainer) { [Security.AccessControl.DirectorySecurity]::new() } else { [Security.AccessControl.FileSecurity]::new() }
        # Uma DACL nova elimina também concessões explícitas antigas, além da herança.
        $acl.SetAccessRuleProtection($true, $false)
        $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
        $permissions = @{ 'S-1-5-18' = 'FullControl'; 'S-1-5-32-544' = 'FullControl' }
        foreach ($sid in $Grants.Keys) { $permissions[$sid] = $Grants[$sid] }
        foreach ($sid in $permissions.Keys) {
            $inheritsGrant = $item.PSIsContainer -and (-not $NoServiceInheritance -or $sid -in @('S-1-5-18', 'S-1-5-32-544'))
            $inheritance = if ($inheritsGrant) { [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit' } else { [Security.AccessControl.InheritanceFlags]::None }
            $rule = [Security.AccessControl.FileSystemAccessRule]::new(
                [Security.Principal.SecurityIdentifier]::new($sid),
                [Security.AccessControl.FileSystemRights]$permissions[$sid],
                $inheritance,
                [Security.AccessControl.PropagationFlags]::None,
                [Security.AccessControl.AccessControlType]::Allow
            )
            $acl.AddAccessRule($rule)
        }
        Set-Acl -LiteralPath $item.FullName -AclObject $acl
    }
}
$installed = @()
try {
    foreach ($name in @('Api', 'Web')) {
        & (Join-Path $state "services\$name\FinanceHub$name.exe") install
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao registrar serviço.' }
        $installed += 'FinanceHub' + $name
        # Impede início automático de uma instalação incompleta em caso de falha ou reinicialização.
        Set-Service -Name ('FinanceHub' + $name) -StartupType Manual
    }
    $apiSid = ([Security.Principal.NTAccount]::new('NT SERVICE\FinanceHubApi')).Translate([Security.Principal.SecurityIdentifier]).Value
    $webSid = ([Security.Principal.NTAccount]::new('NT SERVICE\FinanceHubWeb')).Translate([Security.Principal.SecurityIdentifier]).Value
    Set-PrivateAcl $state @{ $apiSid = 'ReadAndExecute'; $webSid = 'ReadAndExecute' } -NoServiceInheritance
    Set-PrivateAcl $project @{ $apiSid = 'ReadAndExecute'; $webSid = 'ReadAndExecute' } -NoServiceInheritance
    foreach ($directory in @('backend', '.venv')) { Set-PrivateAcl (Join-Path $project $directory) @{ $apiSid = 'ReadAndExecute' } -Recursive }
    Set-PrivateAcl (Join-Path $project 'deploy') @{ $webSid = 'ReadAndExecute' } -Recursive
    foreach ($directory in @('config', 'data', 'backups')) { Set-PrivateAcl (Join-Path $state $directory) @{ $apiSid = 'Modify' } -Recursive }
    Set-PrivateAcl (Join-Path $state 'keys') @{ $apiSid = 'ReadAndExecute' } -Recursive
    Set-PrivateAcl (Join-Path $state 'www') @{ $webSid = 'ReadAndExecute' } -Recursive
    Set-PrivateAcl (Join-Path $state 'services') @{ $apiSid = 'ReadAndExecute'; $webSid = 'ReadAndExecute' } -Recursive
    Set-PrivateAcl (Join-Path $state 'logs') @{ $apiSid = 'ReadAndExecute'; $webSid = 'ReadAndExecute' } -NoServiceInheritance
    foreach ($name in @('Api', 'Web')) {
        $sid = if ($name -eq 'Api') { $apiSid } else { $webSid }
        Set-PrivateAcl (Join-Path $state ('logs\' + $name)) @{ $sid = 'Modify' } -Recursive
    }

    # Os serviços estão parados. A troca atômica preserva o acesso da API e da administração.
    $setServiceSid = @'
import os, sys
from io import StringIO
from pathlib import Path
from uuid import uuid4
from dotenv.parser import parse_stream
sys.path.insert(0, str(Path(sys.argv[1]) / 'backend'))
from services.data_encryption import write_private_file
path = Path(sys.argv[2])
bindings = list(parse_stream(StringIO(path.read_text(encoding='utf-8'))))
if any(binding.error for binding in bindings):
    raise SystemExit(1)
content = ''.join(binding.original.string for binding in bindings if binding.key != 'FINANCEHUB_FILE_ACCESS_SID')
content = content.rstrip('\r\n') + '\nFINANCEHUB_FILE_ACCESS_SID=' + repr(sys.argv[3]) + '\n'
os.environ['FINANCEHUB_FILE_ACCESS_SID'] = sys.argv[3]
temporary = path.with_name('.' + uuid4().hex + '.tmp')
try:
    write_private_file(temporary, content.encode('utf-8'))
    temporary.replace(path)
finally:
    temporary.unlink(missing_ok=True)
'@
    & $python -B -c $setServiceSid $project $envFile $apiSid
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao preservar as permissões da configuração.' }
    & (Join-Path $project 'deploy\windows\Invoke-Backend.ps1') -ProjectPath $project -StatePath $state -Operation Initialize
    & (Join-Path $project 'deploy\windows\Invoke-Backend.ps1') -ProjectPath $project -StatePath $state -Operation Backup -ExternalBackupPath $external

    $jobScript = Join-Path $project 'deploy\run_backup.py'
    $taskArguments = '-B "' + $jobScript + '" --state-dir "' + $state + '"'
    if ($external) { $taskArguments += ' --external-directory "' + $external + '"' }
    $action = New-ScheduledTaskAction -Execute $python -Argument $taskArguments -WorkingDirectory (Join-Path $project 'backend')
    $trigger = New-ScheduledTaskTrigger -Daily -At '03:00'
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) -ExecutionTimeLimit (New-TimeSpan -Hours 1)
    Register-ScheduledTask -TaskName 'FinanceHubBackup' -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
    foreach ($name in @('Api', 'Web')) {
        & sc.exe config ('FinanceHub' + $name) 'start=' 'delayed-auto' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao configurar início automático.' }
    }
    foreach ($name in @('Api', 'Web')) {
        Start-Service -Name ('FinanceHub' + $name)
        (Get-Service -Name ('FinanceHub' + $name)).WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
    }
} catch {
    foreach ($service in $installed) {
        Set-Service -Name $service -StartupType Manual -ErrorAction SilentlyContinue
        Stop-Service -Name $service -Force -ErrorAction SilentlyContinue
    }
    throw 'Instalação interrompida; serviços registrados ficaram em início Manual. Confira logs e conclua a configuração antes de iniciá-los.'
}
Write-Output 'Serviços registrados e backup diário preparado. Configure Tailscale Serve e valide HTTPS conforme o guia.'
