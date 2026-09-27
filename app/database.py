from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import settings

def utc_now():
    """Returns a timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)

# Create database engine
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    age = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    goal = Column(String(100), nullable=True)
    intensity = Column(String(50), nullable=True)
    
    # Stripe Monetization Fields
    tier = Column(String(20), default="free", nullable=False) # "free" or "pro"
    stripe_customer_id = Column(String(100), nullable=True)
    subscription_id = Column(String(100), nullable=True)
    subscription_status = Column(String(50), default="free", nullable=False) # "free", "active", "past_due", "canceled"

    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    plans = relationship("Plan", back_populates="user", cascade="all, delete-orphan", order_by="desc(Plan.created_at)")
    workout_logs = relationship("WorkoutLog", back_populates="user", cascade="all, delete-orphan", order_by="desc(WorkoutLog.completed_at)")
    likes = relationship("PlanLike", back_populates="user", cascade="all, delete-orphan")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    original_plan = Column(Text, nullable=False)
    updated_plan = Column(Text, nullable=True)
    nutrition_tip = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    
    # Community & Social Fields
    is_public = Column(Boolean, default=False, nullable=False, index=True)
    like_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("User", back_populates="plans")
    workout_logs = relationship("WorkoutLog", back_populates="plan", cascade="all, delete-orphan")
    likes = relationship("PlanLike", back_populates="plan", cascade="all, delete-orphan")

class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    day_number = Column(Integer, nullable=False) # Day 1 to Day 7
    completed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'plan_id', 'day_number', name='uix_user_plan_day'),
    )

    # Relationships
    user = relationship("User", back_populates="workout_logs")
    plan = relationship("Plan", back_populates="workout_logs")

class PlanLike(Base):
    __tablename__ = "plan_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        UniqueConstraint('user_id', 'plan_id', name='uix_user_plan_like'),
    )

    # Relationships
    user = relationship("User", back_populates="likes")
    plan = relationship("Plan", back_populates="likes")


def init_db():
    """Initializes the database by creating all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_plans(db: SessionLocal, user_id: str) -> List[Plan]:
    """Fetches all historical plans for a user ordered by newest first."""
    return db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.created_at.desc()).all()

def get_user_plan_by_id(db: SessionLocal, user_id: str, plan_id: int) -> Optional[Plan]:
    """Fetches a single specific plan belonging to a user."""
    return db.query(Plan).filter(Plan.id == plan_id, Plan.user_id == user_id).first()

def delete_user_plan(db: SessionLocal, user_id: str, plan_id: int) -> bool:
    """Deletes a plan if it belongs to the given user."""
    plan = get_user_plan_by_id(db, user_id, plan_id)
    if not plan:
        return False
    db.delete(plan)
    db.commit()
    return True

def toggle_workout_day(db: SessionLocal, user_id: str, plan_id: int, day_number: int) -> Tuple[bool, Optional[WorkoutLog]]:
    """Toggles completion for a plan day."""
    existing_log = db.query(WorkoutLog).filter(
        WorkoutLog.user_id == user_id,
        WorkoutLog.plan_id == plan_id,
        WorkoutLog.day_number == day_number
    ).first()

    if existing_log:
        db.delete(existing_log)
        db.commit()
        return False, None
    else:
        new_log = WorkoutLog(
            user_id=user_id,
            plan_id=plan_id,
            day_number=day_number,
            completed_at=utc_now()
        )
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        return True, new_log

def calculate_user_streak(db: SessionLocal, user_id: str) -> dict:
    """Calculates current streak, longest streak, total workouts completed, and overall completion statistics."""
    logs = db.query(WorkoutLog).filter(WorkoutLog.user_id == user_id).order_by(WorkoutLog.completed_at.desc()).all()
    total_completed = len(logs)
    
    total_plans = db.query(Plan).filter(Plan.user_id == user_id).count()
    total_possible_workouts = total_plans * 7
    completion_rate = round((total_completed / total_possible_workouts * 100), 1) if total_possible_workouts > 0 else 0.0

    if not logs:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "total_completed": 0,
            "total_plans": total_plans,
            "completion_rate": 0.0,
            "active_today": False
        }

    # Extract distinct active calendar dates in UTC
    active_dates = sorted({log.completed_at.date() for log in logs}, reverse=True)
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    active_today = today in active_dates

    current_streak = 0
    if active_today or (yesterday in active_dates):
        expected_date = today if active_today else yesterday
        for d in active_dates:
            if d == expected_date:
                current_streak += 1
                expected_date -= timedelta(days=1)
            elif d < expected_date:
                break

    longest_streak = 0
    temp_streak = 0
    sorted_asc_dates = sorted(active_dates)
    if sorted_asc_dates:
        temp_streak = 1
        longest_streak = 1
        for i in range(1, len(sorted_asc_dates)):
            if sorted_asc_dates[i] == sorted_asc_dates[i - 1] + timedelta(days=1):
                temp_streak += 1
                if temp_streak > longest_streak:
                    longest_streak = temp_streak
            else:
                temp_streak = 1

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_completed": total_completed,
        "total_plans": total_plans,
        "completion_rate": completion_rate,
        "active_today": active_today
    }

def count_monthly_generated_plans(db: SessionLocal, user_id: str) -> int:
    """Returns number of plans created by the user in the current calendar month."""
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    return db.query(Plan).filter(Plan.user_id == user_id, Plan.created_at >= month_start).count()
