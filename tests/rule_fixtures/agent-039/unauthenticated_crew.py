"""AGENT-039 trigger: multi-agent setup without inter-agent authentication."""
from crewai import Crew

crew = Crew(
    agents=[researcher_agent, writer_agent, reviewer_agent],
    tasks=[research_task, write_task],
)
