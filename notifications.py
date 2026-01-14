"""
Notification and approval checkpoint system.
"""
from typing import Callable, Optional, Dict, Any
from enum import Enum
import json
from datetime import datetime
import os


class NotificationType(Enum):
    """Types of notifications."""
    PLAN_COMPLETE = "plan_complete"
    IMPLEMENTATION_COMPLETE = "implementation_complete"
    TESTING_PASSED = "testing_passed"
    TESTING_FAILED = "testing_failed"
    PR_CREATED = "pr_created"
    PR_MERGED = "pr_merged"
    TECHNICAL_HURDLE = "technical_hurdle"
    APPROVAL_REQUIRED = "approval_required"


class ApprovalCheckpoint(Enum):
    """Approval checkpoints."""
    PLAN_APPROVAL = "plan_approval"
    IMPLEMENTATION_APPROVAL = "implementation_approval"
    PRE_PR_APPROVAL = "pre_pr_approval"


class NotificationManager:
    """Manages notifications and approval checkpoints."""
    
    def __init__(self, callback: Optional[Callable] = None, discord_integration=None):
        """
        Initialize notification manager.
        
        Args:
            callback: Optional callback function for notifications.
                     Signature: callback(notification_type, data)
            discord_integration: Optional DiscordIntegration instance for Discord notifications
        """
        self.callback = callback
        self.discord = discord_integration
        self.notifications = []
        self.approvals = {}
    
    def notify(
        self,
        notification_type: NotificationType,
        data: Dict[str, Any],
        require_approval: bool = False
    ):
        """
        Send a notification.
        
        Args:
            notification_type: Type of notification
            data: Notification data
            require_approval: Whether this requires user approval
        """
        notification = {
            "type": notification_type.value,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "requires_approval": require_approval
        }
        
        self.notifications.append(notification)
        
        # Format notification for display
        message = self._format_notification(notification_type, data)
        print(f"\n{'='*80}")
        print(f"🔔 NOTIFICATION: {notification_type.value.upper()}")
        print(f"{'='*80}")
        print(message)
        print(f"{'='*80}\n")
        
        # Send to Discord if enabled
        if self.discord and self.discord.enabled:
            try:
                self._send_to_discord(notification_type, data)
            except Exception as e:
                print(f"⚠️ Discord notification error: {e}")
        
        # Call callback if provided
        if self.callback:
            try:
                self.callback(notification_type, data)
            except Exception as e:
                print(f"⚠️ Notification callback error: {e}")
        
        # Handle approval requirement
        if require_approval:
            return self._request_approval(notification_type, data)
        
        return True
    
    def request_approval(
        self,
        checkpoint: ApprovalCheckpoint,
        data: Dict[str, Any],
        prompt: str = None
    ) -> bool:
        """
        Request user approval at a checkpoint.
        
        Args:
            checkpoint: The approval checkpoint
            data: Context data for the approval
            prompt: Custom approval prompt
        
        Returns:
            True if approved, False otherwise
        """
        if prompt is None:
            prompt = f"Do you approve this {checkpoint.value}?"
        
        print(f"\n{'='*80}")
        print(f"⏸️  APPROVAL REQUIRED: {checkpoint.value.upper()}")
        print(f"{'='*80}")
        
        # Display relevant data
        if checkpoint == ApprovalCheckpoint.PLAN_APPROVAL:
            print("\n📋 Development Plan:")
            print(data.get("plan", "")[:1000])
            if len(data.get("plan", "")) > 1000:
                print("... (truncated)")
        
        elif checkpoint == ApprovalCheckpoint.IMPLEMENTATION_APPROVAL:
            print("\n💻 Implementation Summary:")
            print(data.get("summary", ""))
            print(f"\n📊 Files: {data.get('file_count', 0)}")
            print(f"📝 Lines of Code: {data.get('loc', 'N/A')}")
        
        elif checkpoint == ApprovalCheckpoint.PRE_PR_APPROVAL:
            print("\n📝 Pull Request Details:")
            print(f"Title: {data.get('title', 'N/A')}")
            print(f"Branch: {data.get('branch', 'N/A')}")
            print(f"\nDescription:\n{data.get('body', '')[:500]}")
        
        print(f"\n{prompt}")
        print("Type 'yes' or 'y' to approve, 'no' or 'n' to reject:")
        
        # In interactive mode, get user input
        # For automated testing, you can set auto_approve
        auto_approve = data.get("auto_approve", False)
        if auto_approve:
            print("(Auto-approved)")
            self.approvals[checkpoint.value] = True
            return True
        
        try:
            response = input().strip().lower()
            approved = response in ['yes', 'y', 'approve']
            self.approvals[checkpoint.value] = approved
            
            if approved:
                print("✅ Approved!")
            else:
                print("❌ Rejected!")
            
            return approved
        except (EOFError, KeyboardInterrupt):
            # Non-interactive mode - default to approval
            print("(Non-interactive mode - defaulting to approval)")
            self.approvals[checkpoint.value] = True
            return True
    
    def _request_approval(
        self,
        notification_type: NotificationType,
        data: Dict[str, Any]
    ) -> bool:
        """Internal method to handle approval requests from notifications."""
        # Map notification types to checkpoints if needed
        checkpoint_map = {
            NotificationType.PLAN_COMPLETE: ApprovalCheckpoint.PLAN_APPROVAL,
            NotificationType.IMPLEMENTATION_COMPLETE: ApprovalCheckpoint.IMPLEMENTATION_APPROVAL,
        }
        
        checkpoint = checkpoint_map.get(notification_type)
        if checkpoint:
            return self.request_approval(checkpoint, data)
        
        return True
    
    def _format_notification(
        self,
        notification_type: NotificationType,
        data: Dict[str, Any]
    ) -> str:
        """Format notification message for display."""
        if notification_type == NotificationType.PLAN_COMPLETE:
            plan_preview = data.get("plan", "")[:500]
            return f"Development plan has been created.\n\nPreview:\n{plan_preview}"
        
        elif notification_type == NotificationType.IMPLEMENTATION_COMPLETE:
            return f"Implementation complete!\nFiles: {data.get('file_count', 0)}\nSummary: {data.get('summary', 'N/A')}"
        
        elif notification_type == NotificationType.TESTING_PASSED:
            return f"✅ All tests passed!\n\nTest Results:\n{data.get('test_results', 'N/A')}"
        
        elif notification_type == NotificationType.TESTING_FAILED:
            return f"❌ Tests failed!\n\nFailures:\n{data.get('test_failures', 'N/A')}"
        
        elif notification_type == NotificationType.PR_CREATED:
            return f"Pull Request created:\nURL: {data.get('url', 'N/A')}\nNumber: {data.get('number', 'N/A')}"
        
        elif notification_type == NotificationType.PR_MERGED:
            return f"✅ Pull Request #{data.get('number', 'N/A')} merged successfully!"
        
        elif notification_type == NotificationType.TECHNICAL_HURDLE:
            return f"⚠️ Technical hurdle detected:\n{data.get('issue', 'N/A')}\n\nSuggested solutions:\n{data.get('suggestions', 'N/A')}"
        
        else:
            return json.dumps(data, indent=2)
    
    def get_notification_history(self) -> list:
        """Get all notifications."""
        return self.notifications
    
    def get_approval_status(self, checkpoint: ApprovalCheckpoint) -> Optional[bool]:
        """Get approval status for a checkpoint."""
        return self.approvals.get(checkpoint.value)
    
    def _send_to_discord(self, notification_type: NotificationType, data: Dict[str, Any]):
        """Send notification to Discord."""
        if not self.discord or not self.discord.enabled:
            return
        
        try:
            if notification_type == NotificationType.PLAN_COMPLETE:
                self.discord.send_plan_complete(
                    plan=data.get("plan", ""),
                    hurdles=data.get("hurdles", [])
                )
            elif notification_type == NotificationType.IMPLEMENTATION_COMPLETE:
                self.discord.send_implementation_complete(
                    summary=data.get("summary", ""),
                    file_count=data.get("file_count", 0),
                    loc=data.get("loc", 0)
                )
            elif notification_type == NotificationType.TESTING_PASSED:
                self.discord.send_test_results(
                    passed=True,
                    test_results=data.get("test_results", "")
                )
            elif notification_type == NotificationType.TESTING_FAILED:
                self.discord.send_test_results(
                    passed=False,
                    test_results=data.get("test_results", "")
                )
            elif notification_type == NotificationType.PR_CREATED:
                self.discord.send_pr_created(
                    pr_number=data.get("number", 0),
                    url=data.get("url", ""),
                    branch=data.get("branch", "")
                )
            elif notification_type == NotificationType.PR_MERGED:
                self.discord.send_pr_merged(
                    pr_number=data.get("number", 0),
                    url=data.get("url", "")
                )
            elif notification_type == NotificationType.TECHNICAL_HURDLE:
                self.discord.send_technical_hurdle(data)
            elif notification_type == NotificationType.APPROVAL_REQUIRED:
                self.discord.send_approval_request(
                    checkpoint=data.get("checkpoint", "unknown"),
                    context=data
                )
        except Exception as e:
            print(f"⚠️ Error sending to Discord: {e}")


def create_notification_callback(output_file: str = None):
    """
    Create a notification callback that logs to file.
    
    Args:
        output_file: Optional file path to log notifications
    
    Returns:
        Callback function
    """
    def callback(notification_type: NotificationType, data: Dict[str, Any]):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": notification_type.value,
            "data": data
        }
        
        if output_file:
            with open(output_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
    
    return callback
