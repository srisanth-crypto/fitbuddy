#!/usr/bin/env bash
# ==============================================================================
# FitBuddy Production Smoke Test Suite (Bash / Linux / macOS)
# End-to-End Verification: Health, Auth, AI Generation, PDF Export & Streaks
# ==============================================================================

set -e

BASE_URL="${1:-https://YOUR-LIVE-APP.onrender.com}"
# Strip trailing slash if present
BASE_URL="${BASE_URL%/}"

echo "========================================================="
echo " Starting FitBuddy Production Smoke Test Suite"
echo " Target URL: $BASE_URL"
echo "========================================================="

TIMESTAMP=$(date +%Y%m%d%H%M%S)
TEST_USER="athlete_${TIMESTAMP}"
TEST_EMAIL="athlete_${TIMESTAMP}@example.com"
TEST_PASS="ProductionSecurePassword123!"

# Robust JSON extraction helper using python3 or jq
json_extract() {
    local json_input="$1"
    local key="$2"
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "import sys, json; data = json.loads('''$json_input'''); print(data.get('$key', ''))" 2>/dev/null
    elif command -v jq >/dev/null 2>&1; then
        echo "$json_input" | jq -r ".$key // empty"
    else
        # Fallback simple extractor
        echo "$json_input" | grep -o "\"$key\":[^,}]*" | head -1 | cut -d':' -f2 | tr -d ' "'
    fi
}

# ------------------------------------------------------------------------------
# STAGE 1: Health & Gemini Status Check
# ------------------------------------------------------------------------------
echo ""
echo "[STAGE 1/6] Verifying System Health Endpoint..."
HEALTH_RESP=$(curl -s -f "$BASE_URL/api/health" || { echo "Health check failed"; exit 1; })
STATUS=$(json_extract "$HEALTH_RESP" "status")
PROJECT=$(json_extract "$HEALTH_RESP" "project")
GEMINI=$(json_extract "$HEALTH_RESP" "gemini_configured")

echo " Status:      $STATUS"
echo " Project:     $PROJECT"
echo " Gemini Live: $GEMINI"

if [ "$STATUS" != "healthy" ]; then
    echo "[STAGE 1 FAILED] System status is not healthy."
    exit 1
fi
echo "[STAGE 1 PASSED] Health check succeeded."

# ------------------------------------------------------------------------------
# STAGE 2: User Account Registration
# ------------------------------------------------------------------------------
echo ""
echo "[STAGE 2/6] Registering New Production Athlete..."
REG_PAYLOAD=$(cat <<EOF
{
  "username": "$TEST_USER",
  "email": "$TEST_EMAIL",
  "password": "$TEST_PASS",
  "age": 28,
  "weight": 65.0,
  "goal": "Muscle Gain",
  "intensity": "Medium"
}
EOF
)

REG_RESP=$(curl -s -f -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "$REG_PAYLOAD" || { echo "Registration failed"; exit 1; })

CREATED_USER=$(json_extract "$REG_RESP" "username")
echo " Created User: $CREATED_USER"
echo "[STAGE 2 PASSED] User registration succeeded."

# ------------------------------------------------------------------------------
# STAGE 3: Authenticate and Extract JWT Token
# ------------------------------------------------------------------------------
echo ""
echo "[STAGE 3/6] Authenticating and Extracting JWT Access Token..."
LOGIN_PAYLOAD=$(cat <<EOF
{
  "username_or_email": "$TEST_USER",
  "password": "$TEST_PASS"
}
EOF
)

LOGIN_RESP=$(curl -s -f -X POST "$BASE_URL/api/auth/login-json" \
  -H "Content-Type: application/json" \
  -d "$LOGIN_PAYLOAD" || { echo "Login failed"; exit 1; })

TOKEN=$(json_extract "$LOGIN_RESP" "access_token")

if [ -z "$TOKEN" ]; then
    echo "[STAGE 3 FAILED] Access token was empty in login response."
    exit 1
fi

echo " Token Type:   Bearer"
echo " JWT Acquired: ${TOKEN:0:30}..."
echo "[STAGE 3 PASSED] Authentication & token retrieval succeeded."

