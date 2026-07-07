"""
MindGuard Wellness Toolkit
--------------------------
Collection of deterministic wellness tools exposed through MCP.
These are intentionally rule-based so the AI agent can call them
instead of generating everything from the LLM.
"""


def breathing_exercise():
    return """
🌬 Box Breathing

• Inhale for 4 seconds
• Hold for 4 seconds
• Exhale for 4 seconds
• Hold for 4 seconds

Repeat for 5 cycles.
"""


def grounding_activity():
    return """
🌿 5-4-3-2-1 Grounding

Notice:

5 things you can see

4 things you can feel

3 things you can hear

2 things you can smell

1 thing you can taste
"""


def journal_prompt():
    return """
📝 Journal Prompt

Spend five minutes answering:

• What is affecting my peace today?

• What is one thing I can control?

• What is one small win I had today?
"""


def affirmation():
    return """
💙 Daily Affirmation

"I am doing the best I can today.

Small progress is still progress.

I deserve kindness, especially from myself."
"""


def meditation():
    return """
🧘 Five Minute Meditation

Sit comfortably.

Close your eyes.

Take slow breaths.

Focus only on your breathing.

When your mind wanders,
gently bring it back.

Continue for five minutes.
"""


def sleep_tips():
    return """
😴 Better Sleep Tips

• Avoid screens 30 minutes before bed.

• Keep your room cool and dark.

• Try sleeping at the same time each night.

• Avoid caffeine late in the evening.
"""


def gratitude_prompt():
    return """
🙏 Gratitude Exercise

Write down:

• Three things you're grateful for today.

• One person you appreciate.

• One thing you're looking forward to tomorrow.
"""


def activity_suggestion(level):

    level = level.lower()

    if level == "low":
        return """
🚶 Activity Suggestion

Take a slow 10-minute walk.

Stretch gently.

Drink some water.
"""

    elif level == "medium":
        return """
🚶 Activity Suggestion

Go for a 20-minute walk.

Do light yoga.

Listen to calming music.
"""

    return """
🏃 Activity Suggestion

Try:

• Cycling

• Jogging

• Dancing

• A short workout
"""


def stress_relief():
    return """
🌸 Quick Stress Relief

• Relax your shoulders.

• Unclench your jaw.

• Take five slow breaths.

• Drink a glass of water.

• Step away from your screen for five minutes.
"""


def therapist_finder():
    return """
📍 Future Feature

MindGuard AI will soon be able to recommend nearby licensed therapists and mental health professionals based on:

• your location

• your consent

• your preferred language

This feature is currently under development.
"""