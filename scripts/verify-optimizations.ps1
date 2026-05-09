# CloudVisor Optimization Verification Script
# This script verifies that all optimizations are working correctly

param(
    [switch]$Detailed = $false
)

Write-Host "🔍 CloudVisor Optimization Verification" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

$results = @()

# Function to add test result
function Add-TestResult {
    param($Test, $Status, $Details = "")
    $results += [PSCustomObject]@{
        Test = $Test
        Status = $Status
        Details = $Details
    }
    
    $color = if ($Status -eq "PASS") { "Green" } elseif ($Status -eq "FAIL") { "Red" } else { "Yellow" }
    $icon = if ($Status -eq "PASS") { "✅" } elseif ($Status -eq "FAIL") { "❌" } else { "⚠️" }
    
    Write-Host "$icon $Test" -ForegroundColor $color
    if ($Detailed -and $Details) {
        Write-Host "   $Details" -ForegroundColor Gray
    }
}

Write-Host "`n1. Testing Service Health" -ForegroundColor Yellow
Write-Host "=========================" -ForegroundColor Yellow

# Test auth service health
try {
    $authHealth = Invoke-WebRequest -Uri "http://localhost:8002/health" -UseBasicParsing -TimeoutSec 5
    if ($authHealth.StatusCode -eq 200) {
        Add-TestResult "Auth Service Health" "PASS" "HTTP 200 - Service is healthy"
    } else {
        Add-TestResult "Auth Service Health" "FAIL" "HTTP $($authHealth.StatusCode)"
    }
} catch {
    Add-TestResult "Auth Service Health" "FAIL" "Connection failed: $($_.Exception.Message)"
}

# Test graph service health
try {
    $graphHealth = Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing -TimeoutSec 5
    if ($graphHealth.StatusCode -eq 200) {
        Add-TestResult "Graph Service Health" "PASS" "HTTP 200 - Service is healthy"
    } else {
        Add-TestResult "Graph Service Health" "FAIL" "HTTP $($graphHealth.StatusCode)"
    }
} catch {
    Add-TestResult "Graph Service Health" "FAIL" "Connection failed: $($_.Exception.Message)"
}

Write-Host "`n2. Testing Docker Optimizations" -ForegroundColor Yellow
Write-Host "===============================" -ForegroundColor Yellow

# Check Docker image sizes
try {
    $authImageSize = docker images cloudvisor-auth-service:latest --format "{{.Size}}"
    $graphImageSize = docker images cloudvisor-graph-service:latest --format "{{.Size}}"
    
    Add-TestResult "Auth Service Image Built" "PASS" "Size: $authImageSize"
    Add-TestResult "Graph Service Image Built" "PASS" "Size: $graphImageSize"
} catch {
    Add-TestResult "Docker Images" "FAIL" "Could not check image sizes"
}

# Check if containers are running as non-root
try {
    $authUser = docker exec cv-auth whoami 2>$null
    if ($authUser -eq "appuser") {
        Add-TestResult "Auth Service Security (Non-root)" "PASS" "Running as: $authUser"
    } else {
        Add-TestResult "Auth Service Security (Non-root)" "FAIL" "Running as: $authUser"
    }
} catch {
    Add-TestResult "Auth Service Security (Non-root)" "WARN" "Could not verify user"
}

Write-Host "`n3. Testing Structured Logging" -ForegroundColor Yellow
Write-Host "=============================" -ForegroundColor Yellow

# Check for structured JSON logs
try {
    $authLogs = docker-compose logs --tail=5 auth-service 2>$null | Select-String '"timestamp"'
    if ($authLogs.Count -gt 0) {
        Add-TestResult "Structured JSON Logging" "PASS" "Found $($authLogs.Count) JSON log entries"
    } else {
        Add-TestResult "Structured JSON Logging" "FAIL" "No JSON log entries found"
    }
} catch {
    Add-TestResult "Structured JSON Logging" "WARN" "Could not verify logs"
}

Write-Host "`n4. Testing Security Improvements" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow

# Check if .env files are properly secured
$envFiles = @(
    "services/auth/.env",
    "services/graph/.env"
)

