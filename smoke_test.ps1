# ==============================================================================
# FitBuddy Production Smoke Test Suite (PowerShell)
# End-to-End Verification: Health, Auth, AI Generation, PDF Export & Streaks
# ==============================================================================

param (
    [string]$BaseUrl = "https://YOUR-LIVE-APP.onrender.com"
)

# Strip trailing slash if present
$BaseUrl = $BaseUrl.TrimEnd('/')

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " Starting FitBuddy Production Smoke Test Suite" -ForegroundColor Cyan
Write-Host " Target URL: $BaseUrl" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

# Unique identifier to avoid duplicate username/email collisions
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$testUsername = "athlete_$timestamp"
$testEmail = "athlete_$timestamp@example.com"
$testPassword = "ProductionSecurePassword123!"

# ------------------------------------------------------------------------------
# STAGE 1: Health & Gemini Status Check
# ------------------------------------------------------------------------------
Write-Host "`n[STAGE 1/6] Verifying System Health Endpoint..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "$BaseUrl/api/health" -Method Get -TimeoutSec 15
    Write-Host " Status:       $($healthResponse.status)" -ForegroundColor Green
    Write-Host " Project:      $($healthResponse.project)" -ForegroundColor Green
    Write-Host " Gemini Live:  $($healthResponse.gemini_configured)" -ForegroundColor Green
    Write-Host " Version:      $($healthResponse.version)" -ForegroundColor Green
    Write-Host "[STAGE 1 PASSED] Health check succeeded." -ForegroundColor Green
} catch {
    Write-Host "[STAGE 1 FAILED] Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------------------
# STAGE 2: User Account Registration
# ------------------------------------------------------------------------------
Write-Host "`n[STAGE 2/6] Registering New Production Athlete..." -ForegroundColor Yellow
$regBody = @{
    username  = $testUsername
    email     = $testEmail
    password  = $testPassword
    age       = 28
    weight    = 65.0
    goal      = "Muscle Gain"
    intensity = "Medium"
} | ConvertTo-Json -Compress

try {
    $regResponse = Invoke-RestMethod -Uri "$BaseUrl/api/auth/register" `
        -Method Post `
        -ContentType "application/json" `
        -Body $regBody `
        -TimeoutSec 15

    Write-Host " Created User: $($regResponse.username) (ID: $($regResponse.user_id))" -ForegroundColor Green
    Write-Host " Email:        $($regResponse.email)" -ForegroundColor Green
    Write-Host "[STAGE 2 PASSED] User registration succeeded." -ForegroundColor Green
} catch {
    Write-Host "[STAGE 2 FAILED] Registration failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------------------
# STAGE 3: Authenticate and Extract JWT Token
# ------------------------------------------------------------------------------
Write-Host "`n[STAGE 3/6] Authenticating and Extracting JWT Access Token..." -ForegroundColor Yellow
$loginBody = @{
    username_or_email = $testUsername
    password          = $testPassword
} | ConvertTo-Json -Compress

try {
    $loginResponse = Invoke-RestMethod -Uri "$BaseUrl/api/auth/login-json" `
        -Method Post `
        -ContentType "application/json" `
        -Body $loginBody `
        -TimeoutSec 15

    $token = $loginResponse.access_token
    if (-not $token) {
        throw "Access token was empty in login response."
    }

    $tokenSnippet = $token.Substring(0, [Math]::Min(30, $token.Length))
    Write-Host " Token Type:   $($loginResponse.token_type)" -ForegroundColor Green
    Write-Host " JWT Acquired: $tokenSnippet..." -ForegroundColor Green
    Write-Host "[STAGE 3 PASSED] Authentication & token retrieval succeeded." -ForegroundColor Green
} catch {
    Write-Host "[STAGE 3 FAILED] Login failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Standard Auth Header for subsequent protected calls
$authHeaders = @{
    "Authorization" = "Bearer $token"
}

# ------------------------------------------------------------------------------
# STAGE 4: Generate Personalized AI Workout & Nutrition Plan
# ------------------------------------------------------------------------------
Write-Host "`n[STAGE 4/6] Generating 7-Day Plan via Gemini AI..." -ForegroundColor Yellow
$planBody = @{
    age                = 28
    gender             = "Female"
    weight             = 65.0
    height             = 170.0
    fitness_goal       = "Muscle Gain"
    fitness_level      = "Intermediate"
    dietary_preference = "Non-Vegetarian"
    workout_location   = "Gym"
} | ConvertTo-Json -Compress

try {
    $planResponse = Invoke-RestMethod -Uri "$BaseUrl/api/generate" `
        -Method Post `
        -Headers $authHeaders `
        -ContentType "application/json" `
        -Body $planBody `
        -TimeoutSec 60

    $planId = $planResponse.id
    Write-Host " Generated Plan ID: #$planId" -ForegroundColor Green
    Write-Host " Target Athlete:    $($planResponse.user_id)" -ForegroundColor Green
    Write-Host " Has Workout Plan:  $(-not [string]::IsNullOrEmpty($planResponse.original_plan))" -ForegroundColor Green
    Write-Host " Has Nutrition Tip: $(-not [string]::IsNullOrEmpty($planResponse.nutrition_tip))" -ForegroundColor Green
    Write-Host "[STAGE 4 PASSED] AI Plan Generation succeeded." -ForegroundColor Green
} catch {
    Write-Host "[STAGE 4 FAILED] Plan generation failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------------------
# STAGE 5: Download & Verify ReportLab PDF Export
# ------------------------------------------------------------------------------
Write-Host "`n[STAGE 5/6] Verifying Branded PDF Streaming Export..." -ForegroundColor Yellow
$pdfFileName = "downloaded_plan_$planId.pdf"

try {
    Invoke-WebRequest -Uri "$BaseUrl/api/plans/$planId/pdf" `
        -Method Get `
        -Headers $authHeaders `
        -OutFile $pdfFileName `
        -TimeoutSec 20

    if (Test-Path $pdfFileName) {
        $fileSize = (Get-Item $pdfFileName).Length
        # Verify basic PDF binary header (%PDF-)
        $firstBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $pdfFileName))[0..3]
        $headerString = [System.Text.Encoding]::ASCII.GetString($firstBytes)

        if ($headerString -eq "%PDF" -and $fileSize -gt 1000) {
            Write-Host " PDF File Saved:    $pdfFileName ($fileSize bytes)" -ForegroundColor Green
            Write-Host " Format Signature:  $headerString (Valid PDF)" -ForegroundColor Green
            Write-Host "[STAGE 5 PASSED] PDF download and structure verified." -ForegroundColor Green
        } else {
            throw "Downloaded file does not have valid %PDF- header or is too small."
        }
    } else {
        throw "Failed to find downloaded PDF file on disk."
    }
} catch {
    Write-Host "[STAGE 5 FAILED] PDF Export failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------------------
# STAGE 6: Workout Progress Tracking & Streak Counter Verification
# ------------------------------------------------------------------------------
Write-Host "`n[STAGE 6/6] Testing Workout Day Toggle & Active Streak Counter..." -ForegroundColor Yellow
try {
    # 6a. Toggle Day 1 to completed
    $toggleRes = Invoke-RestMethod -Uri "$BaseUrl/api/plans/$planId/toggle-day/1" `
        -Method Post `
        -Headers $authHeaders `
        -TimeoutSec 15

    Write-Host " Day 1 Completion:  $($toggleRes.completed) ($($toggleRes.message))" -ForegroundColor Green

    # 6b. Retrieve Streak Statistics
    $streakRes = Invoke-RestMethod -Uri "$BaseUrl/api/users/streak" `
        -Method Get `
        -Headers $authHeaders `
        -TimeoutSec 15

    Write-Host " Current Streak:    $($streakRes.current_streak) day(s)" -ForegroundColor Green
    Write-Host " Longest Streak:    $($streakRes.longest_streak) day(s)" -ForegroundColor Green
    Write-Host " Total Completed:   $($streakRes.total_completed) workout(s)" -ForegroundColor Green
    Write-Host " Completion Rate:   $($streakRes.completion_rate)%" -ForegroundColor Green
    Write-Host " Active Today:      $($streakRes.active_today)" -ForegroundColor Green

    if ($streakRes.total_completed -ge 1 -and $streakRes.active_today -eq $true) {
        Write-Host "[STAGE 6 PASSED] Progress tracking and streak algorithms verified." -ForegroundColor Green
    } else {
        throw "Streak stats did not reflect completed workout day."
    }
} catch {
    Write-Host "[STAGE 6 FAILED] Streak tracking failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n=========================================================" -ForegroundColor Cyan
Write-Host " ALL 6 SMOKE TEST STAGES COMPLETED SUCCESSFULLY! " -ForegroundColor Green
Write-Host " FitBuddy is fully operational and production-ready." -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
