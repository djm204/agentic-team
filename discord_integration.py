"""
Discord integration for real-time project creation updates.
"""
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
import requests
from enum import Enum


class DiscordMessageType(Enum):
    """Types of Discord messages."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    APPROVAL = "approval"


class DiscordIntegration:
    """Discord integration for real-time notifications."""
    
    def __init__(self, webhook_url: str = None):
        """
        Initialize Discord integration.
        
        Args:
            webhook_url: Discord webhook URL (or from DISCORD_WEBHOOK_URL env var)
        """
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.enabled = self.webhook_url is not None
        
        if not self.enabled:
            print("⚠️ Discord integration disabled: No webhook URL provided")
    
    def send_message(
        self,
        title: str,
        description: str,
        message_type: DiscordMessageType = DiscordMessageType.INFO,
        fields: Dict[str, str] = None,
        footer: str = None
    ) -> bool:
        """
        Send a message to Discord.
        
        Args:
            title: Message title
            description: Message description
            message_type: Type of message (affects color)
            fields: Optional fields to add
            footer: Optional footer text
        
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        # Color mapping
        colors = {
            DiscordMessageType.INFO: 0x3498db,      # Blue
            DiscordMessageType.SUCCESS: 0x2ecc71,    # Green
            DiscordMessageType.WARNING: 0xf39c12,    # Orange
            DiscordMessageType.ERROR: 0xe74c3c,      # Red
            DiscordMessageType.APPROVAL: 0x9b59b6    # Purple
        }
        
        # Emoji mapping
        emojis = {
            DiscordMessageType.INFO: "ℹ️",
            DiscordMessageType.SUCCESS: "✅",
            DiscordMessageType.WARNING: "⚠️",
            DiscordMessageType.ERROR: "❌",
            DiscordMessageType.APPROVAL: "⏸️"
        }
        
        embed = {
            "title": f"{emojis.get(message_type, '')} {title}",
            "description": description,
            "color": colors.get(message_type, 0x3498db),
            "timestamp": datetime.utcnow().isoformat(),
            "fields": []
        }
        
        # Add fields
        if fields:
            for key, value in fields.items():
                # Truncate long values
                if len(str(value)) > 1024:
                    value = str(value)[:1021] + "..."
                embed["fields"].append({
                    "name": key,
                    "value": str(value),
                    "inline": False
                })
        
        # Add footer
        if footer:
            embed["footer"] = {"text": footer}
        
        payload = {"embeds": [embed]}
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"⚠️ Failed to send Discord message: {e}")
            return False
    
    def send_planning_update(
        self,
        stage: str,
        content: str,
        progress: float = None
    ):
        """Send planning stage update."""
        description = f"**Stage:** {stage}\n\n{content[:1000]}"
        if len(content) > 1000:
            description += "\n\n*(truncated)*"
        
        fields = {}
        if progress is not None:
            fields["Progress"] = f"{progress:.1f}%"
        
        return self.send_message(
            title="Planning Update",
            description=description,
            message_type=DiscordMessageType.INFO,
            fields=fields,
            footer="Agentic Project Creation Team"
        )
    
    def send_plan_complete(self, plan: str, hurdles: list = None):
        """Send plan completion notification."""
        description = f"Development plan has been created!\n\n```\n{plan[:500]}\n```"
        if len(plan) > 500:
            description += "\n\n*(plan truncated - see full plan in approval)*"
        
        fields = {}
        if hurdles:
            critical = [h for h in hurdles if h.get("severity") in ["high", "critical"]]
            if critical:
                fields["⚠️ Critical Hurdles"] = f"{len(critical)} detected"
        
        return self.send_message(
            title="Plan Complete - Approval Required",
            description=description,
            message_type=DiscordMessageType.APPROVAL,
            fields=fields,
            footer="Waiting for your approval to proceed"
        )
    
    def send_implementation_complete(
        self,
        summary: str,
        file_count: int = 0,
        loc: int = 0
    ):
        """Send implementation completion notification."""
        description = f"Implementation complete!\n\n{summary[:500]}"
        if len(summary) > 500:
            description += "\n\n*(summary truncated)*"
        
        fields = {
            "Files Created": str(file_count),
            "Lines of Code": str(loc)
        }
        
        return self.send_message(
            title="Implementation Complete - Approval Required",
            description=description,
            message_type=DiscordMessageType.APPROVAL,
            fields=fields,
            footer="Waiting for your approval to proceed"
        )
    
    def send_test_results(self, passed: bool, test_results: str):
        """Send test results notification."""
        message_type = DiscordMessageType.SUCCESS if passed else DiscordMessageType.ERROR
        title = "Tests Passed ✅" if passed else "Tests Failed ❌"
        
        description = f"Test execution complete!\n\n```\n{test_results[:800]}\n```"
        if len(test_results) > 800:
            description += "\n\n*(results truncated)*"
        
        return self.send_message(
            title=title,
            description=description,
            message_type=message_type,
            footer="QA Testing Phase"
        )
    
    def send_pr_created(self, pr_number: int, url: str, branch: str):
        """Send PR creation notification."""
        return self.send_message(
            title="Pull Request Created",
            description=f"PR #{pr_number} has been created",
            message_type=DiscordMessageType.SUCCESS,
            fields={
                "PR Number": f"#{pr_number}",
                "Branch": branch,
                "URL": f"[View PR]({url})"
            },
            footer="GitHub Integration"
        )
    
    def send_pr_merged(self, pr_number: int, url: str):
        """Send PR merge notification."""
        return self.send_message(
            title="Pull Request Merged",
            description=f"PR #{pr_number} has been successfully merged!",
            message_type=DiscordMessageType.SUCCESS,
            fields={
                "PR Number": f"#{pr_number}",
                "URL": f"[View PR]({url})"
            },
            footer="GitHub Integration"
        )
    
    def send_technical_hurdle(self, hurdle: Dict[str, Any]):
        """Send technical hurdle notification."""
        severity = hurdle.get("severity", "medium").upper()
        issue = hurdle.get("issue", "Unknown issue")
        suggestions = hurdle.get("suggestions", [])
        
        description = f"**Severity:** {severity}\n\n**Issue:**\n{issue[:500]}"
        
        if suggestions:
            suggestions_text = "\n".join(f"• {s}" for s in suggestions[:5])
            description += f"\n\n**Suggestions:**\n{suggestions_text}"
        
        message_type = DiscordMessageType.ERROR if severity in ["HIGH", "CRITICAL"] else DiscordMessageType.WARNING
        
        return self.send_message(
            title="Technical Hurdle Detected",
            description=description,
            message_type=message_type,
            footer="Requires attention"
        )
    
    def send_real_time_update(
        self,
        agent_name: str,
        action: str,
        details: str = None
    ):
        """Send real-time update from an agent."""
        description = f"**Agent:** {agent_name}\n**Action:** {action}"
        if details:
            description += f"\n\n{details[:500]}"
        
        return self.send_message(
            title="Real-Time Update",
            description=description,
            message_type=DiscordMessageType.INFO,
            footer="Live Planning Process"
        )
    
    def send_approval_request(
        self,
        checkpoint: str,
        context: Dict[str, Any] = None
    ):
        """Send approval request notification."""
        description = f"**Checkpoint:** {checkpoint}\n\nApproval required to proceed."
        
        fields = {}
        if context:
            for key, value in list(context.items())[:5]:  # Limit to 5 fields
                if isinstance(value, str) and len(value) > 100:
                    value = value[:97] + "..."
                fields[key] = str(value)
        
        return self.send_message(
            title="Approval Required",
            description=description,
            message_type=DiscordMessageType.APPROVAL,
            fields=fields,
            footer="Please approve in the console"
        )


