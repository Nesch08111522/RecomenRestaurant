param([string]$Time='04:15', [switch]$Remove)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$name='SmartResto-Discovery-Refresh'
if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output 'Tarea SmartResto retirada. No se modificaron datos ni secretos.'
    exit 0
}
$python=Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'No se encontró el Python del entorno virtual de SmartResto.' }
if ($Time -notmatch '^(?:[01]\d|2[0-3]):[0-5]\d$') { throw 'Usa una hora HH:MM válida.' }
$existing=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
if ($existing) { throw 'La tarea ya existe. Revísala antes de sustituirla; usa -Remove para retirarla expresamente.' }
$user=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
if ($user -match '(?i)system|localservice|networkservice') { throw 'Ejecuta el instalador desde tu PowerShell de usuario, no como cuenta de servicio.' }
$action=New-ScheduledTaskAction -Execute $python -Argument '-m scripts.refresh_discovery' -WorkingDirectory $root
$trigger=New-ScheduledTaskTrigger -Daily -At $Time
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Actualiza fuentes gastronómicas autorizadas vencidas de SmartResto. No publica fichas ni envía mensajes externos.' | Out-Null
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State,@{Name='User';Expression={$_.Principal.UserId}}
Write-Output 'Tarea diaria registrada. Requiere sesión de usuario, equipo encendido y acceso a Internet. No se modificó .env.'