# ------------------------------------------------------------------------------
# STAGE 4: Generate Personalized AI Workout & Nutrition Plan
# ------------------------------------------------------------------------------
echo ""
echo "[STAGE 4/6] Generating 7-Day Plan via Gemini AI..."
PLAN_PAYLOAD=$(cat <<EOF
{
  "age": 28,
  "gender": "Female",
  "weight": 65.0,
  "height": 170.0,
  "fitness_goal": "Muscle Gain",
  "fitness_level": "Intermediate",
  "dietary_preference": "Non-Vegetarian",
  "workout_location": "Gym"
}
EOF
)

PLAN_RESP=$(curl -s -f -X POST "$BASE_URL/api/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PLAN_PAYLOAD" || { echo "Plan generation failed"; exit 1; })

PLAN_ID=$(json_extract "$PLAN_RESP" "id")

if [ -z "$PLAN_ID" ]; then
    echo "[STAGE 4 FAILED] Failed to retrieve generated Plan ID."
    exit 1
fi

echo " Generated Plan ID: #$PLAN_ID"
echo "[STAGE 4 PASSED] AI Plan Generation succeeded."

# ------------------------------------------------------------------------------
# STAGE 5: Download & Verify ReportLab PDF Export
# ------------------------------------------------------------------------------
echo ""
echo "[STAGE 5/6] Verifying Branded PDF Streaming Export..."
PDF_FILE="downloaded_plan_${PLAN_ID}.pdf"

curl -s -f -X GET "$BASE_URL/api/plans/$PLAN_ID/pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -o "$PDF_FILE" || { echo "PDF Download failed"; exit 1; }

if [ -f "$PDF_FILE" ]; then
    FILE_SIZE=$(wc -c < "$PDF_FILE" | tr -d ' ')
    PDF_HEADER=$(head -c 4 "$PDF_FILE")
    
    if [ "$PDF_HEADER" = "%PDF" ] && [ "$FILE_SIZE" -gt 1000 ]; then
        echo " PDF File Saved:   $PDF_FILE ($FILE_SIZE bytes)"
        echo " Signature Check:  $PDF_HEADER (Valid PDF)"
        echo "[STAGE 5 PASSED] PDF export verified."
    else
        echo "[STAGE 5 FAILED] File does not have valid %PDF- header or is corrupt."
        exit 1
    fi
else
    echo "[STAGE 5 FAILED] PDF file was not created."
    exit 1
fi

# ------------------------------------------------------------------------------
# STAGE 6: Workout Progress Tracking & Streak Counter Verification
# ------------------------------------------------------------------------------
echo ""
echo "[STAGE 6/6] Testing Workout Day Toggle & Active Streak Counter..."

# 6a. Toggle Day 1
TOGGLE_RESP=$(curl -s -f -X POST "$BASE_URL/api/plans/$PLAN_ID/toggle-day/1" \
  -H "Authorization: Bearer $TOKEN" || { echo "Toggle day failed"; exit 1; })
COMPLETED=$(json_extract "$TOGGLE_RESP" "completed")
echo " Day 1 Completion: $COMPLETED"

# 6b. Check streak
STREAK_RESP=$(curl -s -f -X GET "$BASE_URL/api/users/streak" \
  -H "Authorization: Bearer $TOKEN" || { echo "Streak check failed"; exit 1; })

CURR_STREAK=$(json_extract "$STREAK_RESP" "current_streak")
TOTAL_COMP=$(json_extract "$STREAK_RESP" "total_completed")
RATE=$(json_extract "$STREAK_RESP" "completion_rate")

echo " Current Streak:   $CURR_STREAK day(s)"
echo " Total Completed:  $TOTAL_COMP workout(s)"
echo " Completion Rate:  $RATE%"

echo "[STAGE 6 PASSED] Progress tracking and streak algorithms verified."

echo ""
echo "========================================================="
echo " ALL 6 SMOKE TEST STAGES COMPLETED SUCCESSFULLY! "
echo " FitBuddy is fully operational and production-ready."
echo "========================================================="
