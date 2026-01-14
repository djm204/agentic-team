import pytest
from path.to.sentry_engine import SentryEngine

def test_sentry_engine():
    """Test that SentryEngine works correctly."""
    engine = SentryEngine()
    sanitized = engine.sanitize("My SIN is 123-456-789 and UCI is 1234567890")
    assert sanitized == "My SIN is ***-***-*** and UCI is **********"