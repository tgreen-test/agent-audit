"""AGENT-052 trigger: credential interpolated into a log statement."""
import logging

logger = logging.getLogger(__name__)


def authenticate(username: str, password: str) -> None:
    logger.info(f"authenticating {username} with password={password}")
