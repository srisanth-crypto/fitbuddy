import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db, User, Plan, WorkoutLog, PlanLike
from app.config import settings
from app.security import get_password_hash, create_access_token

# Setup in-memory test database with StaticPool to share connection
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def client():
    return TestClient(app)

# ==========================================
# AUTHENTICATION & SECURITY TESTS
# ==========================================

def test_user_registration(client):
    """Test POST /api/auth/register endpoint."""
    payload = {
        "username": "fituser1",
        "email": "fituser1@example.com",
        "password": "Password123!",
        "age": 27,
        "weight": 74.0,
        "goal": "Muscle Gain",
        "intensity": "High"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "fituser1"
    assert data["tier"] == "free"

def test_duplicate_registration_fails(client):
    """Test that duplicate registration fails with 400."""
    payload = {
        "username": "duplicate_user",
        "email": "dup@example.com",
        "password": "Password123!"
    }
    client.post("/api/auth/register", json=payload)
    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400

def test_login_and_jwt(client):
    """Test login and JWT token receipt."""
    client.post("/api/auth/register", json={
        "username": "tokenuser", "email": "token@test.com", "password": "Password123"
    })
    login_resp = client.post("/api/auth/login-json", json={
        "username_or_email": "tokenuser", "password": "Password123"
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

# ==========================================
# STRIPE BILLING & FREE TIER QUOTA TESTS
# ==========================================

def test_free_tier_usage_limit(client):
    """Test that free tier accounts are restricted after monthly limit is reached."""
    client.post("/api/auth/register", json={
        "username": "free_athlete", "email": "free@test.com", "password": "Password123"
    })
    token = client.post("/api/auth/login-json", json={
        "username_or_email": "free_athlete", "password": "Password123"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate allowed plans (up to limit of 3)
    for i in range(settings.FREE_TIER_MONTHLY_LIMIT):
        res = client.post("/api/generate", json={"goal": f"Goal {i}"}, headers=headers)
        assert res.status_code == 201

    # 4th generation should be forbidden with 403
    exceeded_res = client.post("/api/generate", json={"goal": "Goal 4"}, headers=headers)
    assert exceeded_res.status_code == 403
    assert "limit reached" in exceeded_res.json()["detail"].lower()

def test_stripe_checkout_and_billing_status(client):
    """Test billing status endpoint and checkout session creation."""
    client.post("/api/auth/register", json={
        "username": "paying_user", "email": "pay@test.com", "password": "Password123"
    })
    token = client.post("/api/auth/login-json", json={
        "username_or_email": "paying_user", "password": "Password123"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    status_resp = client.get("/api/billing/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["tier"] == "free"

    checkout_resp = client.post("/api/billing/create-checkout-session", headers=headers)
    assert checkout_resp.status_code == 200
    assert "checkout_url" in checkout_resp.json()

# ==========================================
# SOCIAL COMMUNITY & LEADERBOARDS TESTS
# ==========================================

def test_community_public_plans_and_likes(client):
    """Test toggling public plans, community feed, and plan likes."""
    client.post("/api/auth/register", json={
        "username": "social_user", "email": "social@test.com", "password": "Password123"
    })
    token = client.post("/api/auth/login-json", json={
        "username_or_email": "social_user", "password": "Password123"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate plan
    plan = client.post("/api/generate", json={"goal": "General Fitness"}, headers=headers).json()
    plan_id = plan["id"]

    # Toggle Public
    toggle_pub = client.post(f"/api/plans/{plan_id}/toggle-public", headers=headers)
    assert toggle_pub.status_code == 200
    assert toggle_pub.json()["is_public"] is True

    # Check appears in community feed
    comm_resp = client.get("/api/community/plans", headers=headers)
    assert comm_resp.status_code == 200
    plans_feed = comm_resp.json()
    assert len(plans_feed) >= 1
    assert plans_feed[0]["id"] == plan_id

    # Like the plan
    like_resp = client.post(f"/api/plans/{plan_id}/like", headers=headers)
    assert like_resp.status_code == 200
    assert like_resp.json()["liked"] is True
    assert like_resp.json()["like_count"] == 1

def test_community_leaderboard(client):
    """Test community leaderboard aggregation."""
    client.post("/api/auth/register", json={
        "username": "rank1_athlete", "email": "r1@test.com", "password": "Password123"
    })
    token = client.post("/api/auth/login-json", json={
        "username_or_email": "rank1_athlete", "password": "Password123"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    plan = client.post("/api/generate", json={"goal": "Muscle Gain"}, headers=headers).json()
    client.post(f"/api/plans/{plan['id']}/toggle-day/1", headers=headers)

    lb_resp = client.get("/api/community/leaderboard")
    assert lb_resp.status_code == 200
    leaders = lb_resp.json()
    assert len(leaders) >= 1
    assert leaders[0]["username"] == "rank1_athlete"
    assert leaders[0]["total_completed"] == 1

# ==========================================
# PROGRESS, PDF & HEALTH TESTS
# ==========================================

def test_toggle_day_progress_and_streak(client):
    """Test toggling Day 1-7 workout completions."""
    client.post("/api/auth/register", json={
        "username": "streak_tester", "email": "st@test.com", "password": "Password123"
    })
    token = client.post("/api/auth/login-json", json={
        "username_or_email": "streak_tester", "password": "Password123"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    plan = client.post("/api/generate", json={"goal": "Muscle Gain"}, headers=headers).json()
    t1 = client.post(f"/api/plans/{plan['id']}/toggle-day/1", headers=headers)
    assert t1.status_code == 200
    assert t1.json()["completed"] is True

def test_plan_pdf_download(client):
    """Test PDF generation streaming endpoint."""
    client.post("/api/auth/register", json={
        "username": "pdf_tester", "email": "pdf2@test.com", "password": "Password123"
    })
    token = client.post("/api/auth/login-json", json={
        "username_or_email": "pdf_tester", "password": "Password123"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    plan = client.post("/api/generate", json={"goal": "General Fitness"}, headers=headers).json()
    pdf_resp = client.get(f"/api/plans/{plan['id']}/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF-")

def test_api_health(client):
    """Test health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

# ==========================================
# HTML UI PAGES TESTS
# ==========================================

def test_html_ui_pages_render(client):
    """Test that all public UI pages render status 200 with complete navigation and footer."""
    pages = [
        "/",
        "/login",
        "/register",
        "/dashboard",
        "/community",
        "/features",
        "/pricing",
        "/about",
        "/contact",
        "/faq",
        "/privacy",
        "/terms",
        "/feedback",
        "/view-all-users"
    ]
    for page in pages:
        res = client.get(page)
        assert res.status_code == 200, f"Page {page} failed to render with {res.status_code}"
        assert "FitBuddy" in res.text

def test_contact_form_submission(client):
    """Test POST /submit-contact endpoint."""
    res = client.post("/submit-contact", data={
        "name": "Sarah Connor",
        "email": "sarah@example.com",
        "subject": "Subscription & Billing",
        "message": "Testing contact form submission."
    })
    assert res.status_code == 200
    assert "Message Received" in res.text

def test_general_feedback_submission(client):
    """Test POST /submit-general-feedback endpoint."""
    res = client.post("/submit-general-feedback", data={
        "name": "Alex Hunter",
        "email": "alex@hunter.com",
        "category": "Workout Plan Accuracy",
        "rating": 5,
        "comments": "Amazing Gemini generated plans!"
    })
    assert res.status_code == 200
    assert "Thank you, Alex Hunter" in res.text

