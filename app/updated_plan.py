from typing import Dict, Any
from app.config import settings
from app.ai_common import call_gemini

SYSTEM_PROMPT = """You are FitBuddy AI Plan Adapter.
Your task is to revise an existing 7-day workout plan based on the athlete's specific feedback and current profile.

CRITICAL INSTRUCTIONS:
- Review the original plan, athlete's fitness profile, and feedback carefully.
- Modify the 7-day plan directly addressing the athlete's feedback (e.g., make easier/harder, swap gym exercises for home/bodyweight variations, adjust cardio, add recovery days).
- DO NOT blindly execute dangerous or medically harmful requests. If a request is extreme, adjust it to a safe and balanced modification.
- Maintain full 7-day structure (DAY 1 through DAY 7) with warm-up, exercises with sets/reps, rest guidance, and cooldown.
- Retain the safety disclaimer at the end.
"""

def generate_fallback_updated_plan(original_plan: str, feedback: str, user_data: Dict[str, Any]) -> str:
    """Generates an adjusted plan based on common feedback keywords when API is unavailable."""
    name = user_data.get("username", "Athlete")
    feedback_lower = feedback.lower()

    adjustment_note = f"Updated based on your feedback: *\"{feedback}\"*"

    # Simple smart modifications for fallback demo
    if "home" in feedback_lower or "no equipment" in feedback_lower or "bodyweight" in feedback_lower:
        plan_flavor = "Home / Bodyweight Focused Adjustments"
    elif "easier" in feedback_lower or "light" in feedback_lower or "reduce" in feedback_lower:
        plan_flavor = "Lower Intensity & Increased Rest Intervals"
    elif "harder" in feedback_lower or "intense" in feedback_lower or "more cardio" in feedback_lower:
        plan_flavor = "Enhanced Conditioning & Cardio Integration"
    elif "recovery" in feedback_lower or "rest" in feedback_lower:
        plan_flavor = "Additional Active Recovery & Joint Mobility Days"
    else:
        plan_flavor = "Custom Refined Routine"

    return f"""### FitBuddy 7-Day Revised Plan ({plan_flavor})
**Athlete:** {name} | **Status:** Revised Plan
**User Feedback Incorporated:** {adjustment_note}

---

### DAY 1: Adapted Full-Body Training
- **Warm-up:** 5-8 mins dynamic whole-body mobility and light joint rotations.
- **Exercises & Routine:**
  1. Adjusted Squats (Tempo Bodyweight or Goblet): 3 sets of 10-12 reps
  2. Modified Push-ups (Incline/Floor): 3 sets of 8-10 reps (paced smoothly)
  3. Bodyweight Rows or Towel Pulls / Band Pulls: 3 sets of 12 reps
  4. Elevated Glute Bridges: 3 sets of 12 reps with 2-second hold at top
  5. Core Plank / Knee Plank: 3 sets of 30 seconds
- **Rest Guidance:** 60-90 seconds between sets.
- **Cooldown & Recovery:** 5 mins deep relaxed stretching.

---

### DAY 2: Targeted Conditioning / Home Cardio
- **Warm-up:** 5 mins brisk marching in place and arm swings.
- **Exercises & Routine:**
  1. Low-Impact Aerobic Intervals / Fast Walk: 25 mins (moderate sustainable pace).
  2. Standing Knee-to-Elbows: 3 sets of 12 per side.
  3. Bird-Dogs & Glute Extensions: 3 sets of 10 reps each.
  4. Supine Pelvic Tilts & Core Bracing: 3 sets of 15 reps.
- **Rest Guidance:** 45-60 seconds between exercises.
- **Cooldown & Recovery:** 5 mins restorative breathing and spine decompressions.

---

### DAY 3: Lower Body Mobility & Tone
- **Warm-up:** 5 mins hip circles and light lunges.
- **Exercises & Routine:**
  1. Split Squats / Supported Lunges: 3 sets of 8-10 reps per leg.
  2. Bodyweight Good Mornings / Romanian Band Deadlifts: 3 sets of 12 reps.
  3. Wall Sit: 3 sets of 25-35 seconds.
  4. Seated Calf Presses or Bodyweight Calf Raises: 3 sets of 15 reps.
- **Rest Guidance:** 60-75 seconds between sets.
- **Cooldown & Recovery:** 5 mins hamstring and lower back stretching.

---

### DAY 4: Dedicated Active Recovery (Adapted)
- **Warm-up:** 5 mins gentle stroll.
- **Exercises & Routine:**
  - Easy Conversational Walk or Gentle Cycling: 20-30 mins.
  - Guided Joint Mobility & Foam Rolling / Deep Stretching: 15 mins.
- **Rest Guidance:** Keep heart rate relaxed; aim for physical rejuvenation.
- **Cooldown & Recovery:** Gentle neck and shoulder releases.

---

### DAY 5: Upper Body & Core Alignment
- **Warm-up:** 5 mins arm swings, shoulder circles, and band dislocations.
- **Exercises & Routine:**
  1. Pike Push-ups / Band Overhead Press: 3 sets of 8-10 reps.
  2. Doorframe Rows / Resistance Band Rows: 3 sets of 12 reps.
  3. Chair / Bench Tricep Dips: 3 sets of 10 reps.
  4. Dumbbell or Water-Bottle Bicep Curls: 3 sets of 12 reps.
  5. Dead Bugs: 3 sets of 10 reps per side.
- **Rest Guidance:** 60-90 seconds between sets.
- **Cooldown & Recovery:** 5 mins chest opening and lat stretch.

---

### DAY 6: Low-Impact Functional Movement
- **Warm-up:** 5 mins torso twists and dynamic side reaches.
- **Exercises & Routine:**
  1. Step-Back Lunges to Knee Drive: 3 sets of 10 per leg.
  2. Shadow Boxing / Aerobic Agility: 15 mins of rhythmic movement.
  3. Russian Twists (bodyweight): 3 sets of 16 total.
  4. Supermans (lower back & posterior chain): 3 sets of 12 reps.
- **Rest Guidance:** 60 seconds rest between circuits.
- **Cooldown & Recovery:** 5 mins child's pose and cobra stretch.

---

### DAY 7: Rest, Regeneration & Hydration
- **Warm-up:** None.
- **Exercises & Routine:**
  - Full Rest & Rejuvenation.
  - Hydration focus and healthy nutrient replenishment.
- **Rest Guidance:** Complete rest for optimal adaptation.
- **Cooldown & Recovery:** Deep sleep and stress reduction.

---
> **Safety & Medical Disclaimer:** This revised plan has been adjusted for fitness preferences. If any movement causes discomfort, stop immediately and seek advice from a licensed fitness or medical specialist."""

def update_workout_plan(original_plan: str, feedback: str, user_data: Dict[str, Any]) -> str:
    """Updates an existing workout plan using Gemini based on feedback with fallback."""
    prompt = f"""Here is the athlete's current fitness profile:
- Name: {user_data.get('username')}
- Age: {user_data.get('age')}
- Weight: {user_data.get('weight')} kg
- Goal: {user_data.get('goal')}
- Intensity: {user_data.get('intensity')}

ORIGINAL 7-DAY WORKOUT PLAN:
\"\"\"
{original_plan}
\"\"\"

ATHLETE FEEDBACK / REQUESTED CHANGES:
\"{feedback}\"

Please generate a revised, complete 7-Day Workout Plan (DAY 1 through DAY 7) modifying the routine to directly accommodate their feedback safely while maintaining effectiveness. Include the safety disclaimer at the end."""

    ai_response = call_gemini(
        prompt=prompt,
        model_name=settings.GEMINI_WORKOUT_MODEL,
        system_instruction=SYSTEM_PROMPT
    )

    if ai_response:
        return ai_response

    return generate_fallback_updated_plan(original_plan, feedback, user_data)
