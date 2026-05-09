#!/usr/bin/env pwsh

# CloudVisor Service Health Check Script
# Comprehensive health verification for all services

Write-Host "🔍 CloudVisor Service Health Check" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

$services = @(
    @{ Name = "Connector"; Port = 8000; Path = "/health" },
    @{ Name = "Graph"; Port = 8001; Path = "/health" },
    @{ Name = "Auth"; Port = 8002; Path = "/health" },
    @{ Name = "Policy"; Port = 8003; Path = "/health" },
    @{ Name = "Alert"; Port = 8004; Path = "/health" },
    @{ Name = "API Gateway"; Port = 8005; Path = "/health" },
    @{ Name = "CSPM"; Port = 8006; Path = "/health" },
    @{ Name = "Copilot"; Port = 8010; Path = "/health" }
)

$infrastructure = @(
    @{ Name = "PostgreSQL"; Port = 5432; Type = "database" },
    @{ Name = "Redis"; Port = 6379; Type = "cache" },
    @{ Name = "Elasticsearch"; Port = 9200; Type = "search" },
    @{ Name = "Neo4j"; Port = 7474; Type = "graph-db" },
    @{ Name = "Kafka"; Port = 9092; Type = "messaging" }
)

$healthyServices = 0
$totalServices = $services.Count
$healthyInfra = 0
$totalInfra = $infrastructure.Count

Write-Host "📊 Application Services" -ForegroundColor Yellow
Write-Host "----------------------" -ForegroundColor Yellow

foreach ($service in $services) {
    $url = "http://localhost:$($service.Port)$($service.Path)"
    try {
        $response = Invoke-RestMethod -Uri $url -Method GET -TimeoutSec 5 -ErrorAction Stop
        if ($response.status -eq "healthy") {
            Write-Host "✅ $($service.Name) (port $($service.Port)): HEALTHY" -ForegroundColor Green
            $healthyServices++
        } else {
            Write-Host "⚠️  $($service.Name) (port $($service.Port)): UNHEALTHY - $($response.status)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ $($service.Name) (port $($service.Port)): FAILED - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "🏗️  Infrastructure Services" -ForegroundColor Yellow
Write-Host "---------------------------" -ForegroundColor Yellow

foreach ($infra in $infrastructure) {
    switch ($infra.Type) {
        "database" {
            try {
                $result = docker exec cv-postgres pg_isready -U cloudvisor 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "✅ $($infra.Name) (port $($infra.Port)): HEALTHY" -ForegroundColor Green
                    $healthyInfra++
                } else {
                    Write-Host "❌ $($infra.Name) (port $($infra.Port)): NOT READY" -ForegroundColor Red
                }
            } catch {
                Write-Host "❌ $($infra.Name) (port $($infra.Port)): FAILED" -ForegroundColor Red
            }
        }
        "cache" {
            try {
                $result = docker exec cv-redis redis-cli ping 2>$null
                if ($result -eq "PONG") {
                    Write-Host "✅ $($infra.Name) (port $($infra.Port)): HEALTHY" -ForegroundColor Green
                    $healthyInfra++
                } else {
                    Write-Host "❌ $($infra.Name) (port $($infra.Port)): NOT RESPONDING" -ForegroundColor Red
                }
            } catch {
                Write-Host "❌ $($infra.Name) (port $($infra.Port)): FAILED" -ForegroundColor Red
            }
        }
        "search" {
            try {
                $response = Invoke-RestMethod -Uri "http://localhost:$($infra.Port)/_cluster/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
                if ($response.status -in @("green", "yellow")) {
                    Write-Host "✅ $($infra.Name) (port $($infra.Port)): HEALTHY ($($response.status))" -ForegroundColor Green
                    $healthyInfra++
                } else {
                    Write-Host "⚠️  $($infra.Name) (port $($infra.Port)): UNHEALTHY - $($response.status)" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "❌ $($infra.Name) (port $($infra.Port)): FAILED" -ForegroundColor Red
            }
        }
        "graph-db" {
            try {
                $response = Invoke-RestMethod -Uri "http://localhost:$($infra.Port)/" -Method GET -TimeoutSec 5 -ErrorAction Stop
                if ($response.neo4j_version) {
                    Write-Host "✅ $($infra.Name) (port $($infra.Port)): HEALTHY (v$($response.neo4j_version))" -ForegroundColor Green
                    $healthyInfra++
                } else {
                    Write-Host "❌ $($infra.Name) (port $($infra.Port)): NOT RESPONDING" -ForegroundColor Red
                }
            } catch {
                Write-Host "❌ $($infra.Name) (port $($infra.Port)): FAILED" -ForegroundColor Red
            }
        }
        "messaging" {
            try {
                # Check if Kafka container is running
                $containerStatus = docker ps --filter "name=cv-kafka" --format "{{.Status}}" 2>$null
                if ($containerStatus -like "*Up*") {
                    Write-Host "✅ $($infra.Name) (port $($infra.Port)): HEALTHY" -ForegroundColor Green
                    $healthyInfra++
                } else {
                    Write-Host "❌ $($infra.Name) (port $($infra.Port)): NOT RUNNING" -ForegroundColor Red
                }
            } catch {
                Write-Host "❌ $($infra.Name) (port $($infra.Port)): FAILED" -ForegroundColor Red
            }
        }
    }
}

Write-Host ""
Write-Host "📈 Summary" -ForegroundColor Cyan
Write-Host "----------" -ForegroundColor Cyan
Write-Host "Application Services: $healthyServices/$totalServices healthy" -ForegroundColor $(if ($healthyServices -eq $totalServices) { "Green" } else { "Yellow" })
Write-Host "Infrastructure Services: $healthyInfra/$totalInfra healthy" -ForegroundColor $(if ($healthyInfra -eq $totalInfra) { "Green" } else { "Yellow" })

$overallHealth = ($healthyServices + $healthyInfra) / ($totalServices + $totalInfra) * 100
Write-Host "Overall Health: $([math]::Round($overallHealth, 1))%" -ForegroundColor $(if ($overallHealth -ge 90) { "Green" } elseif ($overallHealth -ge 70) { "Yellow" } else { "Red" })

if ($healthyServices -eq $totalServices -and $healthyInfra -eq $totalInfra) {
    Write-Host ""
    Write-Host "🎉 All services are healthy and operational!" -ForegroundColor Green
    exit 0
} else {
    Write-Host ""
    Write-Host "⚠️  Some services need attention. Check the logs for failed services." -ForegroundColor Yellow
    exit 1
}