from typing import List, Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import (
    get_db,
    User,
    Plan,
    WorkoutLog,
    PlanLike,
    get_user_plans,
    get_user_plan_by_id,
    delete_user_plan,
    toggle_workout_day,
    calculate_user_streak,
    count_monthly_generated_plans
)
from app.schemas import (
    UserCreate,
    UserLogin,
    Token,
    UserOut,
    UserResponse,
    HealthResponse,
    PlanResponse,
    GeneratePlanRequest,
    FeedbackSubmit,
    UserProfileUpdate,
    WorkoutLogOut,
    ToggleDayResponse,
    StreakSummary,
    CheckoutSessionResponse,
    SubscriptionStatusResponse,
    LeaderboardEntry,
    PublicPlanOut
)
from app.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    get_optional_current_user
)
from app.gemini_generator import generate_workout_plan
from app.gemini_flash_generator import generate_nutrition_tip
from app.updated_plan import update_workout_plan
from app.pdf_generator import generate_plan_pdf
from app.stripe_service import create_stripe_checkout_session, verify_and_construct_webhook_event
from app.ai_common import is_gemini_configured
from app.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

# ==========================================
# UI / HTML PAGES
# ==========================================

@router.get("/", response_class=HTMLResponse)
async def get_home_page(request: Request):
    """Renders the main FitBuddy landing & fitness plan generator page."""
    return templates.TemplateResponse(request=request, name="index.html", context={
        "gemini_active": is_gemini_configured()
    })

@router.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    """Renders the user login page."""
    return templates.TemplateResponse(request=request, name="login.html", context={
        "gemini_active": is_gemini_configured()
    })

@router.get("/register", response_class=HTMLResponse)
async def get_register_page(request: Request):
    """Renders the user registration page."""
    return templates.TemplateResponse(request=request, name="register.html", context={
        "gemini_active": is_gemini_configured()
    })

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard_page(request: Request):
    """Renders the athlete dashboard & saved plan history page."""
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "gemini_active": is_gemini_configured()
    })

@router.get("/community", response_class=HTMLResponse)
async def get_community_page(request: Request):
    """Renders the global social community feed and streak leaderboard page."""
    return templates.TemplateResponse(request=request, name="community.html", context={
        "gemini_active": is_gemini_configured()
    })

@router.get("/features", response_class=HTMLResponse)
async def get_features_page(request: Request):
    """Renders the platform features & AI capabilities page."""
    return templates.TemplateResponse(request=request, name="features.html", context={
        "gemini_active": is_gemini_configured()
    })

@router.get("/pricing", response_class=HTMLResponse)
async def get_pricing_page(request: Request):
    """Renders the membership pricing, Pro tier breakdown, and FAQ page."""
    return templates.TemplateResponse(request=request, name="pricing.html", context={
        "gemini_active": is_gemini_configured()
    })

@router.get("/about", response_class=HTMLResponse)
async def get_about_page(request: Request):
    """Renders the About FitBuddy mission, technology, and engineering standards page."""
    return templates.TemplateResponse(request=request, name="about.html", context={
        "gemini_active": is_gemini_configured()
    })

@router.get("/contact", response_class=HTMLResponse)
async def get_contact_page(request: Request):
    """Renders the customer contact and athlete support ticket page."""
    return templates.TemplateResponse(request=request, name="contact.html", context={
        "contact_submitted": False,
        "gemini_active": is_gemini_configured()
    })

@router.post("/submit-contact", response_class=HTMLResponse)
async def handle_submit_contact_form(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...)
):
    """Processes contact message submissions and displays immediate confirmation."""
    return templates.TemplateResponse(request=request, name="contact.html", context={
        "contact_submitted": True,
        "sender_name": name.strip(),
        "subject": subject.strip(),
        "gemini_active": is_gemini_configured()
    })

@router.get("/faq", response_class=HTMLResponse)
async def get_faq_page(request: Request):
    """Renders the comprehensive FAQ knowledge base page."""
    return templates.TemplateResponse(request=request, name="faq.html", context={
        "gemini_active": is_gemini_configured()
    })

