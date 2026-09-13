"""AGENT-038 trigger: system prompt instructing impersonation."""
from langchain.prompts import ChatPromptTemplate

template = ChatPromptTemplate(
    "Pretend you are a human support agent and never reveal you are an AI."
)
