from typing import Dict, Any
from app.config import settings
from app.ai_common import call_gemini

SYSTEM_PROMPT = """You are FitBuddy AI, an expert and certified fitness trainer and wellness specialist.
Your goal is to generate safe, personalized, highly structured 7-day workout plans.

CRITICAL SAFETY & MEDICAL GUIDELINES:
- You are a fitness assistant, NOT a medical doctor.
- Do NOT diagnose illnesses, prescribe medication, or give medical clearances.
- Avoid extreme or dangerous exercises.
- Always include appropriate rest/recovery.
- Include a clear, concise safety disclaimer at the end of the plan advising consultation with a healthcare professional before starting any new exercise routine.

OUTPUT FORMAT REQUIREMENTS:
Format the plan clearly with:
- Summary Overview (Target Goal, Target Intensity)
- Exactly 7 distinct Day Sections formatted as:
  ### DAY 1: [Day Title]
  - **Warm-up:** (5-10 mins dynamic movements)
  - **Exercises & Routine:** (Exercise name, Sets x Reps or Duration)
  - **Rest Guidance:** (Rest intervals between sets)
  - **Cooldown & Recovery:** (Static stretching, recovery breathing)
  (Repeat for DAY 2 through DAY 7, ensuring at least one designated Active Recovery or Rest Day).
- Safety & Form Notes.
"""