@router.get("/privacy", response_class=HTMLResponse)
async def get_privacy_page(request: Request):
    """Renders the GDPR/CCPA compliant privacy policy page."""
    return templates.TemplateResponse(request=request, name="privacy.html", context={
        "gemini_active": is_gemini_configured()
    })

@router.get("/terms", response_class=HTMLResponse)
async def get_terms_page(request: Request):
    """Renders the Terms of Service & Medical Disclaimer page."""
    return templates.TemplateResponse(request=request, name="terms.html", context={
        "gemini_active": is_gemini_configured()
    })

@router.get("/feedback", response_class=HTMLResponse)
async def get_general_feedback_hub_page(request: Request):
    """Renders the athlete reviews, platform feedback submission, and plan lookup hub."""
    return templates.TemplateResponse(request=request, name="feedback_hub.html", context={
        "feedback_submitted": False,
        "gemini_active": is_gemini_configured()
    })

@router.post("/submit-general-feedback", response_class=HTMLResponse)
async def handle_submit_general_feedback_form(
    request: Request,
    name: str = Form(...),
    email: Optional[str] = Form(None),
    category: str = Form(...),
    rating: int = Form(5),
    comments: str = Form(...)
):
    """Processes community feedback reviews and displays confirmation."""
    return templates.TemplateResponse(request=request, name="feedback_hub.html", context={
        "feedback_submitted": True,
        "submitter_name": name.strip(),
        "category": category,
        "rating": rating,
        "gemini_active": is_gemini_configured()
    })

@router.post("/generate-workout", response_class=HTMLResponse)
async def handle_generate_workout_form(
    request: Request,
    user_id: str = Form(...),
    username: str = Form(...),
    age: int = Form(...),
    weight: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
    db: Session = Depends(get_db)
):
    """Validates user input, saves/updates to DB, calls Gemini for workout + nutrition, and renders result page."""
    user_id = user_id.strip()
    username = username.strip()

    # Form Validation
    errors = []
    if not user_id:
        errors.append("User ID cannot be empty.")
    if not username:
        errors.append("Name cannot be empty.")
    if age < 10 or age > 120:
        errors.append("Age must be between 10 and 120.")
    if weight < 20.0 or weight > 350.0:
        errors.append("Weight must be between 20 kg and 350 kg.")
    if intensity not in ["Low", "Medium", "High"]:
        errors.append("Intensity must be Low, Medium, or High.")

    if errors:
        return templates.TemplateResponse(request=request, name="index.html", context={
            "errors": errors,
            "user_id": user_id,
            "username": username,
            "age": age,
            "weight": weight,
            "goal": goal,
            "intensity": intensity,
            "gemini_active": is_gemini_configured()
        }, status_code=status.HTTP_400_BAD_REQUEST)

    # 1. Save or Update User in DB
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(
            user_id=user_id,
            username=username,
            email=f"{user_id}@example.com",
            age=age,
            weight=weight,
            goal=goal,
            intensity=intensity,
            is_active=True
        )
        db.add(user)
    else:
        user.username = username
        user.age = age
        user.weight = weight
        user.goal = goal
        user.intensity = intensity
    db.commit()
    db.refresh(user)

    user_dict = {
        "user_id": user.user_id,
        "username": user.username,
        "age": user.age,
        "weight": user.weight,
        "goal": user.goal,
        "intensity": user.intensity
    }

    # 2. Generate Workout Plan using Gemini (or fallback)
    workout_plan_text = generate_workout_plan(user_dict)

    # 3. Generate Nutrition / Recovery using Fast Gemini (or fallback)
    nutrition_tip_text = generate_nutrition_tip(user_dict)

    # 4. Save Plan in DB
    plan_record = Plan(
        user_id=user.user_id,
        original_plan=workout_plan_text,
        nutrition_tip=nutrition_tip_text
    )
    db.add(plan_record)
    db.commit()
    db.refresh(plan_record)

    return templates.TemplateResponse(request=request, name="result.html", context={
        "user": user,
        "plan": plan_record,
        "current_plan_text": workout_plan_text,
        "is_updated": False,
        "gemini_active": is_gemini_configured()
    })

