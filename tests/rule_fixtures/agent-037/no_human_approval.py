"""AGENT-037 trigger: side-effect tools with no human approval."""
from langchain.agents import AgentExecutor

executor = AgentExecutor(
    agent=None,
    tools=[write_file_tool, shell_command_tool, delete_record_tool],
    verbose=True,
)
