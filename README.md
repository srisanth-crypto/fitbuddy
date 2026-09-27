# ⚡ FitBuddy – Commercial AI Fitness & SaaS Platform

> **FitBuddy** is a full-stack, commercial-grade AI Fitness & Nutrition Plan Generator powered by Google Gemini Models, JWT Authentication, Interactive Streak Progress Tracking, ReportLab PDF Streaming, Stripe Tiered Monetization, Social Community Leaderboards, and Progressive Web App (PWA) Offline Capabilities.

---

## 🌟 Key Features

1. **⚡ Google Gemini AI Coaching**:
   - High-precision 7-day personalized workout routines and tailored nutrition blueprints.
   - Built-in graceful fallback generators guaranteeing 100% uptime even during network or quota limits.
   - Interactive feedback plan revisions (e.g. swap gym gear for home bodyweight exercises).

2. **💳 Stripe SaaS Monetization & Tiered Access**:
   - **Free Tier**: 3 AI plan generations per month with standard workout tracking.
   - **Pro Tier ($9.99/mo)**: Unlimited AI plan generations, priority processing, and public community badges.
   - Stripe Checkout and webhook synchronization (`checkout.session.completed`, `customer.subscription.deleted`).

3. **🌐 Social Fitness Community & Global Leaderboard**:
   - **Public Plan Feed**: Share workout routines publicly with the FitBuddy athlete community.
   - **Interactive Upvotes & Likes**: Upvote proven community training regimens.
   - **Global Streak Leaderboard**: Real-time athlete ranking by consecutive workout days and completion rates.

4. **📱 Progressive Web App (PWA) & Offline Mode**:
   - Installable on iOS, Android, macOS, and Windows.
   - Service worker asset caching (`static/sw.js`) and web app manifest (`static/manifest.json`).

5. **📄 ReportLab PDF Export & Printable Protocols**:
   - One-click branded PDF streaming downloads (`/api/plans/{plan_id}/pdf`).
   - Clean `@media print` styling for native browser printing.

6. **🔒 Enterprise JWT Security & Database Isolation**:
   - Bcrypt password hashing and OAuth2 Bearer token extraction.
   - Complete multi-tenant data isolation and SQLite/PostgreSQL dynamic compatibility.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, Uvicorn, Gunicorn, Pydantic v2, SQLAlchemy 2.0
- **AI Models**: Google Gemini (`gemini-2.5-flash`) via `google-genai` & `google-generativeai`
- **Database**: SQLite (local development) / PostgreSQL (production)
- **Monetization**: Stripe SDK (`stripe`)
- **PDF Engine**: ReportLab Flowables (`reportlab`)
- **Frontend**: Vanilla CSS (CSS Variables, Glassmorphism, Responsive Grid), Vanilla JavaScript (PWA Service Worker)
- **Observability**: Sentry SDK (`sentry-sdk[fastapi]`) & Structured JSON Request Logging
- **CI/CD**: GitHub Actions (`.github/workflows/ci-cd.yml`), Docker (`python:3.11-slim`)

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Create Environment
```bash
git clone https://github.com/<YOUR_USERNAME>/fitbuddy.git
cd fitbuddy

python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Environment Variables
Copy [.env.example](file:///c:/Users/jagadish%20kumar/OneDrive/Desktop/fitbuddy/.env.example) to `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_jwt_secret_key
DATABASE_URL=sqlite:///./fitbuddy.db
```

### 3. Run Application
```bash
uvicorn app.main:app --reload --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## 🧪 Testing & Verification

```bash
# Run complete test suite
pytest -v

# Run PowerShell production smoke test
.\smoke_test.ps1 -BaseUrl "http://127.0.0.1:8000"

# Run Bash production smoke test
./smoke_test.sh "http://127.0.0.1:8000"
```

---

## 🚢 Docker & Production Deployment

```bash
# Run locally with Docker Compose
docker-compose up --build
```
Detailed cloud deployment instructions for Render, Railway, and PostgreSQL are available in [DEPLOYMENT.md](file:///c:/Users/jagadish%20kumar/OneDrive/Desktop/fitbuddy/DEPLOYMENT.md).