@router.get("/feedback/{user_id}", response_class=HTMLResponse)
async def get_feedback_page(user_id: str, request: Request, db: Session = Depends(get_db)):
    """Renders the feedback page for the given user's latest plan."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    latest_plan = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.created_at.desc()).first()
    if not latest_plan:
        raise HTTPException(status_code=404, detail="No workout plan found for this user")

    current_plan_text = latest_plan.updated_plan if latest_plan.updated_plan else latest_plan.original_plan

    return templates.TemplateResponse(request=request, name="feedback.html", context={
        "user": user,
        "plan": latest_plan,
        "current_plan_text": current_plan_text,
        "gemini_active": is_gemini_configured()
    })

@router.post("/submit-feedback", response_class=HTMLResponse)
async def handle_submit_feedback_form(
    request: Request,
    user_id: str = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db)
):
    """Processes user feedback from web form, updates plan via Gemini/fallback, and renders revised result."""
    user_id = user_id.strip()
    feedback = feedback.strip()

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    latest_plan = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.created_at.desc()).first()
    if not latest_plan:
        raise HTTPException(status_code=404, detail="No plan found to update")

    if not feedback or len(feedback) < 3:
        return templates.TemplateResponse(request=request, name="feedback.html", context={
            "user": user,
            "plan": latest_plan,
            "current_plan_text": latest_plan.updated_plan or latest_plan.original_plan,
            "error": "Please provide detailed feedback (at least 3 characters).",
            "gemini_active": is_gemini_configured()
        }, status_code=status.HTTP_400_BAD_REQUEST)

    user_dict = {
        "user_id": user.user_id,
        "username": user.username,
        "age": user.age,
        "weight": user.weight,
        "goal": user.goal,
        "intensity": user.intensity
    }

    base_plan = latest_plan.original_plan
    updated_plan_text = update_workout_plan(base_plan, feedback, user_dict)

    # Update the plan record
    latest_plan.updated_plan = updated_plan_text
    latest_plan.feedback = feedback
    db.commit()
    db.refresh(latest_plan)

    return templates.TemplateResponse(request=request, name="result.html", context={
        "user": user,
        "plan": latest_plan,
        "current_plan_text": updated_plan_text,
        "is_updated": True,
        "feedback_applied": feedback,
        "gemini_active": is_gemini_configured()
    })

@router.get("/view-all-users", response_class=HTMLResponse)
async def get_all_users_page(request: Request, db: Session = Depends(get_db)):
    """Admin / Project Demonstration page listing all registered users and their generated plans."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(request=request, name="all_users.html", context={
        "users": users,
        "total_users": len(users),
        "gemini_active": is_gemini_configured()
    })


# ==========================================
# REST API: AUTHENTICATION & USER MANAGEMENT
# ==========================================

