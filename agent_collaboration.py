"""
Agent collaboration system with standups, peer reviews, and agent management.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from crewai import Agent, Task, Crew, Process
import json


class AgentPerformance(Enum):
    """Agent performance levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    SATISFACTORY = "satisfactory"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


class AgentStatus(Enum):
    """Agent status."""
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    FIRED = "fired"
    REPLACED = "replaced"


class AgentRecord:
    """Record of an agent's performance and status."""
    
    def __init__(self, agent_name: str, agent_instance: Agent):
        self.agent_name = agent_name
        self.agent_instance = agent_instance
        self.status = AgentStatus.ACTIVE
        self.performance_history = []
        self.peer_reviews = []
        self.issues_solved = []
        self.issues_created = []
        self.standup_participations = 0
        self.created_at = datetime.now()
        self.fired_at = None
        self.replacement_reason = None
    
    def add_performance_review(self, performance: AgentPerformance, review: str, reviewer: str):
        """Add a performance review."""
        self.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            "performance": performance.value,
            "review": review,
            "reviewer": reviewer
        })
    
    def add_peer_review(self, reviewer: str, feedback: str, rating: int):
        """Add a peer review (rating 1-5)."""
        self.peer_reviews.append({
            "timestamp": datetime.now().isoformat(),
            "reviewer": reviewer,
            "feedback": feedback,
            "rating": rating
        })
    
    def calculate_average_rating(self) -> float:
        """Calculate average peer review rating."""
        if not self.peer_reviews:
            return 3.0  # Default neutral rating
        return sum(r["rating"] for r in self.peer_reviews) / len(self.peer_reviews)
    
    def should_be_fired(self, threshold: float = 2.0) -> bool:
        """Determine if agent should be fired based on performance."""
        avg_rating = self.calculate_average_rating()
        recent_performance = [p["performance"] for p in self.performance_history[-3:]]
        
        # Fire if average rating is below threshold
        if avg_rating < threshold:
            return True
        
        # Fire if recent performance is consistently poor
        if len(recent_performance) >= 2:
            poor_count = sum(1 for p in recent_performance if p in [AgentPerformance.POOR.value, AgentPerformance.UNACCEPTABLE.value])
            if poor_count >= 2:
                return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "status": self.status.value,
            "average_rating": self.calculate_average_rating(),
            "peer_reviews_count": len(self.peer_reviews),
            "performance_reviews_count": len(self.performance_history),
            "issues_solved": len(self.issues_solved),
            "issues_created": len(self.issues_created),
            "standup_participations": self.standup_participations,
            "created_at": self.created_at.isoformat(),
            "fired_at": self.fired_at.isoformat() if self.fired_at else None,
            "replacement_reason": self.replacement_reason
        }


