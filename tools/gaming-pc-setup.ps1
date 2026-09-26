# APVIS gaming PC setup: lets APVIS OS use this PC's GPU for bigger AI models.
# Run once on the gaming PC in an ADMIN PowerShell:
#   powershell -ExecutionPolicy Bypass -File gaming-pc-setup.ps1
# What it does (nothing else):
#   1. Installs Ollama with winget if it is missing
#   2. Lets computers on your home network reach Ollama (OLLAMA_HOST=0.0.0.0)
#   3. Opens TCP port 11434 in Windows Firewall for PRIVATE networks only
#   4. Downloads llama3.1:8b (everyday answers) and qwen2.5-coder:7b (code)
#   5. Prints the address to type into APVIS (Settings > Local AI > Gaming PC boost)
$ErrorActionPreference = 'Stop'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Please run this in an Administrator PowerShell (right-click > Run as administrator).' -ForegroundColor Yellow
    exit 1
}

Write-Host '== APVIS gaming PC setup ==' -ForegroundColor Green

# 1. Ollama
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host 'Installing Ollama (winget)...'
    winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
} else {
    Write-Host 'Ollama is already installed.'
}

# 2. Reachable from the home network
[Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0', 'Machine')
$env:OLLAMA_HOST = '0.0.0.0'
Write-Host 'Set OLLAMA_HOST=0.0.0.0 (home network can reach Ollama).'

# 3. Firewall: private networks only
if (-not (Get-NetFirewallRule -DisplayName 'APVIS Ollama (private)' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName 'APVIS Ollama (private)' -Direction Inbound -Protocol TCP -LocalPort 11434 -Profile Private -Action Allow | Out-Null
}
Write-Host 'Firewall: port 11434 open on private networks only.'
$profiles = Get-NetConnectionProfile | Where-Object { $_.IPv4Connectivity -ne 'Disconnected' }
foreach ($p in $profiles) {
    if ($p.NetworkCategory -ne 'Private') {
        Write-Host "Note: network '$($p.Name)' is set to $($p.NetworkCategory). Set it to Private in Windows Settings if APVIS can't find this PC." -ForegroundColor Yellow
    }
}

# Restart Ollama so it listens on the network
Get-Process ollama*, 'ollama app' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden
Start-Sleep -Seconds 4

# 4. Models (GTX 1080 Ti, 11 GB: both fit)
foreach ($m in 'llama3.1:8b', 'qwen2.5-coder:7b') {
    Write-Host "Downloading $m..."
    ollama pull $m
}

# 5. What to type into APVIS
$nic = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1
$ip = $nic.IPv4Address.IPAddress
$mac = ($nic.NetAdapter.MacAddress) -replace '-', ':'
Write-Host ''
Write-Host '== Done ==' -ForegroundColor Green
Write-Host "In APVIS: Settings > Local AI > Gaming PC boost"
Write-Host "  Address:  http://${ip}:11434   (or press Find)" -ForegroundColor Cyan
Write-Host "  MAC (for Wake):  $mac" -ForegroundColor Cyan
Write-Host 'Tip: for Wake to work, enable Wake-on-LAN in the BIOS and in the network adapter settings.'