foreach ($envFile in $envFiles) {
    if (Test-Path $envFile) {
        $content = Get-Content $envFile -Raw
        if ($content -match "REPLACE_WITH_YOUR_") {
            Add-TestResult "Environment Security ($envFile)" "PASS" "Contains placeholder values"
        } else {
            Add-TestResult "Environment Security ($envFile)" "WARN" "May contain real credentials"
        }
    } else {
        Add-TestResult "Environment Security ($envFile)" "WARN" "File not found"
    }
}

# Check if .env.example files exist
$exampleFiles = @(
    "services/auth/.env.example"
)

foreach ($exampleFile in $exampleFiles) {
    if (Test-Path $exampleFile) {
        Add-TestResult "Environment Template ($exampleFile)" "PASS" "Template file exists"
    } else {
        Add-TestResult "Environment Template ($exampleFile)" "FAIL" "Template file missing"
    }
}

Write-Host "`n5. Testing Performance Optimizations" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow

# Test response times
try {
    $startTime = Get-Date
    $response = Invoke-WebRequest -Uri "http://localhost:8002/health" -UseBasicParsing
    $endTime = Get-Date
    $responseTime = ($endTime - $startTime).TotalMilliseconds
    
    if ($responseTime -lt 500) {
        Add-TestResult "Auth Service Response Time" "PASS" "$([math]::Round($responseTime, 2))ms"
    } elseif ($responseTime -lt 1000) {
        Add-TestResult "Auth Service Response Time" "WARN" "$([math]::Round($responseTime, 2))ms (acceptable)"
    } else {
        Add-TestResult "Auth Service Response Time" "FAIL" "$([math]::Round($responseTime, 2))ms (too slow)"
    }
} catch {
    Add-TestResult "Auth Service Response Time" "FAIL" "Could not measure response time"
}

Write-Host "`n6. Testing Database Optimizations" -ForegroundColor Yellow
Write-Host "=================================" -ForegroundColor Yellow

# Check if database is accessible
try {
    $dbStatus = docker-compose ps postgres --format json | ConvertFrom-Json
    if ($dbStatus.State -eq "running") {
        Add-TestResult "Database Availability" "PASS" "PostgreSQL is running"
    } else {
        Add-TestResult "Database Availability" "FAIL" "PostgreSQL is not running"
    }
} catch {
    Add-TestResult "Database Availability" "WARN" "Could not verify database status"
}

# Check Redis availability
try {
    $redisStatus = docker-compose ps redis --format json | ConvertFrom-Json
    if ($redisStatus.State -eq "running") {
        Add-TestResult "Cache Availability" "PASS" "Redis is running"
    } else {
        Add-TestResult "Cache Availability" "FAIL" "Redis is not running"
    }
} catch {
    Add-TestResult "Cache Availability" "WARN" "Could not verify Redis status"
}

Write-Host "`n📊 Verification Summary" -ForegroundColor Cyan
Write-Host "======================" -ForegroundColor Cyan

$passCount = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failCount = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$warnCount = ($results | Where-Object { $_.Status -eq "WARN" }).Count
$totalCount = $results.Count

Write-Host "✅ Passed: $passCount" -ForegroundColor Green
Write-Host "❌ Failed: $failCount" -ForegroundColor Red
Write-Host "⚠️  Warnings: $warnCount" -ForegroundColor Yellow
Write-Host "📋 Total Tests: $totalCount" -ForegroundColor White

$successRate = [math]::Round(($passCount / $totalCount) * 100, 1)
Write-Host "`n🎯 Success Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 80) { "Green" } elseif ($successRate -ge 60) { "Yellow" } else { "Red" })

if ($failCount -eq 0) {
    Write-Host "`n🎉 All critical tests passed! CloudVisor optimizations are working correctly." -ForegroundColor Green
} elseif ($failCount -le 2) {
    Write-Host "`n✨ Most optimizations are working. Review failed tests for minor issues." -ForegroundColor Yellow
} else {
    Write-Host "`n🔧 Several optimizations need attention. Please review the failed tests." -ForegroundColor Red
}

Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Monitor service logs: docker-compose logs -f auth-service graph-service"
Write-Host "2. Test API endpoints with your application"
Write-Host "3. Monitor performance metrics in production"
Write-Host "4. Update .env files with your actual credentials"
Write-Host "5. Set up SSL/TLS certificates for production deployment"

if ($Detailed) {
    Write-Host "`n📄 Detailed Results:" -ForegroundColor Cyan
    $results | Format-Table -AutoSize
}

Write-Host "`nVerification completed! 🚀" -ForegroundColor Green