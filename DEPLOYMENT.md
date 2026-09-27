# FitBuddy Production Deployment & CI/CD Guide

This guide details the complete production setup, database configuration, CI/CD pipeline, and observability integration for **FitBuddy – AI Fitness Plan Generator**.

---

## 1. Production Environment Variables Checklist

Ensure these variables are configured in your Render / Railway environment settings:

| Variable | Required | Default / Recommended | Description |
|---|---|---|---|
| `ENVIRONMENT` | **Yes** | `production` | Deployment mode (production, development, testing) |
| `GEMINI_API_KEY` | **Yes** | `AIzaSy...` | Google Gemini API key from Google AI Studio |
| `SECRET_KEY` | **Yes** | `64+ char random string` | High-entropy key for JWT signature hashing |
| `ALGORITHM` | Optional | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | `10080` (7 days) | JWT session expiration length |
| `DATABASE_URL` | Optional | `postgresql://...` | Connection URI for managed PostgreSQL |
| `SENTRY_DSN` | Optional | `https://...@sentry.io/...` | Real-time backend error & performance monitoring |
| `GEMINI_WORKOUT_MODEL` | Optional | `gemini-2.5-flash` | Primary workout split generator |
| `GEMINI_NUTRITION_MODEL` | Optional | `gemini-2.5-flash` | Nutrition & hydration generator |
| `DEBUG` | Optional | `False` | Turn off interactive tracebacks in production |
| `ALLOWED_ORIGINS` | Optional | `https://your-domain.com` | Allowed CORS origins for cross-origin callers |

---

## 2. Managed Database Setup (PostgreSQL)

FitBuddy automatically normalizes `postgres://` to `postgresql://` to maintain seamless compatibility with SQLAlchemy 2.0.

### On Render:
1. Click **New +** → **PostgreSQL**.
2. Set Name to `fitbuddy-db` and select the Free/Starter tier.
3. Under your Web Service settings, add the environment variable:
   - **Key**: `DATABASE_URL`
   - **Value**: Select **Add from Database** → `Internal Database URL`.
4. FitBuddy's `init_db()` will automatically construct all relational tables (`users`, `plans`, `workout_logs`) upon application boot.

### On Railway:
1. Click **New** → **Database** → **PostgreSQL**.
2. Railway automatically injects the `DATABASE_URL` into your connected web service container.

---

## 3. GitHub Actions CI/CD Pipeline Configuration

FitBuddy includes an automated CI/CD pipeline in [`.github/workflows/ci-cd.yml`](file:///c:/Users/jagadish%20kumar/OneDrive/Desktop/fitbuddy/.github/workflows/ci-cd.yml).

### Pipeline Workflow Stages:
1. **Test Job**: Runs `pytest -v` across Python 3.11 to block broken commits.
2. **Docker Build Job**: Builds container `fitbuddy:latest` and verifies container integrity.
3. **Deploy Job**: Triggers the Render / Railway deploy webhook automatically upon merging into `main`.

### Setting Up the Deployment Webhook:
1. **Render**:
   - In your Render Web Service dashboard, navigate to **Settings** → **Deploy Hook**.
   - Copy the Deploy Hook URL (`https://api.render.com/deploy/srv-xxxx?key=yyyy`).
2. **GitHub Secrets**:
   - In your GitHub repo, go to **Settings** → **Secrets and variables** → **Actions**.
   - Add a new repository secret named `RENDER_DEPLOY_HOOK_URL` and paste the URL.
3. Now, every push to `main` that passes tests will automatically trigger deployment.

---

## 4. Production Observability & Error Tracking

1. **Structured JSON Request Logging**:
   - All incoming requests and responses are logged as structured JSON objects containing `method`, `path`, `status_code`, `process_time_ms`, and `client_ip`.
2. **Sentry Integration**:
   - Set the `SENTRY_DSN` environment variable to enable automatic exception tracking, stack trace visualization, and transaction performance profiling.

---

## 5. Production Smoke Testing & Verification

Run the end-to-end verification suite against your live URL:

### Using PowerShell:
```powershell
.\smoke_test.ps1 -BaseUrl "https://YOUR-APP-NAME.onrender.com"
```

### Using Bash / Linux:
```bash
chmod +x ./smoke_test.sh
./smoke_test.sh "https://YOUR-APP-NAME.onrender.com"
```

The script will test all 6 production stages:
- ✅ **Stage 1**: Health check status
- ✅ **Stage 2**: User registration
- ✅ **Stage 3**: Login and JWT extraction
- ✅ **Stage 4**: Gemini AI plan generation
- ✅ **Stage 5**: ReportLab PDF stream download
- ✅ **Stage 6**: Day completion toggle & streak computation
