```python
# tests/test_main.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from main import load_manifesto, main, example_create_pr_only, example_merge_pr, notification_callback

def test_load_manifesto():
    """Test that load_manifesto works correctly."""
    expected = 'expected_manifesto_output'
    assert load_manifesto() == expected

def test_main():
    """Test that main function works correctly."""
    expected = 'expected_main_output'
    assert main() == expected

def test_example_create_pr_only():
    """Test that example_create_pr_only function works correctly."""
    expected = 'expected_pr_output'
    assert example_create_pr_only() == expected

def test_example_merge_pr():
    """Test that example_merge_pr function works correctly."""
    expected = 'expected_merge_output'
    assert example_merge_pr() == expected

def test_notification_callback():
    """Test that notification_callback function works correctly."""
    expected = 'expected_callback_output'
    assert notification_callback() == expected
```