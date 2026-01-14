"""
Pytest configuration file.
This file is automatically loaded by pytest before collecting tests.
It sets up the Python path so tests can import modules from the parent directory.
"""
import sys
import os

# Add the parent directory to Python path so tests can import modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