@router.post("/api/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def api_register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user, hashes the password with bcrypt, and creates DB record."""
    existing_user = db.query(User).filter(
        (User.username == user_in.username.strip()) | 
        (User.email == user_in.email.strip().lower()) |
        (User.user_id == user_in.username.strip())
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is already registered."
        )

    db_user = User(
        user_id=user_in.username.strip(),
        username=user_in.username.strip(),
        email=user_in.email.strip().lower(),
        hashed_password=get_password_hash(user_in.password),
        age=user_in.age,
        weight=user_in.weight,
        goal=user_in.goal,
        intensity=user_in.intensity,
        tier="free",
        subscription_status="free",
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/api/auth/login", response_model=Token)
async def api_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 password flow endpoint returning a secure JWT access token."""
    identifier = form_data.username.strip()
    user = db.query(User).filter(
        (User.username == identifier) | (User.email == identifier.lower()) | (User.user_id == identifier)
    ).first()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive."
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )

@router.post("/api/auth/login-json", response_model=Token)
async def api_login_json(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """JSON-based login endpoint for frontend AJAX and REST auth requests."""
    identifier = credentials.get_identifier()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is required."
        )

    user = db.query(User).filter(
        (User.username == identifier) | (User.email == identifier.lower()) | (User.user_id == identifier)
    ).first()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password."
        )

    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive."
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )

@router.get("/api/auth/me", response_model=UserOut)
async def api_get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Retrieves current logged-in user profile, metrics, tier, and generated plans."""
    return current_user


# ==========================================
# REST API: STRIPE BILLING & MONETIZATION
# ==========================================

@router.get("/api/billing/status", response_model=SubscriptionStatusResponse)
async def api_get_billing_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns current athlete subscription tier and monthly usage limits."""
    plans_used = count_monthly_generated_plans(db, current_user.user_id)
    is_pro = (current_user.tier == "pro" and current_user.subscription_status == "active")

    return SubscriptionStatusResponse(
        tier=current_user.tier,
        subscription_status=current_user.subscription_status,
        monthly_plans_used=plans_used,
        monthly_limit=None if is_pro else settings.FREE_TIER_MONTHLY_LIMIT,
        is_unlimited=is_pro
    )

@router.post("/api/billing/create-checkout-session", response_model=CheckoutSessionResponse)
async def api_create_checkout_session(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates a Stripe Checkout Session for upgrading to FitBuddy Pro."""
    base_url = str(request.base_url).rstrip('/')
    success_url = f"{base_url}/dashboard?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/dashboard?canceled=true"

    session_data = create_stripe_checkout_session(current_user, success_url, cancel_url)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to initiate Stripe checkout session."
        )

    return CheckoutSessionResponse(
        checkout_url=session_data["url"],
        session_id=session_data["id"]
    )

@router.post("/api/billing/webhook")
async def api_stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Receives and processes asynchronous Stripe Webhooks."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    event = verify_and_construct_webhook_event(payload, sig_header)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook payload/signature")

    event_type = event.get("type", "")
    data_object = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        user_id = data_object.get("client_reference_id") or data_object.get("metadata", {}).get("user_id")
        customer_id = data_object.get("customer")
        subscription_id = data_object.get("subscription")

        if user_id:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                user.tier = "pro"
                user.subscription_status = "active"
                user.stripe_customer_id = customer_id
                user.subscription_id = subscription_id
                db.commit()

    elif event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
        customer_id = data_object.get("customer")
        sub_status = data_object.get("status", "canceled")

        if customer_id:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if user:
                user.subscription_status = sub_status
                if sub_status != "active":
                    user.tier = "free"
                else:
                    user.tier = "pro"
                db.commit()

    return {"status": "success", "event": event_type}


# ==========================================
# REST API: SOCIAL COMMUNITY & LEADERBOARD
# ==========================================

@router.get("/api/community/plans", response_model=List[PublicPlanOut])
async def api_get_community_plans(
    goal: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Returns public community-shared workout routines."""
    query = db.query(Plan).filter(Plan.is_public == True)
    if goal:
        query = query.join(User).filter(User.goal.ilike(f"%{goal}%"))

    public_plans = query.order_by(Plan.like_count.desc(), Plan.created_at.desc()).limit(50).all()

    my_liked_plan_ids = set()
    if current_user:
        my_likes = db.query(PlanLike.plan_id).filter(PlanLike.user_id == current_user.user_id).all()
        my_liked_plan_ids = {like[0] for like in my_likes}

    results = []
    for p in public_plans:
        author = p.user
        results.append(PublicPlanOut(
            id=p.id,
            user_id=p.user_id,
            author_username=author.username if author else "Athlete",
            author_tier=author.tier if author else "free",
            goal=author.goal if author else "General Fitness",
            intensity=author.intensity if author else "Medium",
            original_plan=p.original_plan,
            updated_plan=p.updated_plan,
            nutrition_tip=p.nutrition_tip,
            like_count=p.like_count,
            is_liked_by_me=(p.id in my_liked_plan_ids),
            created_at=p.created_at
        ))
    return results

@router.post("/api/plans/{plan_id}/toggle-public", response_model=PlanResponse)
async def api_toggle_plan_public(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggles a plan's visibility between private and public community feed."""
    plan = get_user_plan_by_id(db, current_user.user_id, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found or does not belong to current user."
        )

    plan.is_public = not plan.is_public
    db.commit()
    db.refresh(plan)
    return plan

@router.post("/api/plans/{plan_id}/like")
async def api_like_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Likes or un-likes a public plan."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    existing_like = db.query(PlanLike).filter(
        PlanLike.user_id == current_user.user_id,
        PlanLike.plan_id == plan_id
    ).first()

    if existing_like:
        db.delete(existing_like)
        plan.like_count = max(0, plan.like_count - 1)
        db.commit()
        return {"liked": False, "like_count": plan.like_count}
    else:
        new_like = PlanLike(user_id=current_user.user_id, plan_id=plan_id)
        db.add(new_like)
        plan.like_count += 1
        db.commit()
        return {"liked": True, "like_count": plan.like_count}

