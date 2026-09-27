from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict

# ==========================================
# AUTH SCHEMAS
# ==========================================

class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="Valid email address for login")
    username: str = Field(..., min_length=2, max_length=50, description="Unique username / display handle")
    password: str = Field(..., min_length=6, max_length=100, description="Secure account password")
    age: Optional[int] = Field(default=25, ge=10, le=120, description="Age in years")
    weight: Optional[float] = Field(default=70.0, ge=20.0, le=350.0, description="Weight in kilograms")
    goal: Optional[str] = Field(default="General Fitness", description="Fitness goal")
    intensity: Optional[str] = Field(default="Medium", description="Workout intensity level")

    @field_validator("intensity")
    @classmethod
    def validate_intensity(cls, v: Optional[str]) -> str:
        if v is None:
            return "Medium"
        allowed = ["Low", "Medium", "High"]
        clean = v.strip().capitalize()
        if clean not in allowed:
            return "Medium"
        return clean

class UserLogin(BaseModel):
    username_or_email: Optional[str] = Field(None, description="Username or Email address")
    username: Optional[str] = Field(None, description="Username alias")
    email: Optional[str] = Field(None, description="Email alias")
    password: str = Field(..., description="Account password")

    def get_identifier(self) -> str:
        ident = self.username_or_email or self.username or self.email
        return ident.strip() if ident else ""

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional["UserOut"] = None

class TokenData(BaseModel):
    username: Optional[str] = None

# ==========================================
# STRIPE BILLING & TIER SCHEMAS
# ==========================================

class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str

class SubscriptionStatusResponse(BaseModel):
    tier: str
    subscription_status: str
    monthly_plans_used: int
    monthly_limit: Optional[int] = None
    is_unlimited: bool

# ==========================================
# WORKOUT LOG & PROGRESS SCHEMAS
# ==========================================

class WorkoutLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    plan_id: int
    day_number: int
    completed_at: datetime
    notes: Optional[str] = None

class WorkoutLogCreate(BaseModel):
    notes: Optional[str] = Field(None, max_length=500)

class ToggleDayResponse(BaseModel):
    plan_id: int
    day_number: int
    completed: bool
    log: Optional[WorkoutLogOut] = None
    message: str

class StreakSummary(BaseModel):
    current_streak: int = Field(..., description="Current consecutive active workout days")
    longest_streak: int = Field(..., description="Personal record for consecutive active days")
    total_completed: int = Field(..., description="Total completed workout days across all plans")
    total_plans: int = Field(..., description="Total fitness plans generated")
    completion_rate: float = Field(..., description="Percentage of total workouts completed")
    active_today: bool = Field(..., description="Whether user completed a workout today")

# ==========================================
# COMMUNITY & LEADERBOARD SCHEMAS
# ==========================================

class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    user_id: str
    tier: str
    current_streak: int
    longest_streak: int
    total_completed: int
    completion_rate: float

class PublicPlanOut(BaseModel):
    id: int
    user_id: str
    author_username: str
    author_tier: str
    goal: str
    intensity: str
    original_plan: str
    updated_plan: Optional[str] = None
    nutrition_tip: Optional[str] = None
    like_count: int
    is_liked_by_me: bool = False
    created_at: datetime

# ==========================================
# PLAN & USER SCHEMAS
# ==========================================

class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    original_plan: str
    updated_plan: Optional[str] = None
    nutrition_tip: Optional[str] = None
    feedback: Optional[str] = None
    is_public: bool = False
    like_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    workout_logs: List[WorkoutLogOut] = []

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    username: str
    email: Optional[str] = None
    is_active: bool
    tier: str = "free"
    subscription_status: str = "free"
    age: Optional[int] = None
    weight: Optional[float] = None
    goal: Optional[str] = None
    intensity: Optional[str] = None
    created_at: datetime
    plans: List[PlanResponse] = []

class UserResponse(UserOut):
    pass

class UserProfileUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=10, le=120)
    weight: Optional[float] = Field(None, ge=20.0, le=350.0)
    goal: Optional[str] = None
    intensity: Optional[str] = None

# ==========================================
# FITNESS & GENERATOR SCHEMAS
# ==========================================

class GeneratePlanRequest(BaseModel):
    goal: Optional[str] = Field(None, description="Primary goal")
    fitness_goal: Optional[str] = Field(None, description="Alias for goal")
    intensity: Optional[str] = Field(None, description="Intensity level (Low, Medium, High)")
    fitness_level: Optional[str] = Field(None, description="Alias for intensity (Beginner, Intermediate, Advanced)")
    age: Optional[int] = Field(None, ge=10, le=120)
    weight: Optional[float] = Field(None, ge=20.0, le=350.0)
    gender: Optional[str] = None
    height: Optional[float] = None
    dietary_preference: Optional[str] = None
    workout_location: Optional[str] = None

    def get_resolved_goal(self, default_val: str = "General Fitness") -> str:
        return self.fitness_goal or self.goal or default_val

    def get_resolved_intensity(self, default_val: str = "Medium") -> str:
        val = self.intensity or self.fitness_level or default_val
        val_clean = str(val).strip().capitalize()
        if val_clean in ["Beginner", "Low"]:
            return "Low"
        elif val_clean in ["Intermediate", "Medium", "Moderate"]:
            return "Medium"
        elif val_clean in ["Advanced", "High", "Challenging"]:
            return "High"
        return default_val

class FeedbackSubmit(BaseModel):
    feedback: str = Field(..., min_length=3, max_length=1000, description="Feedback or adjustments requested")

class HealthResponse(BaseModel):
    status: str
    project: str
    gemini_configured: bool
    version: str
