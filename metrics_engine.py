"""
Metrics engine for tracking agent usage, token consumption, and performance.
Uses SQLite for local database storage.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import sqlite3
import json
import os
import threading


class TokenTracker:
    """Tracks token usage for agents."""
    
    def __init__(self, db_conn: sqlite3.Connection):
        """
        Initialize token tracker.
        
        Args:
            db_conn: SQLite database connection
        """
        self.db_conn = db_conn
        self._init_db()
    
    def _init_db(self):
        """Initialize token tracking tables."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                agent_name TEXT NOT NULL,
                stage TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                model TEXT,
                cost_estimate REAL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_token_agent ON token_usage(agent_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_token_stage ON token_usage(stage)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_token_timestamp ON token_usage(timestamp)
        """)
        self.db_conn.commit()
    
    def record_usage(
        self,
        agent_name: str,
        stage: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4"
    ):
        """Record token usage for an agent and stage."""
        if not self.db_conn:
            return  # Database not initialized yet
        total = input_tokens + output_tokens
        cost = self._estimate_cost(input_tokens, output_tokens, model)
        
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO token_usage 
            (agent_name, stage, input_tokens, output_tokens, total_tokens, model, cost_estimate)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (agent_name, stage, input_tokens, output_tokens, total, model, cost))
        self.db_conn.commit()
    
    def _estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Estimate cost based on model pricing (approximate)."""
        # Pricing per 1M tokens (as of 2024)
        pricing = {
            "gpt-4": {"input": 30.0, "output": 60.0},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        }
        
        model_key = model.lower()
        if "gpt-4" in model_key and "turbo" not in model_key:
            prices = pricing.get("gpt-4", {"input": 30.0, "output": 60.0})
        elif "turbo" in model_key:
            prices = pricing.get("gpt-4-turbo", {"input": 10.0, "output": 30.0})
        else:
            prices = pricing.get("gpt-3.5-turbo", {"input": 0.5, "output": 1.5})
        
        input_cost = (input_tokens / 1_000_000) * prices["input"]
        output_cost = (output_tokens / 1_000_000) * prices["output"]
        return input_cost + output_cost
    
    def get_agent_stats(self, agent_name: str) -> Dict[str, Any]:
        """Get statistics for a specific agent."""
        if not self.db_conn:
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "calls": 0,
                "cost_estimate": 0.0
            }
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as calls,
                SUM(cost_estimate) as cost_estimate
            FROM token_usage
            WHERE agent_name = ?
        """, (agent_name,))
        
        row = cursor.fetchone()
        if row and row[0]:
            return {
                "input_tokens": row[0] or 0,
                "output_tokens": row[1] or 0,
                "total_tokens": row[2] or 0,
                "calls": row[3] or 0,
                "cost_estimate": row[4] or 0.0
            }
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
            "cost_estimate": 0.0
        }
    
    def get_stage_stats(self, stage: str) -> Dict[str, Any]:
        """Get statistics for a specific stage."""
        if not self.db_conn:
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "calls": 0
            }
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as calls
            FROM token_usage
            WHERE stage = ?
        """, (stage,))
        
        row = cursor.fetchone()
        if row and row[0]:
            return {
                "input_tokens": row[0] or 0,
                "output_tokens": row[1] or 0,
                "total_tokens": row[2] or 0,
                "calls": row[3] or 0
            }
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "calls": 0
        }
    
    def get_total_stats(self) -> Dict[str, Any]:
        """Get total statistics across all agents."""
        if not self.db_conn:
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "total_calls": 0,
                "total_cost_estimate": 0.0
            }
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as total_calls,
                SUM(cost_estimate) as total_cost_estimate
            FROM token_usage
        """)
        
        row = cursor.fetchone()
        if row and row[0]:
            return {
                "input_tokens": row[0] or 0,
                "output_tokens": row[1] or 0,
                "total_tokens": row[2] or 0,
                "total_calls": row[3] or 0,
                "total_cost_estimate": row[4] or 0.0
            }
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "total_calls": 0,
            "total_cost_estimate": 0.0
        }


class MetricsEngine:
    """Main metrics engine for tracking agent performance and usage."""
    
    def __init__(self, db_path: str = "metrics.db"):
        """
        Initialize metrics engine.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_conn = None
        self.lock = threading.Lock()
        self.token_tracker = None
        self._initialized = False
    
    def start(self):
        """Start/initialize the SQLite database connection."""
        if self._initialized:
            return
        
        db_exists = os.path.exists(self.db_path)
        print(f"📊 Initializing metrics database: {self.db_path}")
        if db_exists:
            print(f"   Database file already exists, checking schema...")
        
        self.db_conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.db_conn.row_factory = sqlite3.Row  # Enable column access by name
        
        self.token_tracker = TokenTracker(self.db_conn)
        self._init_db()
        self._initialized = True
        print(f"✅ Metrics database initialized successfully")
    
    def _ensure_initialized(self):
        """Ensure database is initialized before operations."""
        if not self._initialized:
            self.start()
    
    def _init_db(self):
        """Initialize database tables (only creates if they don't exist)."""
        cursor = self.db_conn.cursor()
        
        # Check if tables already exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('agent_actions', 'stage_metrics', 'project_metrics', 'code_quality', 'token_usage')
        """)
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        # Agent actions table
        if 'agent_actions' not in existing_tables:
            cursor.execute("""
                CREATE TABLE agent_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    agent_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    action_details TEXT,
                    duration REAL
                )
            """)
            cursor.execute("""
                CREATE INDEX idx_actions_agent ON agent_actions(agent_name)
            """)
            cursor.execute("""
                CREATE INDEX idx_actions_timestamp ON agent_actions(timestamp)
            """)
        else:
            # Ensure indexes exist even if table exists
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_actions_agent ON agent_actions(agent_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON agent_actions(timestamp)
            """)
        
        # Stage metrics table
        if 'stage_metrics' not in existing_tables:
            cursor.execute("""
                CREATE TABLE stage_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stage_name TEXT NOT NULL UNIQUE,
                    start_time DATETIME,
                    end_time DATETIME,
                    duration REAL,
                    agents_involved TEXT,
                    success BOOLEAN,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX idx_stage_name ON stage_metrics(stage_name)
            """)
        else:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stage_name ON stage_metrics(stage_name)
            """)
        
        # Project metrics table
        if 'project_metrics' not in existing_tables:
            # Table doesn't exist, create it and seed
            cursor.execute("""
                CREATE TABLE project_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL UNIQUE,
                    metric_value INTEGER NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                INSERT INTO project_metrics (metric_name, metric_value)
                VALUES 
                    ('projects_started', 0),
                    ('projects_completed', 0),
                    ('projects_failed', 0),
                    ('total_iterations', 0)
            """)
        else:
            # Table exists, check if project metrics are already seeded
            cursor.execute("SELECT COUNT(*) FROM project_metrics")
            metric_count = cursor.fetchone()[0]
            
            # Only seed if no metrics exist
            if metric_count == 0:
                cursor.execute("""
                    INSERT INTO project_metrics (metric_name, metric_value)
                    VALUES 
                        ('projects_started', 0),
                        ('projects_completed', 0),
                        ('projects_failed', 0),
                        ('total_iterations', 0)
                """)
        
        # Code quality metrics table
        if 'code_quality' not in existing_tables:
            cursor.execute("""
                CREATE TABLE code_quality (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    agent_name TEXT NOT NULL,
                    dry_violations INTEGER DEFAULT 0,
                    complexity_score REAL DEFAULT 0.0,
                    readability_score REAL DEFAULT 0.0,
                    maintainability_score REAL DEFAULT 0.0,
                    code_reviews INTEGER DEFAULT 0,
                    improvements_suggested INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE INDEX idx_quality_agent ON code_quality(agent_name)
            """)
        else:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_quality_agent ON code_quality(agent_name)
            """)
        
        self.db_conn.commit()
    
    def record_agent_action(
        self,
        agent_name: str,
        action_type: str,
        action_details: Dict[str, Any],
        duration: float = None
    ):
        """Record an agent action."""
        self._ensure_initialized()
        with self.lock:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT INTO agent_actions (agent_name, action_type, action_details, duration)
                VALUES (?, ?, ?, ?)
            """, (agent_name, action_type, json.dumps(action_details), duration))
            self.db_conn.commit()
    
    def record_stage(
        self,
        stage_name: str,
        start_time: datetime = None,
        end_time: datetime = None,
        agents: List[str] = None,
        success: bool = True
    ):
        """Record a stage completion."""
        self._ensure_initialized()
        with self.lock:
            start = start_time or datetime.now()
            end = end_time or datetime.now()
            duration = (end - start).total_seconds()
            
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO stage_metrics 
                (stage_name, start_time, end_time, duration, agents_involved, success, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (stage_name, start.isoformat(), end.isoformat(), duration, 
                  json.dumps(agents or []), success))
            self.db_conn.commit()
    
    def record_token_usage(
        self,
        agent_name: str,
        stage: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4"
    ):
        """Record token usage."""
        self._ensure_initialized()
        self.token_tracker.record_usage(agent_name, stage, input_tokens, output_tokens, model)
    
    def record_code_quality(
        self,
        agent_name: str,
        dry_violations: int = 0,
        complexity_score: float = 0.0,
        readability_score: float = 0.0,
        maintainability_score: float = 0.0
    ):
        """Record code quality metrics."""
        self._ensure_initialized()
        with self.lock:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT INTO code_quality 
                (agent_name, dry_violations, complexity_score, readability_score, 
                 maintainability_score, code_reviews)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (agent_name, dry_violations, complexity_score, 
                  readability_score, maintainability_score))
            self.db_conn.commit()
    
    def update_project_metric(self, metric_name: str, increment: int = 1):
        """Update a project metric."""
        self._ensure_initialized()
        with self.lock:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                UPDATE project_metrics 
                SET metric_value = metric_value + ?, updated_at = CURRENT_TIMESTAMP
                WHERE metric_name = ?
            """, (increment, metric_name))
            self.db_conn.commit()
    
    def get_project_metrics(self) -> Dict[str, int]:
        """Get project metrics."""
        self._ensure_initialized()
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT metric_name, metric_value FROM project_metrics")
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def _get_agent_metrics_without_efficiency(self, agent_name: str) -> Dict[str, Any]:
        """Get agent metrics without calculating efficiency score (to avoid recursion)."""
        self._ensure_initialized()
        cursor = self.db_conn.cursor()
        
        # Get actions
        cursor.execute("""
            SELECT action_type, COUNT(*) as count, AVG(duration) as avg_duration
            FROM agent_actions
            WHERE agent_name = ?
            GROUP BY action_type
        """, (agent_name,))
        
        actions_summary = {row[0]: {"count": row[1], "avg_duration": row[2]} 
                          for row in cursor.fetchall()}
        
        # Get recent actions
        cursor.execute("""
            SELECT action_type, action_details, duration, timestamp
            FROM agent_actions
            WHERE agent_name = ?
            ORDER BY timestamp DESC
            LIMIT 100
        """, (agent_name,))
        
        recent_actions = []
        for row in cursor.fetchall():
            try:
                details = json.loads(row[1]) if row[1] else {}
            except:
                details = {}
            recent_actions.append({
                "action_type": row[0],
                "details": details,
                "duration": row[2],
                "timestamp": row[3]
            })
        
        # Get code quality metrics
        cursor.execute("""
            SELECT 
                SUM(dry_violations) as total_dry_violations,
                AVG(complexity_score) as avg_complexity,
                AVG(readability_score) as avg_readability,
                AVG(maintainability_score) as avg_maintainability,
                COUNT(*) as code_reviews
            FROM code_quality
            WHERE agent_name = ?
        """, (agent_name,))
        
        quality_row = cursor.fetchone()
        code_quality = {
            "dry_violations": quality_row[0] or 0,
            "complexity_score": quality_row[1] or 0.0,
            "readability_score": quality_row[2] or 0.0,
            "maintainability_score": quality_row[3] or 0.0,
            "code_reviews": quality_row[4] or 0
        }
        
        # Calculate tasks completed/failed
        tasks_completed = sum(1 for a in recent_actions if a["action_type"] == "COMPLETE")
        tasks_failed = sum(1 for a in recent_actions if a["action_type"] == "ERROR")
        
        return {
            "actions": recent_actions,
            "actions_summary": actions_summary,
            "tasks_completed": tasks_completed,
            "tasks_failed": tasks_failed,
            "code_quality": code_quality
        }
    
    def get_agent_metrics(self, agent_name: str) -> Dict[str, Any]:
        """Get metrics for a specific agent."""
        metrics = self._get_agent_metrics_without_efficiency(agent_name)
        metrics["efficiency_score"] = self.calculate_efficiency_score(agent_name, metrics)
        return metrics
    
    def calculate_efficiency_score(self, agent_name: str, agent_metrics: Dict[str, Any] = None) -> float:
        """Calculate efficiency score for an agent (0-100)."""
        self._ensure_initialized()
        token_stats = self.token_tracker.get_agent_stats(agent_name)
        if agent_metrics is None:
            # Get metrics without efficiency score to avoid recursion
            agent_metrics = self._get_agent_metrics_without_efficiency(agent_name)
        
        if not agent_metrics.get("actions"):
            return 0.0
        
        # Factors:
        # 1. Token efficiency (lower is better, normalized)
        # 2. Task completion rate
        # 3. Average action duration (lower is better)
        
        total_tokens = token_stats.get("total_tokens", 1)
        calls = token_stats.get("calls", 1)
        avg_tokens_per_call = total_tokens / calls if calls > 0 else 0
        
        # Normalize token efficiency (assuming 10k tokens per call is baseline)
        token_efficiency = max(0, 100 - (avg_tokens_per_call / 100))
        
        # Task completion rate
        total_tasks = agent_metrics.get("tasks_completed", 0) + agent_metrics.get("tasks_failed", 0)
        completion_rate = (agent_metrics.get("tasks_completed", 0) / total_tasks * 100) if total_tasks > 0 else 0
        
        # Duration efficiency
        actions = agent_metrics.get("actions", [])
        if actions:
            durations = [a.get("duration", 0) for a in actions if a.get("duration")]
            avg_duration = sum(durations) / len(durations) if durations else 60
            duration_efficiency = max(0, 100 - (avg_duration / 0.6))
        else:
            duration_efficiency = 50
        
        # Weighted average
        efficiency = (token_efficiency * 0.4 + completion_rate * 0.4 + duration_efficiency * 0.2)
        return efficiency
    
    def get_all_agent_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all agents."""
        self._ensure_initialized()
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT DISTINCT agent_name FROM agent_actions")
        agent_names = [row[0] for row in cursor.fetchall()]
        
        return {name: self.get_agent_metrics(name) for name in agent_names}
    
    def get_stage_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all stage metrics."""
        self._ensure_initialized()
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT stage_name, start_time, end_time, duration, agents_involved, success
            FROM stage_metrics
            ORDER BY updated_at DESC
        """)
        
        stages = {}
        for row in cursor.fetchall():
            try:
                agents = json.loads(row[4]) if row[4] else []
            except:
                agents = []
            stages[row[0]] = {
                "start_time": row[1],
                "end_time": row[2],
                "duration": row[3],
                "agents_involved": agents,
                "success": bool(row[5])
            }
        return stages
    
    def get_code_quality_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get code quality metrics for all agents."""
        self._ensure_initialized()
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT 
                agent_name,
                SUM(dry_violations) as total_dry_violations,
                AVG(complexity_score) as avg_complexity,
                AVG(readability_score) as avg_readability,
                AVG(maintainability_score) as avg_maintainability,
                COUNT(*) as code_reviews
            FROM code_quality
            GROUP BY agent_name
        """)
        
        quality = {}
        for row in cursor.fetchall():
            quality[row[0]] = {
                "dry_violations": row[1] or 0,
                "complexity_score": row[2] or 0.0,
                "readability_score": row[3] or 0.0,
                "maintainability_score": row[4] or 0.0,
                "code_reviews": row[5] or 0
            }
        return quality
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all data for dashboard display."""
        self._ensure_initialized()
        return {
            "timestamp": datetime.now().isoformat(),
            "token_usage": {
                "total": self.token_tracker.get_total_stats(),
                "by_agent": {
                    name: self.token_tracker.get_agent_stats(name) 
                    for name in self._get_all_agent_names()
                },
                "by_stage": {
                    stage: self.token_tracker.get_stage_stats(stage)
                    for stage in self._get_all_stages()
                }
            },
            "agent_metrics": self.get_all_agent_metrics(),
            "stage_metrics": self.get_stage_metrics(),
            "project_metrics": self.get_project_metrics(),
            "code_quality": self.get_code_quality_metrics()
        }
    
    def _get_all_agent_names(self) -> List[str]:
        """Get all unique agent names from token_usage."""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT DISTINCT agent_name FROM token_usage")
        return [row[0] for row in cursor.fetchall()]
    
    def _get_all_stages(self) -> List[str]:
        """Get all unique stages from token_usage."""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT DISTINCT stage FROM token_usage")
        return [row[0] for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection."""
        if self._initialized and self.db_conn:
            self.db_conn.close()
            self._initialized = False
            print("📊 Metrics database connection closed")