class DiscordStreamingHandler:
    """Handler for streaming agent actions to Discord in real-time."""
    
    def __init__(self, discord: DiscordIntegration):
        """
        Initialize streaming handler.
        
        Args:
            discord: DiscordIntegration instance
        """
        self.discord = discord
        self.current_stage = None
        self.stage_start_time = None
        self.action_count = 0
    
    def on_agent_start(self, agent_name: str, task: str):
        """Called when an agent starts working."""
        self.action_count += 1
        self.discord.send_real_time_update(
            agent_name=agent_name,
            action=f"Starting: {task}",
            details="Agent is beginning work..."
        )
        # Also send as a detailed action log
        self.log_agent_action(
            agent_name=agent_name,
            action_type="START",
            action=f"Started working on: {task}",
            details={"task": task, "action_id": self.action_count}
        )
    
    def on_agent_progress(self, agent_name: str, progress: str):
        """Called when an agent makes progress."""
        self.action_count += 1
        self.discord.send_real_time_update(
            agent_name=agent_name,
            action="In Progress",
            details=progress
        )
        # Also send as a detailed action log
        self.log_agent_action(
            agent_name=agent_name,
            action_type="PROGRESS",
            action="Making progress",
            details={"progress": progress, "action_id": self.action_count}
        )
    
    def on_agent_complete(self, agent_name: str, result: str):
        """Called when an agent completes work."""
        self.action_count += 1
        self.discord.send_real_time_update(
            agent_name=agent_name,
            action="Completed",
            details=result[:500] if result else "Task completed successfully"
        )
        # Also send as a detailed action log
        self.log_agent_action(
            agent_name=agent_name,
            action_type="COMPLETE",
            action="Completed task",
            details={"result": result[:500] if result else "Success", "action_id": self.action_count}
        )
    
    def log_agent_action(
        self,
        agent_name: str,
        action_type: str,
        action: str,
        details: Dict[str, Any] = None
    ):
        """Log any agent action to Discord."""
        if not self.discord or not self.discord.enabled:
            return
        
        action_emoji = {
            "START": "🚀",
            "PROGRESS": "⚙️",
            "COMPLETE": "✅",
            "DECISION": "🤔",
            "COLLABORATION": "🤝",
            "REVIEW": "📝",
            "ERROR": "❌",
            "WARNING": "⚠️"
        }.get(action_type, "📌")
        
        details_text = ""
        if details:
            details_items = [f"**{k}:** {v}" for k, v in list(details.items())[:5]]
            details_text = "\n".join(details_items)
        
            self.discord.send_message(
                title=f"{action_emoji} Agent Action: {agent_name}",
                description=f"**Action Type:** {action_type}\n**Action:** {action}\n\n{details_text}",
                message_type=DiscordMessageType.INFO,
                fields={
                    "Agent": agent_name,
                    "Action Type": action_type,
                    "Timestamp": datetime.utcnow().strftime("%H:%M:%S")
                },
                footer="Agent Action Log"
            )
    
    def on_stage_start(self, stage_name: str):
        """Called when a workflow stage starts."""
        self.current_stage = stage_name
        self.stage_start_time = datetime.utcnow()
        self.discord.send_message(
            title=f"Stage Started: {stage_name}",
            description=f"Beginning {stage_name} phase...",
            message_type=DiscordMessageType.INFO,
            footer="Workflow Progress"
        )
    
    def on_stage_complete(self, stage_name: str, summary: str = None):
        """Called when a workflow stage completes."""
        duration = None
        if self.stage_start_time:
            duration = (datetime.utcnow() - self.stage_start_time).total_seconds()
        
        fields = {}
        if duration:
            fields["Duration"] = f"{duration:.1f} seconds"
        
        self.discord.send_message(
            title=f"Stage Complete: {stage_name}",
            description=summary or f"{stage_name} phase completed successfully",
            message_type=DiscordMessageType.SUCCESS,
            fields=fields,
            footer="Workflow Progress"
        )
    
    def send_message(
        self,
        title: str,
        description: str,
        message_type: DiscordMessageType = DiscordMessageType.INFO,
        fields: Dict[str, str] = None,
        footer: str = None
    ) -> bool:
        """
        Send a message to Discord (delegates to DiscordIntegration).
        
        Args:
            title: Message title
            description: Message description
            message_type: Type of message (affects color)
            fields: Optional fields to add
            footer: Optional footer text
        
        Returns:
            True if sent successfully
        """
        return self.discord.send_message(
            title=title,
            description=description,
            message_type=message_type,
            fields=fields,
            footer=footer
        )
