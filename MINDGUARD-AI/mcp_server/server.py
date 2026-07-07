from mcp.server.fastmcp import FastMCP

from wellness_tools import (
    breathing_exercise,
    grounding_activity,
    journal_prompt,
    affirmation,
    meditation,
    sleep_tips,
    gratitude_prompt,
    activity_suggestion,
    stress_relief,
    therapist_finder,
)

mcp = FastMCP("mindguard_wellness_toolkit")


@mcp.tool()
def get_breathing_exercise() -> str:
    """Guided breathing exercise."""
    return breathing_exercise()


@mcp.tool()
def get_grounding_activity() -> str:
    """5-4-3-2-1 grounding exercise."""
    return grounding_activity()


@mcp.tool()
def get_journal_prompt() -> str:
    """Daily journaling prompt."""
    return journal_prompt()


@mcp.tool()
def get_affirmation() -> str:
    """Positive affirmation."""
    return affirmation()


@mcp.tool()
def get_meditation() -> str:
    """Five minute meditation."""
    return meditation()


@mcp.tool()
def get_sleep_tips() -> str:
    """Healthy sleep suggestions."""
    return sleep_tips()


@mcp.tool()
def get_gratitude_prompt() -> str:
    """Daily gratitude activity."""
    return gratitude_prompt()


@mcp.tool()
def get_activity_suggestion(level: str) -> str:
    """Suggest activity based on energy level."""
    return activity_suggestion(level)


@mcp.tool()
def get_stress_relief() -> str:
    """Quick stress relief exercise."""
    return stress_relief()


@mcp.tool()
def find_nearby_therapists() -> str:
    """Future therapist finder."""
    return therapist_finder()


if __name__ == "__main__":
    mcp.run(transport="stdio")