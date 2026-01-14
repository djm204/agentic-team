"""
Technical hurdle detection and escalation system.
"""
from typing import Dict, List, Any, Optional
from enum import Enum
from agents import get_llm
from crewai import Agent, Task, Crew, Process


class HurdleSeverity(Enum):
    """Severity levels for technical hurdles."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TechnicalHurdle:
    """Represents a technical hurdle."""
    
    def __init__(
        self,
        issue: str,
        severity: HurdleSeverity,
        context: str,
        suggestions: List[str] = None
    ):
        self.issue = issue
        self.severity = severity
        self.context = context
        self.suggestions = suggestions or []
        self.resolved = False
        self.resolution = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "issue": self.issue,
            "severity": self.severity.value,
            "context": self.context,
            "suggestions": self.suggestions,
            "resolved": self.resolved,
            "resolution": self.resolution
        }


class HurdleDetector:
    """Detects technical hurdles in plans and implementations."""
    
    def __init__(self):
        self.llm = get_llm()
        self.detector_agent = Agent(
            role="Technical Hurdle Detector",
            goal="Identify potential technical challenges, blockers, and risks in development plans and implementations",
            backstory="""You are an expert technical architect who specializes in identifying 
            potential problems before they become blockers. You have deep experience across 
            multiple technology stacks and can spot issues related to architecture, dependencies, 
            security, performance, scalability, and integration challenges. You provide actionable 
            solutions and escalation recommendations.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def detect_hurdles(
        self,
        plan_or_implementation: str,
        context: str = "development"
    ) -> List[TechnicalHurdle]:
        """
        Detect technical hurdles in plan or implementation.
        
        Args:
            plan_or_implementation: The plan or implementation to analyze
            context: Context of the analysis ('planning' or 'implementation')
        
        Returns:
            List of detected technical hurdles
        """
        task = Task(
            description=f"""Analyze the following {context} for potential technical hurdles, 
            blockers, or risks:

            {plan_or_implementation}

            Identify:
            1. Technical challenges that might block progress
            2. Missing dependencies or unclear requirements
            3. Security concerns
            4. Performance or scalability issues
            5. Integration complexities
            6. Architecture concerns
            7. Technology stack incompatibilities

            For each hurdle, provide:
            - Clear description of the issue
            - Severity level (low, medium, high, critical)
            - Context explaining why it's a hurdle
            - Suggested solutions or workarounds

            Format your response as a structured list of hurdles with severity ratings.""",
            agent=self.detector_agent,
            expected_output="List of technical hurdles with severity, context, and suggestions"
        )
        
        crew = Crew(
            agents=[self.detector_agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        return self._parse_hurdles(str(result))
    
    def _parse_hurdles(self, result_text: str) -> List[TechnicalHurdle]:
        """Parse hurdles from agent output."""
        hurdles = []
        
        # Try to extract structured information
        lines = result_text.split('\n')
        current_hurdle = None
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect severity
            if 'critical' in line_lower or 'severity: critical' in line_lower:
                severity = HurdleSeverity.CRITICAL
            elif 'high' in line_lower or 'severity: high' in line_lower:
                severity = HurdleSeverity.HIGH
            elif 'medium' in line_lower or 'severity: medium' in line_lower:
                severity = HurdleSeverity.MEDIUM
            elif 'low' in line_lower or 'severity: low' in line_lower:
                severity = HurdleSeverity.LOW
            else:
                severity = HurdleSeverity.MEDIUM  # Default
            
            # Detect issue markers
            if any(marker in line_lower for marker in ['issue:', 'problem:', 'hurdle:', 'challenge:']):
                if current_hurdle:
                    hurdles.append(current_hurdle)
                
                issue = line.split(':', 1)[1].strip() if ':' in line else line.strip()
                current_hurdle = TechnicalHurdle(
                    issue=issue,
                    severity=severity,
                    context="",
                    suggestions=[]
                )
            
            # Detect suggestions
            elif any(marker in line_lower for marker in ['suggestion:', 'solution:', 'workaround:']):
                if current_hurdle:
                    suggestion = line.split(':', 1)[1].strip() if ':' in line else line.strip()
                    current_hurdle.suggestions.append(suggestion)
            
            # Accumulate context
            elif current_hurdle and line.strip():
                if not current_hurdle.context:
                    current_hurdle.context = line.strip()
                else:
                    current_hurdle.context += "\n" + line.strip()
        
        if current_hurdle:
            hurdles.append(current_hurdle)
        
        # If parsing failed, create a single hurdle from the text
        if not hurdles and result_text.strip():
            hurdles.append(TechnicalHurdle(
                issue="Potential technical challenges detected",
                severity=HurdleSeverity.MEDIUM,
                context=result_text[:500],
                suggestions=["Review the analysis above for specific issues"]
            ))
        
        return hurdles


def should_escalate(hurdle: TechnicalHurdle) -> bool:
    """Determine if a hurdle should be escalated to the user."""
    return hurdle.severity in [HurdleSeverity.HIGH, HurdleSeverity.CRITICAL]
