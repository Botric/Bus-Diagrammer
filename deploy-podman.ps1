# Bus Diagrammer Podman Deployment Script
# This script builds and deploys the Bus Diagrammer application using Podman

param(
    [switch]$Stop,
    [switch]$Restart,
    [switch]$Logs,
    [switch]$Status
)

$ContainerName = "bus-diagrammer"
$ImageName = "bus-diagrammer:latest"
$Port = "5620"
$HostPort = "5620"

# Function to check if container exists
function ContainerExists {
    $exists = podman ps -a --format "{{.Names}}" | Select-String -Pattern "^$ContainerName$"
    return $null -ne $exists
}

# Function to check if container is running
function ContainerRunning {
    $running = podman ps --format "{{.Names}}" | Select-String -Pattern "^$ContainerName$"
    return $null -ne $running
}

# Stop container
if ($Stop) {
    Write-Host "Stopping Bus Diagrammer container..." -ForegroundColor Yellow
    if (ContainerExists) {
        podman stop $ContainerName
        podman rm $ContainerName
        Write-Host "Container stopped and removed." -ForegroundColor Green
    } else {
        Write-Host "Container does not exist." -ForegroundColor Yellow
    }
    exit 0
}

# Show logs
if ($Logs) {
    Write-Host "Showing logs for Bus Diagrammer container..." -ForegroundColor Yellow
    if (ContainerExists) {
        podman logs -f $ContainerName
    } else {
        Write-Host "Container does not exist." -ForegroundColor Red
    }
    exit 0
}

# Show status
if ($Status) {
    Write-Host "Bus Diagrammer Container Status:" -ForegroundColor Yellow
    if (ContainerExists) {
        podman ps -a --filter "name=$ContainerName" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        Write-Host "`nContainer details:" -ForegroundColor Yellow
        podman inspect $ContainerName --format "{{.State.Status}}"
    } else {
        Write-Host "Container does not exist." -ForegroundColor Red
    }
    exit 0
}

# Restart container
if ($Restart) {
    Write-Host "Restarting Bus Diagrammer container..." -ForegroundColor Yellow
    if (ContainerRunning) {
        podman restart $ContainerName
        Write-Host "Container restarted." -ForegroundColor Green
    } else {
        Write-Host "Container is not running. Starting fresh deployment..." -ForegroundColor Yellow
    }
}

# Main deployment process
Write-Host "=== Bus Diagrammer Podman Deployment ===" -ForegroundColor Cyan
Write-Host "Building and deploying Bus Diagrammer application..." -ForegroundColor Green

# Stop and remove existing container if it exists
if (ContainerExists) {
    Write-Host "Stopping existing container..." -ForegroundColor Yellow
    podman stop $ContainerName 2>$null
    podman rm $ContainerName 2>$null
}

# Build the image
Write-Host "Building Docker image..." -ForegroundColor Yellow
podman build -t $ImageName .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build image!" -ForegroundColor Red
    exit 1
}

# Create and start the container
Write-Host "Creating and starting container..." -ForegroundColor Yellow
podman run -d `
    --name $ContainerName `
    -p "$HostPort`:$Port" `
    --restart unless-stopped `
    -v "${PWD}/srt_database.json:/home/appuser/app/srt_database.json:Z" `
    $ImageName

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start container!" -ForegroundColor Red
    exit 1
}

# Wait a moment for the container to start
Start-Sleep -Seconds 3

# Check if container is running
if (ContainerRunning) {
    Write-Host "=== Deployment Successful! ===" -ForegroundColor Green
    Write-Host "Bus Diagrammer is now running at: http://localhost:$HostPort" -ForegroundColor Cyan
    Write-Host "Container name: $ContainerName" -ForegroundColor Gray
    Write-Host "`nUseful commands:" -ForegroundColor Yellow
    Write-Host "  View logs:    .\deploy-podman.ps1 -Logs" -ForegroundColor Gray
    Write-Host "  Check status: .\deploy-podman.ps1 -Status" -ForegroundColor Gray
    Write-Host "  Restart:      .\deploy-podman.ps1 -Restart" -ForegroundColor Gray
    Write-Host "  Stop:         .\deploy-podman.ps1 -Stop" -ForegroundColor Gray
} else {
    Write-Host "Failed to start container!" -ForegroundColor Red
    Write-Host "Checking logs for errors..." -ForegroundColor Yellow
    podman logs $ContainerName
    exit 1
}
