"""
Agentic Project Creation Team - A reusable CrewAI team for creating projects from manifestos.
"""
# Make crewai-dependent imports optional to allow tests to run without crewai
try:
    from team import ProjectCreationTeam
except ImportError:
    ProjectCreationTeam = None

# Make optional dependencies optional to allow tests to run without them
try:
    from github_utils import GitHubManager, GitManager
except ImportError:
    GitHubManager = None
    GitManager = None

try:
    from file_utils import write_files_from_implementation, parse_implementation_to_files
except ImportError:
    write_files_from_implementation = None
    parse_implementation_to_files = None

from notifications import NotificationManager, NotificationType, ApprovalCheckpoint

try:
    from context_manager import ContextManager
except ImportError:
    ContextManager = None

try:
    from technical_hurdles import HurdleDetector, TechnicalHurdle, HurdleSeverity
except ImportError:
    HurdleDetector = None
    TechnicalHurdle = None
    HurdleSeverity = None

try:
    from discord_integration import DiscordIntegration, DiscordStreamingHandler, DiscordMessageType
except ImportError:
    DiscordIntegration = None
    DiscordStreamingHandler = None
    DiscordMessageType = None

try:
    from agent_collaboration import (
        StandupManager, PeerReviewSystem, AgentManager,
        AgentRecord, AgentPerformance, AgentStatus
    )
except ImportError:
    StandupManager = None
    PeerReviewSystem = None
    AgentManager = None
    AgentRecord = None
    AgentPerformance = None
    AgentStatus = None

from metrics_engine import MetricsEngine, TokenTracker

__version__ = "0.2.0"
__all__ = [
    "ProjectCreationTeam",
    "GitHubManager",
    "GitManager",
    "write_files_from_implementation",
    "parse_implementation_to_files",
    "NotificationManager",
    "NotificationType",
    "ApprovalCheckpoint",
    "ContextManager",
    "HurdleDetector",
    "TechnicalHurdle",
    "HurdleSeverity",
    "DiscordIntegration",
    "DiscordStreamingHandler",
    "DiscordMessageType",
    "StandupManager",
    "PeerReviewSystem",
    "AgentManager",
    "AgentRecord",
    "AgentPerformance",
    "AgentStatus",
    "MetricsEngine",
    "TokenTracker"
]
