import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from main import load_manifesto, main, example_create_pr_only, example_merge_pr, notification_callback

def test_load_manifesto():
    """Test that load_manifesto works correctly."""
    assert load_manifesto() == expected
# ... more tests for other functions in main.py ...