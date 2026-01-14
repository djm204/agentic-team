import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from notifications import NotificationType, ApprovalCheckpoint, NotificationManager

def test_notification_type_enum():
    """Test that NotificationType is an enum with expected values."""
    assert NotificationType.PLAN_COMPLETE.value == "plan_complete"
    assert NotificationType.IMPLEMENTATION_COMPLETE.value == "implementation_complete"
    assert NotificationType.PR_CREATED.value == "pr_created"
    assert isinstance(NotificationType.PLAN_COMPLETE, NotificationType)

def test_approval_checkpoint_enum():
    """Test that ApprovalCheckpoint is an enum with expected values."""
    assert ApprovalCheckpoint.PLAN_APPROVAL.value == "plan_approval"
    assert ApprovalCheckpoint.IMPLEMENTATION_APPROVAL.value == "implementation_approval"
    assert isinstance(ApprovalCheckpoint.PLAN_APPROVAL, ApprovalCheckpoint)

def test_notification_manager_init():
    """Test that NotificationManager can be initialized."""
    notif_manager = NotificationManager()
    assert notif_manager is not None
    assert notif_manager.notifications == []
    assert notif_manager.approvals == {}

def test_notification_manager_notify():
    """Test that NotificationManager can send notifications."""
    notif_manager = NotificationManager()
    notif_manager.notify(NotificationType.PLAN_COMPLETE, {"plan": "test plan"})
    assert len(notif_manager.notifications) == 1
    # Check the notification structure
    notification = notif_manager.notifications[0]
    assert notification["type"] == NotificationType.PLAN_COMPLETE.value
    assert notification["data"]["plan"] == "test plan"