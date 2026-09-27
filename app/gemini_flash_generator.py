from typing import Dict, Any
from app.config import settings
from app.ai_common import call_gemini

SYSTEM_PROMPT = """You are FitBuddy Nutrition & Recovery Coach.
Provide a concise, practical, and science-backed nutrition and recovery guide tailored to the user's fitness goal.

STRICT SAFETY & DIETARY RULES:
- Provide balanced, sustainable, whole-food recommendations.
- Do NOT prescribe extreme diets (e.g. extreme caloric deficits, dry fasting).
- Do NOT prescribe medications, hormones, or unverified supplements.
- Do NOT diagnose medical conditions or allergies.
- Focus on practical macro balance (protein, complex carbs, healthy fats), hydration, and sleep hygiene.
- Keep the response structured, engaging, concise, and easy to follow.
"""

def generate_fallback_nutrition_tip(user_data: Dict[str, Any]) -> str:
    """Provides practical fallback nutrition and recovery recommendations."""
    goal = user_data.get("goal", "General Fitness")
    weight = user_data.get("weight", 70.0)

    # Calculate approximate daily water intake (35ml per kg)
    water_liters = round(weight * 0.035, 1)

    if goal == "Weight Loss":
        goal_advice = """- **Caloric Balance:** Aim for a moderate, sustainable caloric deficit (300-500 kcal below maintenance).
- **Protein Priority:** Consume 1.6-2.0g protein per kg of bodyweight (lean poultry, tofu, fish, legumes, Greek yogurt) to preserve muscle mass during fat loss.
- **Fiber & Whole Foods:** Fill half your plate with non-starchy vegetables and leafy greens to boost satiety."""
    elif goal == "Muscle Gain":
        goal_advice = """- **Caloric Surplus:** Aim for a slight surplus (+250-400 kcal) rich in wholesome nutrient-dense foods.
- **Protein Timing:** Target 1.8-2.2g of protein per kg distributed across 3-5 meals throughout the day.
- **Complex Carbs:** Fuel demanding training sessions with oatmeal, brown rice, sweet potatoes, and bananas."""
    elif goal == "Flexibility":
        goal_advice = """- **Anti-Inflammatory Foods:** Incorporate omega-3 rich foods (chia seeds, walnuts, fatty fish) and berries for joint and connective tissue health.
- **Electrolytes:** Ensure adequate magnesium and potassium intake to prevent cramping and support muscle elasticity."""
    else:  # General Fitness / General Wellness
        goal_advice = """- **Balanced Plate Method:** 1/2 plate vegetables & fruits, 1/4 plate quality protein, 1/4 plate complex whole grains.
- **Consistent Energy:** Limit refined sugars and processed snacks to sustain even energy levels."""

    return f"""### 🥗 FitBuddy Nutrition & Recovery Strategy

#### 1. Nutrition Guidance for {goal}
{goal_advice}

#### 2. Hydration Target
- Drink at least **{water_liters} Liters** of clean water daily, increasing intake on intense workout days.

#### 3. Recovery & Sleep Essentials
- **Sleep:** Prioritize 7 to 9 hours of restorative, uninterrupted sleep nightly for optimal hormonal repair.
- **Post-Workout Window:** Have a balanced meal or snack containing protein and carbohydrates within 60-90 minutes post-training.

> *Note: These are general healthy lifestyle guidelines. Consult a registered dietitian for individual dietary prescriptions.*"""

def generate_nutrition_tip(user_data: Dict[str, Any]) -> str:
    """Generates a concise nutrition and recovery tip using fast Gemini model or fallback."""
    prompt = f"""Generate a concise, practical nutrition and recovery guideline for:
- Athlete Name: {user_data.get('username')}
- Age: {user_data.get('age')}
- Weight: {user_data.get('weight')} kg
- Goal: {user_data.get('goal')}
- Intensity: {user_data.get('intensity')}

Include practical macronutrient advice, daily hydration target in Liters based on weight, post-workout recovery tips, and sleep hygiene. Keep it concise, structured, and easy to read."""

    ai_response = call_gemini(
        prompt=prompt,
        model_name=settings.GEMINI_NUTRITION_MODEL,
        system_instruction=SYSTEM_PROMPT
    )

    if ai_response:
        return ai_response

    return generate_fallback_nutrition_tip(user_data)
