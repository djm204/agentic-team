import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import tempfile
from metrics_engine import MetricsEngine, TokenTracker

def test_metrics_engine_init():
    """Test that MetricsEngine can be initialized."""
    # Use a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        metrics_engine = MetricsEngine(db_path=db_path)
        assert isinstance(metrics_engine, MetricsEngine)
        assert metrics_engine.db_path == db_path
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_metrics_engine_record_token_usage():
    """Test that MetricsEngine can record token usage."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        metrics_engine = MetricsEngine(db_path=db_path)
        metrics_engine.start()  # Initialize database
        
        # Record token usage (agent_name, stage, input_tokens, output_tokens, model)
        metrics_engine.record_token_usage('test_agent', 'planning', 10, 5)
        
        # Get stats from token tracker
        stats = metrics_engine.token_tracker.get_agent_stats('test_agent')
        assert stats['total_tokens'] == 15  # input + output
        assert stats['calls'] >= 1
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_metrics_engine_record_agent_action():
    """Test that MetricsEngine can record agent actions."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        metrics_engine = MetricsEngine(db_path=db_path)
        metrics_engine.start()
        
        metrics_engine.record_agent_action('test_agent', 'test_action', {'key': 'value'})
        
        # Get agent metrics which should include the action
        metrics = metrics_engine.get_agent_metrics('test_agent')
        assert metrics is not None
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)