import pytest
from metrics_engine import MetricsEngine, TokenTracker

def test_metrics_engine_init():
    metrics_engine = MetricsEngine()
    assert isinstance(metrics_engine, MetricsEngine)

def test_metrics_engine_record_usage():
    metrics_engine = MetricsEngine()
    metrics_engine.record_usage('test_agent', 10)
    stats = metrics_engine.get_agent_stats('test_agent')
    assert stats['tokens_used'] == 10

# More test cases for the rest of the functions and classes in metrics_engine.py...