class StandupManager:
    """Manages agent standups and collaboration."""
    
    def __init__(self, discord_integration=None):
        """
        Initialize standup manager.
        
        Args:
            discord_integration: DiscordIntegration instance for notifications
        """
        self.discord = discord_integration
        self.standup_history = []
        self.agent_records: Dict[str, AgentRecord] = {}
    
    def register_agent(self, agent_name: str, agent_instance: Agent):
        """Register an agent."""
        if agent_name not in self.agent_records:
            self.agent_records[agent_name] = AgentRecord(agent_name, agent_instance)
    
    def conduct_standup(
        self,
        agents: List[AgentRecord],
        context: str = "General standup"
    ) -> Dict[str, Any]:
        """
        Conduct a standup meeting between agents.
        
        Args:
            agents: List of agent records participating
            context: Context for the standup
        
        Returns:
            Standup results
        """
        standup_id = len(self.standup_history) + 1
        
        # Notify Discord
        if self.discord and self.discord.enabled:
            agent_names = [a.agent_name for a in agents]
            self.discord.send_message(
                title="🤝 Agent Standup Meeting",
                description=f"**Standup #{standup_id}**\n\n**Context:** {context}\n\n**Participants:** {', '.join(agent_names)}",
                message_type=self.discord.DiscordMessageType.INFO if hasattr(self.discord, 'DiscordMessageType') else None,
                fields={
                    "Standup ID": str(standup_id),
                    "Participants": str(len(agents)),
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                footer="Agent Collaboration System"
            )
        
        # Each agent shares updates
        updates = {}
        for agent in agents:
            agent.standup_participations += 1
            # Simulate agent sharing updates
            update = f"{agent.agent_name} is working on their assigned tasks and is ready to collaborate."
            updates[agent.agent_name] = update
            
            if self.discord and self.discord.enabled:
                self.discord.send_message(
                    title=f"📢 {agent.agent_name} Standup Update",
                    description=update,
                    message_type=self.discord.DiscordMessageType.INFO if hasattr(self.discord, 'DiscordMessageType') else None,
                    footer=f"Standup #{standup_id}"
                )
        
        # Agents identify issues and help each other
        issues = self._identify_collaboration_issues(agents, context)
        solutions = self._generate_solutions(agents, issues)
        
        standup_result = {
            "standup_id": standup_id,
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "participants": [a.agent_name for a in agents],
            "updates": updates,
            "issues_identified": issues,
            "solutions": solutions
        }
        
        self.standup_history.append(standup_result)
        
        # Notify Discord of standup completion
        if self.discord and self.discord.enabled:
            issues_text = "\n".join(f"• {issue}" for issue in issues[:5]) if issues else "No issues identified"
            solutions_text = "\n".join(f"• {sol}" for sol in solutions[:5]) if solutions else "No solutions needed"
            
            self.discord.send_message(
                title="✅ Standup Complete",
                description=f"Standup #{standup_id} completed successfully",
                message_type=self.discord.DiscordMessageType.SUCCESS if hasattr(self.discord, 'DiscordMessageType') else None,
                fields={
                    "Issues Identified": str(len(issues)),
                    "Solutions Generated": str(len(solutions)),
                    "Issues": issues_text[:500] if issues_text else "None",
                    "Solutions": solutions_text[:500] if solutions_text else "None"
                },
                footer="Agent Collaboration System"
            )
        
        return standup_result
    
    def _identify_collaboration_issues(self, agents: List[AgentRecord], context: str) -> List[str]:
        """Identify issues that need collaboration."""
        # This would use LLM to identify issues, but for now return empty
        # In a real implementation, this would analyze agent outputs and identify blockers
        return []
    
    def _generate_solutions(self, agents: List[AgentRecord], issues: List[str]) -> List[str]:
        """Generate collaborative solutions."""
        # This would use LLM to generate solutions
        return []


class PeerReviewSystem:
    """System for agents to review each other."""
    
    def __init__(self, discord_integration=None):
        """
        Initialize peer review system.
        
        Args:
            discord_integration: DiscordIntegration instance
        """
        self.discord = discord_integration
        self.review_history = []
    
    def conduct_peer_review(
        self,
        reviewer_agent: AgentRecord,
        reviewed_agent: AgentRecord,
        work_product: str,
        context: str = "General review"
    ) -> Dict[str, Any]:
        """
        Conduct a peer review.
        
        Args:
            reviewer_agent: Agent doing the review
            reviewed_agent: Agent being reviewed
            work_product: The work being reviewed
            context: Context for the review
        
        Returns:
            Review results
        """
        # Use LLM to generate review (would use actual LLM in production)
        # For now, generate a simulated review based on work quality
        
        review_prompt = f"""As {reviewer_agent.agent_name}, review the work of {reviewed_agent.agent_name}.

Work Product:
{work_product[:1000]}

Context: {context}

Provide:
1. A rating from 1-5 (1=poor, 5=excellent)
2. Constructive feedback
3. Specific suggestions for improvement
4. What was done well

Format as JSON with: rating, feedback, suggestions, strengths"""

        # In a real implementation, this would call the LLM
        # For now, generate a simulated review
        rating = 4  # Default good rating
        feedback = f"{reviewer_agent.agent_name} reviewed {reviewed_agent.agent_name}'s work and found it satisfactory."
        suggestions = ["Continue maintaining high quality standards"]
        strengths = ["Good attention to detail"]
        
        # Add review to agent record
        reviewed_agent.add_peer_review(
            reviewer=reviewer_agent.agent_name,
            feedback=feedback,
            rating=rating
        )
        
        # Determine performance level
        if rating >= 4:
            performance = AgentPerformance.EXCELLENT if rating == 5 else AgentPerformance.GOOD
        elif rating >= 3:
            performance = AgentPerformance.SATISFACTORY
        else:
            performance = AgentPerformance.POOR if rating >= 2 else AgentPerformance.UNACCEPTABLE
        
        reviewed_agent.add_performance_review(
            performance=performance,
            review=feedback,
            reviewer=reviewer_agent.agent_name
        )
        
        review_result = {
            "timestamp": datetime.now().isoformat(),
            "reviewer": reviewer_agent.agent_name,
            "reviewed": reviewed_agent.agent_name,
            "rating": rating,
            "feedback": feedback,
            "suggestions": suggestions,
            "strengths": strengths,
            "performance": performance.value,
            "context": context
        }
        
        self.review_history.append(review_result)
        
        # Notify Discord
        if self.discord and self.discord.enabled:
            from discord_integration import DiscordMessageType
            
            emoji = "⭐" * rating
            message_type = DiscordMessageType.SUCCESS if rating >= 4 else DiscordMessageType.WARNING if rating >= 3 else DiscordMessageType.ERROR
            
            self.discord.send_message(
                title=f"📝 Peer Review: {reviewed_agent.agent_name}",
                description=f"**Reviewer:** {reviewer_agent.agent_name}\n**Rating:** {emoji} ({rating}/5)\n\n**Feedback:**\n{feedback}",
                message_type=message_type,
                fields={
                    "Performance": performance.value.upper(),
                    "Suggestions": "\n".join(suggestions[:3]),
                    "Strengths": "\n".join(strengths[:3])
                },
                footer="Peer Review System"
            )
        
        return review_result


class AgentManager:
    """Manages agent lifecycle, firing, and replacement."""
    
    def __init__(self, discord_integration=None):
        """
        Initialize agent manager.
        
        Args:
            discord_integration: DiscordIntegration instance
        """
        self.discord = discord_integration
        self.agent_records: Dict[str, AgentRecord] = {}
        self.fired_agents = []
        self.agent_factory = {}  # Maps agent names to factory functions
    
    def register_agent_factory(self, agent_name: str, factory_func):
        """Register a factory function for creating agents."""
        self.agent_factory[agent_name] = factory_func
    
    def evaluate_agent(self, agent_name: str, threshold: float = 2.0) -> bool:
        """
        Evaluate if an agent should be fired.
        
        Args:
            agent_name: Name of agent to evaluate
            threshold: Rating threshold for firing
        
        Returns:
            True if agent should be fired
        """
        if agent_name not in self.agent_records:
            return False
        
        agent = self.agent_records[agent_name]
        should_fire = agent.should_be_fired(threshold)
        
        if should_fire:
            self.fire_agent(agent_name, "Performance below acceptable threshold")
        
        return should_fire
    
    def fire_agent(self, agent_name: str, reason: str):
        """
        Fire an agent and replace it.
        
        Args:
            agent_name: Name of agent to fire
            reason: Reason for firing
        """
        if agent_name not in self.agent_records:
            return
        
        agent = self.agent_records[agent_name]
        agent.status = AgentStatus.FIRED
        agent.fired_at = datetime.now()
        agent.replacement_reason = reason
        
        # Notify Discord
        if self.discord and self.discord.enabled:
            from discord_integration import DiscordMessageType
            
            self.discord.send_message(
                title=f"🚫 Agent Fired: {agent_name}",
                description=f"**Reason:** {reason}\n\n**Performance Summary:**\n- Average Rating: {agent.calculate_average_rating():.2f}/5\n- Peer Reviews: {len(agent.peer_reviews)}\n- Issues Solved: {len(agent.issues_solved)}\n- Issues Created: {len(agent.issues_created)}",
                message_type=DiscordMessageType.ERROR,
                fields={
                    "Status": agent.status.value.upper(),
                    "Fired At": agent.fired_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "Reason": reason
                },
                footer="Agent Management System"
            )
        
        self.fired_agents.append(agent.to_dict())
        
        # Replace agent if factory exists
        if agent_name in self.agent_factory:
            self.replace_agent(agent_name, reason)
    
    def replace_agent(self, agent_name: str, reason: str):
        """
        Replace a fired agent with a new one.
        
        Args:
            agent_name: Name of agent to replace
            reason: Reason for replacement
        """
        if agent_name not in self.agent_factory:
            return
        
        # Create new agent
        factory_func = self.agent_factory[agent_name]
        new_agent = factory_func()
        
        # Create new record
        new_record = AgentRecord(f"{agent_name}_v2", new_agent)
        new_record.status = AgentStatus.REPLACED
        new_record.replacement_reason = f"Replaced {agent_name} due to: {reason}"
        
        # Update records
        old_agent = self.agent_records.get(agent_name)
        if old_agent:
            old_agent.status = AgentStatus.REPLACED
        
        self.agent_records[f"{agent_name}_v2"] = new_record
        
        # Notify Discord
        if self.discord and self.discord.enabled:
            from discord_integration import DiscordMessageType
            
            self.discord.send_message(
                title=f"🔄 Agent Replaced: {agent_name}",
                description=f"**Old Agent:** {agent_name}\n**New Agent:** {agent_name}_v2\n\n**Reason:** {reason}",
                message_type=DiscordMessageType.INFO,
                fields={
                    "Replacement Reason": reason,
                    "New Agent Status": new_record.status.value.upper(),
                    "Created At": new_record.created_at.strftime("%Y-%m-%d %H:%M:%S")
                },
                footer="Agent Management System"
            )
        
        return new_record