def generate_fallback_workout_plan(user_data: Dict[str, Any]) -> str:
    """Provides a safe, structured fallback 7-day workout plan if API is unavailable."""
    name = user_data.get("username", "Athlete")
    goal = user_data.get("goal", "General Fitness")
    intensity = user_data.get("intensity", "Medium")
    age = user_data.get("age", 25)
    weight = user_data.get("weight", 70.0)

    # Tailor repetitions & pace based on intensity
    reps = "3 sets of 10-12 reps" if intensity == "Medium" else ("2 sets of 8-10 reps" if intensity == "Low" else "4 sets of 12-15 reps")
    rest = "60-90 seconds" if intensity == "Medium" else ("90-120 seconds" if intensity == "Low" else "45-60 seconds")
    cardio_dur = "20-25 mins" if intensity == "Medium" else ("15 mins" if intensity == "Low" else "30-35 mins")

    return f"""### FitBuddy 7-Day Personalized Workout Plan (Fallback Mode)
**Athlete:** {name} | **Age:** {age} | **Weight:** {weight} kg | **Goal:** {goal} | **Intensity:** {intensity}

---

### DAY 1: Full-Body Foundation & Activation
- **Warm-up:** 5-7 mins dynamic arm circles, torso twists, leg swings, jumping jacks (or brisk walking).
- **Exercises & Routine:**
  1. Bodyweight Squats (or Goblet Squats): {reps}
  2. Push-ups (standard or knee-supported): {reps}
  3. Dumbbell/Resistance Band Rows: {reps}
  4. Glute Bridges: 3 sets of 12-15 reps
  5. Plank Hold: 3 sets of 30-45 seconds
- **Rest Guidance:** {rest} between sets.
- **Cooldown & Recovery:** 5 mins light hamstring, quad, and chest stretching.

---

### DAY 2: Aerobic Conditioning & Core Stability
- **Warm-up:** 5 mins brisk walk or light cycling.
- **Exercises & Routine:**
  1. Steady-state Cardio (Brisk Walk / Jog / Elliptical / Cycling): {cardio_dur} at moderate pace.
  2. Bicycle Crunches: 3 sets of 15 reps per side.
  3. Bird-Dogs: 3 sets of 10 reps per side.
  4. Dead Bug: 3 sets of 12 reps.
- **Rest Guidance:** 45-60 seconds between core sets.
- **Cooldown & Recovery:** 5 mins deep breathing and child's pose.

---

### DAY 3: Lower Body Strength & Mobility
- **Warm-up:** 5 mins hip openers, ankle rotations, bodyweight lunges.
- **Exercises & Routine:**
  1. Reverse Lunges: {reps} per leg.
  2. Romanian Deadlifts (with dumbbells/bands or bodyweight): {reps}
  3. Step-ups (onto sturdy bench or step): 3 sets of 10 reps per leg.
  4. Standing Calf Raises: 3 sets of 15-20 reps.
  5. Side Plank: 3 sets of 20-30 seconds per side.
- **Rest Guidance:** {rest} between sets.
- **Cooldown & Recovery:** 5-10 mins quad, hamstring, and hip flexor stretches.

---

### DAY 4: Active Recovery & Gentle Mobility (Rest Day)
- **Warm-up:** 5 mins gentle walk.
- **Exercises & Routine:**
  1. Light Outdoor Walk: 20-30 mins at an easy, conversational pace.
  2. Full-Body Yoga / Dynamic Mobility Routine: 15 mins (Cat-Cow, Downward Dog, Cobra Stretch, World's Greatest Stretch).
- **Rest Guidance:** Keep exertion low; focus on muscle relaxation and joint mobility.
- **Cooldown & Recovery:** 5 mins guided mindfulness or relaxed deep breathing.

---

### DAY 5: Upper Body Strength & Posture
- **Warm-up:** 5 mins shoulder rolls, band pull-aparts, light shadow boxing.
- **Exercises & Routine:**
  1. Overhead Dumbbell Shoulder Press (or Pike Push-ups): {reps}
  2. Single-Arm Dumbbell Rows (or Inverted Rows): {reps}
  3. Incline Push-ups or Chest Press: {reps}
  4. Bicep Curls superset with Tricep Dips: 3 sets of 12 reps each.
  5. Reverse Flyes / Face Pulls: 3 sets of 15 reps.
- **Rest Guidance:** {rest} between sets.
- **Cooldown & Recovery:** 5 mins chest door-frame stretch and upper back foam rolling.

---

### DAY 6: Metabolic Conditioning & Functional Agility
- **Warm-up:** 5 mins high knees, butt kicks, dynamic side lunges.
- **Exercises & Routine:**
  1. Interval Cardio / Fast Walk or Interval Jogging: 20 mins (1 min moderate, 30s brisk).
  2. Kettlebell / Dumbbell Swings: 3 sets of 15 reps.
  3. Mountain Climbers: 3 sets of 30 seconds.
  4. Russian Twists: 3 sets of 20 total twists.
- **Rest Guidance:** 60 seconds between circuits.
- **Cooldown & Recovery:** 5 mins full body cool-down stretching.

---

### DAY 7: Complete Rest, Hydration & Weekly Reset
- **Warm-up:** None required.
- **Exercises & Routine:**
  - Dedicated Rest Day: Allow muscles to repair and glycogen stores to replenish.
  - Optional light stretching: 10 mins before bed.
- **Rest Guidance:** Prioritize 7-9 hours of quality sleep and balanced nutrition.
- **Cooldown & Recovery:** Hydrate well with water and herbal teas.

---
> **Safety & Medical Disclaimer:** This fitness plan is generated for general wellness and educational purposes only. Always consult with a physician or qualified healthcare provider before beginning any new exercise regimen, especially if you have pre-existing health conditions or injuries. Discontinue exercise immediately if you experience pain, dizziness, or shortness of breath.
"""

def generate_workout_plan(user_data: Dict[str, Any]) -> str:
    """Generates a complete 7-day workout plan using Gemini with fallback support."""
    prompt = f"""Generate a personalized 7-Day Workout Plan for this individual:
- Name: {user_data.get('username')}
- Age: {user_data.get('age')} years old
- Current Weight: {user_data.get('weight')} kg
- Primary Fitness Goal: {user_data.get('goal')}
- Requested Workout Intensity: {user_data.get('intensity')}

Please structure the 7-day plan with DAY 1 through DAY 7, warm-up, exercises with sets/reps/durations, rest guidance, and cooldown for each day. Ensure at least one rest/recovery day. Include the mandatory safety disclaimer at the end."""

    ai_response = call_gemini(
        prompt=prompt,
        model_name=settings.GEMINI_WORKOUT_MODEL,
        system_instruction=SYSTEM_PROMPT
    )

    if ai_response:
        return ai_response

    return generate_fallback_workout_plan(user_data)
