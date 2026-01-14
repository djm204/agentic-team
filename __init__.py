"""
Agentic Project Creation Team - A reusable CrewAI team for creating projects from manifestos.
"""
from team import ProjectCreationTeam
from github_utils import GitHubManager, GitManager
from file_utils import write_files_from_implementation, parse_implementation_to_files
from notifications import NotificationManager, NotificationType, ApprovalCheckpoint
from context_manager import ContextManager
from technical_hurdles import HurdleDetector, TechnicalHurdle, HurdleSeverity
from discord_integration import DiscordIntegration, DiscordStreamingHandler, DiscordMessageType
from agent_collaboration import (
    StandupManager, PeerReviewSystem, AgentManager,
    AgentRecord, AgentPerformance, AgentStatus
)
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
