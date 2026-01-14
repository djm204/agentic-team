import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

# Try to import, skip tests if dependencies are missing
try:
    from team import ProjectCreationTeam
    TEAM_AVAILABLE = True
except ImportError as e:
    TEAM_AVAILABLE = False
    IMPORT_ERROR = str(e)

@pytest.mark.skipif(not TEAM_AVAILABLE, reason=f"Team module not available: {IMPORT_ERROR if not TEAM_AVAILABLE else ''}")
def test_project_creation_team_init():
    """Test that ProjectCreationTeam can be initialized."""
    # Initialize with minimal required parameters
    team = ProjectCreationTeam(
        github_token=None,
        github_owner=None,
        github_repo=None,
        repo_path=".",
        auto_approve=True
    )
    assert isinstance(team, ProjectCreationTeam)
    assert team.auto_approve == True

@pytest.mark.skipif(not TEAM_AVAILABLE, reason=f"Team module not available: {IMPORT_ERROR if not TEAM_AVAILABLE else ''}")
def test_project_creation_team_metrics_engine():
    """Test that metrics engine is initialized."""
    team = ProjectCreationTeam(
        github_token=None,
        github_owner=None,
        github_repo=None,
        repo_path=".",
        auto_approve=True
    )
    assert team.metrics_engine is not None