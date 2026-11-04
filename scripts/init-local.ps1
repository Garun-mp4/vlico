$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
if (Test-Path -LiteralPath $envPath) { Write-Output '.env already exists; preserved.'; exit 0 }
function New-LocalSecret {
    $bytes = New-Object byte[] 48
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($bytes)
}
$content = [IO.File]::ReadAllText((Join-Path $projectRoot '.env.example'))
$content = $content.Replace('DJANGO_SECRET_KEY=', ('DJANGO_SECRET_KEY=' + (New-LocalSecret)))
$content = $content.Replace('POSTGRES_PASSWORD=', ('POSTGRES_PASSWORD=' + (New-LocalSecret)))
[IO.File]::WriteAllText($envPath, $content, (New-Object Text.UTF8Encoding($false)))
Write-Output 'Created .env with random local secrets. Never commit it.'
