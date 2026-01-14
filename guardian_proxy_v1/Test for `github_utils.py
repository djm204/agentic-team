```python
# tests/test_github_utils.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from github_utils import GitHubManager, GitManager

def test_GitHubManager_init():
    """Test that GitHubManager is initialized correctly."""
    gh_manager = GitHubManager('test_token')
    assert isinstance(gh_manager, GitHubManager)

def test_GitManager_init():
    """Test that GitManager is initialized correctly."""
    git_manager = GitManager('test_repo')
    assert isinstance(git_manager, GitManager)

#... More tests for other methods in GitHubManager and GitManager classes ...
```

You would continue this pattern for other modules and their functions. Tests for `main.py` and `github_utils.py` are shown here for brevity, but you should write similar tests for all other modules.

Ensure all tests pass before code is merged. Run tests using `pytest` command and generate a report using `pytest-cov`. Make sure to aim for a test coverage >80%. 

After running these tests, you would get a result showing the number of tests passed/failed. If any tests fail, debug them and ensure all tests pass before marking the task as complete. 

Remember to follow DRY principles, prioritize simplicity and elegance in your code, and aim for a high level of human readability. Also, ensure proper handling of PII and implementation of security best practices.