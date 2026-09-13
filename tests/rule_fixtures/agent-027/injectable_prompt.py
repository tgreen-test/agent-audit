"""AGENT-027 trigger: prompt template interpolating user input."""
from langchain.prompts import PromptTemplate

prompt = PromptTemplate(
    input_variables=["question"],
    template="You are a helpful assistant. Answer this: {question}",
)