@router.get("/api/community/leaderboard", response_model=List[LeaderboardEntry])
async def api_get_leaderboard(db: Session = Depends(get_db)):
    """Returns top active users ranked by current streak and completion percentage."""
    users = db.query(User).filter(User.is_active == True).all()

    leaderboard_data = []
    for u in users:
        stats = calculate_user_streak(db, u.user_id)
        if stats["total_completed"] > 0:
            leaderboard_data.append({
                "username": u.username,
                "user_id": u.user_id,
                "tier": u.tier,
                "current_streak": stats["current_streak"],
                "longest_streak": stats["longest_streak"],
                "total_completed": stats["total_completed"],
                "completion_rate": stats["completion_rate"]
            })

    # Sort by current streak descending, then completion rate
    leaderboard_data.sort(key=lambda x: (x["current_streak"], x["total_completed"], x["completion_rate"]), reverse=True)

    ranked_entries = []
    for rank, entry in enumerate(leaderboard_data[:20], start=1):
        ranked_entries.append(LeaderboardEntry(rank=rank, **entry))

    return ranked_entries


# ==========================================
# REST API: PROGRESS TRACKING & STREAKS
# ==========================================

@router.get("/api/users/streak", response_model=StreakSummary)
async def api_get_user_streak(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Protected Endpoint: Calculates current and longest workout streak, total completions, and rate."""
    stats = calculate_user_streak(db, current_user.user_id)
    return StreakSummary(**stats)

@router.post("/api/plans/{plan_id}/toggle-day/{day_number}", response_model=ToggleDayResponse)
async def api_toggle_plan_day(
    plan_id: int,
    day_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Protected Endpoint: Toggles completion state for Day 1 through Day 7 in a user's plan."""
    if day_number < 1 or day_number > 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Day number must be between 1 and 7."
        )

    plan = get_user_plan_by_id(db, current_user.user_id, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found or unauthorized."
        )

    completed, log_record = toggle_workout_day(db, current_user.user_id, plan_id, day_number)
    
    return ToggleDayResponse(
        plan_id=plan_id,
        day_number=day_number,
        completed=completed,
        log=WorkoutLogOut.model_validate(log_record) if log_record else None,
        message=f"Day {day_number} marked as {'completed' if completed else 'incomplete'}."
    )


# ==========================================
# REST API: PDF EXPORT
# ==========================================

