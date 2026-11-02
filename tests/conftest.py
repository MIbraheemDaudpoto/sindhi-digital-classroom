"""Pytest configuration and global fixtures for SDC test suite.
Authored under agency-test-automation-engineer.
"""

import pytest
from src.config import settings


@pytest.fixture(autouse=True)
def configure_test_environment():
    """Enable test query auth for unit tests while preserving isolation."""
    orig_query_auth = settings.allow_test_query_auth
    orig_env = settings.environment
    
    settings.allow_test_query_auth = True
    settings.environment = "test"
    
    yield
    
    settings.allow_test_query_auth = orig_query_auth
    settings.environment = orig_env
