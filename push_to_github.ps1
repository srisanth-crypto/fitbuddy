# FitBuddy GitHub Automation Script
param(
    [string]$RepoUrl = ""
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   FitBuddy GitHub Push Assistant         " -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Check if Git is installed
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    # Check standard install path
    if (Test-Path "C:\Program Files\Git\cmd\git.exe") {
        $env:Path += ";C:\Program Files\Git\cmd"
    } else {
        Write-Host "`nGit is not found on your system." -ForegroundColor Red
        Write-Host "Installing Git now via winget..." -ForegroundColor Yellow
        winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements
        $env:Path += ";C:\Program Files\Git\cmd"
    }
}

# 2. Get GitHub Repo URL
if (-not $RepoUrl) {
    Write-Host "`nPlease paste your GitHub repository URL:" -ForegroundColor Green
    Write-Host "(Example: https://github.com/your-username/fitbuddy.git)" -ForegroundColor Gray
    $RepoUrl = Read-Host "Repo URL"
}

if (-not $RepoUrl) {
    Write-Host "No repository URL provided. Aborting." -ForegroundColor Red
    exit 1
}

Write-Host "`n[1/5] Initializing Git repository..." -ForegroundColor Cyan
if (-not (Test-Path ".git")) {
    git init
}

Write-Host "`n[2/5] Staging files..." -ForegroundColor Cyan
git add .

Write-Host "`n[3/5] Committing project files..." -ForegroundColor Cyan
git commit -m "feat: complete FitBuddy AI fitness SaaS with full UI pages and stripe monetization"

Write-Host "`n[4/5] Setting main branch and remote origin..." -ForegroundColor Cyan
git branch -M main
git remote remove origin -ErrorAction SilentlyContinue
git remote add origin $RepoUrl

Write-Host "`n[5/5] Pushing to GitHub repository..." -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n==========================================" -ForegroundColor Green
    Write-Host " SUCCESS: FitBuddy pushed to GitHub!     " -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
} else {
    Write-Host "`nPush encountered an issue. Please check your GitHub permissions or credentials." -ForegroundColor Yellow
}