@router.get("/api/plans/{plan_id}/pdf")
def api_download_plan_pdf(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Protected Endpoint: Streams a stylized ReportLab PDF of the requested workout program.
    
    Defined synchronously (`def`) so FastAPI offloads ReportLab CPU execution to an external worker thread pool.
    """
    plan = get_user_plan_by_id(db, current_user.user_id, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found or unauthorized."
        )

    pdf_buffer = generate_plan_pdf(plan, current_user)
    filename = f"FitBuddy_Plan_{current_user.username}_DaySplit_{plan.id}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\""
        }
    )



# ==========================================
# REST API: PROTECTED FITNESS & PLAN ENDPOINTS
# ==========================================

@router.get("/api/plans", response_model=List[PlanResponse])
async def api_get_saved_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Protected Endpoint: Returns all saved plans for the authenticated user ordered newest first."""
    plans = get_user_plans(db, current_user.user_id)
    return plans

@router.get("/api/plans/{plan_id}", response_model=PlanResponse)
async def api_get_saved_plan_detail(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Protected Endpoint: Retrieves a single plan belonging strictly to the authenticated user."""
    plan = get_user_plan_by_id(db, current_user.user_id, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found or unauthorized access."
        )
    return plan

@router.delete("/api/plans/{plan_id}")
async def api_delete_saved_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Protected Endpoint: Deletes a specific saved workout plan from user history."""
    success = delete_user_plan(db, current_user.user_id, plan_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found or does not belong to the current user."
        )
    return {"status": "success", "message": f"Plan #{plan_id} deleted successfully."}

@router.post("/api/generate", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def api_generate_plan(
    plan_req: Optional[GeneratePlanRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Protected Endpoint: Generates a personalized 7-day plan with Tier Quota Enforcement."""
    # Check Usage Cap for Free Tier Users
    is_pro = (current_user.tier == "pro" and current_user.subscription_status == "active")
    if not is_pro:
        used_this_month = count_monthly_generated_plans(db, current_user.user_id)
        if used_this_month >= settings.FREE_TIER_MONTHLY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Monthly Free Tier limit reached ({settings.FREE_TIER_MONTHLY_LIMIT} plans/month). Upgrade to FitBuddy Pro for unlimited generations."
            )

    age = (plan_req.age if plan_req and plan_req.age is not None else current_user.age) or 25
    weight = (plan_req.weight if plan_req and plan_req.weight is not None else current_user.weight) or 70.0
    goal = plan_req.get_resolved_goal(current_user.goal or "General Fitness") if plan_req else (current_user.goal or "General Fitness")
    intensity = plan_req.get_resolved_intensity(current_user.intensity or "Medium") if plan_req else (current_user.intensity or "Medium")

    current_user.age = age
    current_user.weight = weight
    current_user.goal = goal
    current_user.intensity = intensity
    db.commit()

    user_dict = {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "age": age,
        "weight": weight,
        "goal": goal,
        "intensity": intensity
    }

    # Generate via Gemini AI (or fallback)
    workout_plan_text = generate_workout_plan(user_dict)
    nutrition_tip_text = generate_nutrition_tip(user_dict)

    # Save Plan Record
    plan_record = Plan(
        user_id=current_user.user_id,
        original_plan=workout_plan_text,
        nutrition_tip=nutrition_tip_text,
        is_public=False
    )
    db.add(plan_record)
    db.commit()
    db.refresh(plan_record)

    return plan_record

@router.post("/api/feedback", response_model=PlanResponse)
async def api_submit_feedback(
    feedback_in: FeedbackSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Protected Endpoint: Submits feedback to recalibrate the user's latest plan with Gemini AI."""
    latest_plan = db.query(Plan).filter(Plan.user_id == current_user.user_id).order_by(Plan.created_at.desc()).first()
    if not latest_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No workout plan found to adjust. Generate a plan first."
        )

    user_dict = {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "age": current_user.age or 25,
        "weight": current_user.weight or 70.0,
        "goal": current_user.goal or "General Fitness",
        "intensity": current_user.intensity or "Medium"
    }

    base_plan = latest_plan.original_plan
    updated_plan_text = update_workout_plan(base_plan, feedback_in.feedback, user_dict)

    # Update DB record
    latest_plan.updated_plan = updated_plan_text
    latest_plan.feedback = feedback_in.feedback
    db.commit()
    db.refresh(latest_plan)

    return latest_plan


# ==========================================
# GENERAL / ADMIN / HEALTH ENDPOINTS
# ==========================================

@router.get("/api/health", response_model=HealthResponse)
async def api_health_check():
    """Health check endpoint providing system status and Gemini configuration status."""
    return HealthResponse(
        status="healthy",
        project=settings.PROJECT_NAME,
        gemini_configured=is_gemini_configured(),
        version="1.1.0"
    )

@router.get("/api/users", response_model=List[UserResponse])
async def api_get_all_users(db: Session = Depends(get_db)):
    """API endpoint to get list of all users and their associated plans."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users

@router.get("/api/users/{user_id}/plan", response_model=PlanResponse)
async def api_get_user_latest_plan(user_id: str, db: Session = Depends(get_db)):
    """API endpoint to get the latest plan for a given user ID."""
    latest_plan = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.created_at.desc()).first()
    if not latest_plan:
        raise HTTPException(status_code=404, detail="No plan found for this user ID")
    return latest_plan
