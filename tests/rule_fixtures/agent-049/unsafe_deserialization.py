"""AGENT-049 trigger: untrusted data through an executing deserializer."""
import pickle


def load_agent_memory(path: str):
    with open(path, "rb") as handle:
        return pickle.load(handle)
