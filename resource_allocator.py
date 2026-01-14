"""
Resource allocation system for adaptive agent deployment based on project needs.
Analyzes manifestos to determine optimal agent configuration.
"""
import re
from typing import Dict, List, Set
from enum import Enum


class TaskType(Enum):
    """Types of tasks that determine resource allocation."""
    FULL_PROJECT = "full_project"
    POC = "poc"
    QA_TESTING = "qa_testing"
    CODE_REVIEW = "code_review"
    BUG_FIX = "bug_fix"
    DOCUMENTATION = "documentation"
    TEST_GENERATION = "test_generation"
    REFACTORING = "refactoring"
    SECURITY_AUDIT = "security_audit"
    FEATURE_ADDITION = "feature_addition"


class ResourceAllocation:
    """Determines which agents are needed based on task analysis."""
    
    # Agent roles
    PROJECT_MANAGER = "Project Manager"
    DEVELOPER = "Senior Software Developer"
    CODE_REVIEWER = "Code Reviewer"
    QA_ENGINEER = "QA Engineer & Test Specialist"
    PR_MANAGER = "PR Manager"
    
    # Task type patterns
    POC_PATTERNS = [
        r'\b(poc|proof of concept|prototype|demo|quick test|experiment)\b',
        r'\b(rapid|quick|simple|minimal|basic)\b.*\b(implementation|build|create|poc|prototype)\b',
        r'\b(just|only|simply)\b.*\b(code|implement|build)\b',
        r'\b(create|build|make)\b.*\b(poc|prototype|demo|quick|simple)\b'
    ]
    
    QA_PATTERNS = [
        r'\b(test|testing|qa|quality assurance|test suite|test coverage)\b',
        r'\b(write|create|add|generate).*\b(test|tests|unit test|integration test)\b',
        r'\b(test.*coverage|coverage.*test|test.*suite)\b',
        r'\b(ensure|verify|validate).*\b(test|tests)\b'
    ]
    
    CODE_REVIEW_PATTERNS = [
        r'\b(review|code review|review code|audit code)\b',
        r'\b(check|analyze|examine).*\b(code|implementation|quality)\b',
        r'\b(code.*quality|quality.*code|code.*audit)\b'
    ]
    
    BUG_FIX_PATTERNS = [
        r'\b(bug|fix|issue|error|bugfix|defect|patch)\b',
        r'\b(fix|resolve|correct|repair).*\b(bug|issue|error|problem)\b',
        r'\b(debug|troubleshoot|resolve)\b'
    ]
    
    DOCUMENTATION_PATTERNS = [
        r'\b(documentation|docs|readme|api.*doc|docstring)\b',
        r'\b(write|create|add|generate).*\b(documentation|docs|readme)\b',
        r'\b(document|documenting)\b'
    ]
    
    TEST_GENERATION_PATTERNS = [
        r'\b(test.*generation|generate.*test|add.*test|create.*test)\b',
        r'\b(unit test|integration test|test.*file)\b',
        r'\b(test.*coverage|coverage.*target|test.*suite)\b',
        r'\b(ensure|achieve).*\b(\d+%|80%|coverage)\b'
    ]
    
    REFACTORING_PATTERNS = [
        r'\b(refactor|refactoring|restructure|reorganize|cleanup)\b',
        r'\b(improve|optimize|enhance).*\b(code|structure|architecture)\b',
        r'\b(code.*cleanup|clean.*code|improve.*code)\b'
    ]
    
    SECURITY_PATTERNS = [
        r'\b(security|audit|vulnerability|penetration|security.*scan)\b',
        r'\b(check|analyze|review).*\b(security|vulnerability|threat)\b',
        r'\b(owasp|security.*compliance|security.*review)\b'
    ]
    
    FEATURE_PATTERNS = [
        r'\b(feature|add.*feature|new.*feature|implement.*feature)\b',
        r'\b(enhancement|improvement|addition)\b'
    ]
    
    @classmethod
    def analyze_manifesto(cls, manifesto: str) -> TaskType:
        """
        Analyze manifesto to determine task type.
        
        Args:
            manifesto: Project manifesto/requirements text
            
        Returns:
            TaskType enum value
        """
        manifesto_lower = manifesto.lower()
        
        # Check patterns in order of specificity (most specific first)
        
        # Test generation (very specific)
        if any(re.search(pattern, manifesto_lower, re.IGNORECASE) for pattern in cls.TEST_GENERATION_PATTERNS):
            return TaskType.TEST_GENERATION
        
        # QA/Testing (specific)
        if any(re.search(pattern, manifesto_lower, re.IGNORECASE) for pattern in cls.QA_PATTERNS):
            return TaskType.QA_TESTING
        
        # Code review (specific)
        if any(re.search(pattern, manifesto_lower, re.IGNORECASE) for pattern in cls.CODE_REVIEW_PATTERNS):
            return TaskType.CODE_REVIEW
        
        # Security audit (specific)
        if any(re.search(pattern, manifesto_lower, re.IGNORECASE) for pattern in cls.SECURITY_PATTERNS):
            return TaskType.SECURITY_AUDIT
        
        # Bug fix (specific)
        if any(re.search(pattern, manifesto_lower, re.IGNORECASE) for pattern in cls.BUG_FIX_PATTERNS):
            return TaskType.BUG_FIX
        
        # Documentation (specific)
        if any(re.search(pattern, manifesto_lower, re.IGNORECASE) for pattern in cls.DOCUMENTATION_PATTERNS):
            return TaskType.DOCUMENTATION
        
        # Refactoring (specific)
        if any(re.search(pattern, manifesto_lower, re.IGNORECASE) for pattern in cls.REFACTORING_PATTERNS):
            return TaskType.REFACTORING
        
        # Feature addition (moderate)
        if any(re.search(pattern, manifesto_lower, re.IGNORECASE) for pattern in cls.FEATURE_PATTERNS):
            return TaskType.FEATURE_ADDITION
        
        # POC (check for minimal/quick indicators)
        if any(re.search(pattern, manifesto_lower, re.IGNORECASE) for pattern in cls.POC_PATTERNS):
            return TaskType.POC
        
        # Default: Full project
        return TaskType.FULL_PROJECT
    
    @classmethod
    def get_required_agents(cls, task_type: TaskType, create_pr: bool = True) -> Dict[str, bool]:
        """
        Determine which agents are required for a given task type.
        
        Args:
            task_type: Type of task to perform
            create_pr: Whether a PR will be created (affects PR Manager requirement)
            
        Returns:
            Dictionary mapping agent roles to whether they're required
        """
        agents = {
            cls.PROJECT_MANAGER: False,
            cls.DEVELOPER: False,
            cls.CODE_REVIEWER: False,
            cls.QA_ENGINEER: False,
            cls.PR_MANAGER: False
        }
        
        if task_type == TaskType.FULL_PROJECT:
            # Full project needs all agents
            agents[cls.PROJECT_MANAGER] = True
            agents[cls.DEVELOPER] = True
            agents[cls.CODE_REVIEWER] = True
            agents[cls.QA_ENGINEER] = True
            agents[cls.PR_MANAGER] = create_pr
        
        elif task_type == TaskType.POC:
            # POC: Just developer, minimal planning
            agents[cls.PROJECT_MANAGER] = False  # Skip formal planning for POC
            agents[cls.DEVELOPER] = True
            agents[cls.CODE_REVIEWER] = False  # Skip review for POC
            agents[cls.QA_ENGINEER] = False  # Skip formal testing for POC
            agents[cls.PR_MANAGER] = create_pr
        
        elif task_type == TaskType.QA_TESTING:
            # QA/Testing: Only QA engineer
            agents[cls.PROJECT_MANAGER] = False
            agents[cls.DEVELOPER] = False
            agents[cls.CODE_REVIEWER] = False
            agents[cls.QA_ENGINEER] = True
            agents[cls.PR_MANAGER] = create_pr
        
        elif task_type == TaskType.CODE_REVIEW:
            # Code review: Reviewer + Developer (for context)
            agents[cls.PROJECT_MANAGER] = False
            agents[cls.DEVELOPER] = True  # Need dev for context
            agents[cls.CODE_REVIEWER] = True
            agents[cls.QA_ENGINEER] = False
            agents[cls.PR_MANAGER] = create_pr
        
        elif task_type == TaskType.BUG_FIX:
            # Bug fix: Developer + Reviewer (light review)
            agents[cls.PROJECT_MANAGER] = False
            agents[cls.DEVELOPER] = True
            agents[cls.CODE_REVIEWER] = True  # Review the fix
            agents[cls.QA_ENGINEER] = True  # Test the fix
            agents[cls.PR_MANAGER] = create_pr
        
        elif task_type == TaskType.DOCUMENTATION:
            # Documentation: Developer + minimal review
            agents[cls.PROJECT_MANAGER] = False
            agents[cls.DEVELOPER] = True
            agents[cls.CODE_REVIEWER] = False  # Light review not needed for docs
            agents[cls.QA_ENGINEER] = False
            agents[cls.PR_MANAGER] = create_pr
        
        elif task_type == TaskType.TEST_GENERATION:
            # Test generation: Developer + QA Engineer
            agents[cls.PROJECT_MANAGER] = False
            agents[cls.DEVELOPER] = True  # May need to understand codebase
            agents[cls.CODE_REVIEWER] = False  # Skip review, focus on tests
            agents[cls.QA_ENGINEER] = True
            agents[cls.PR_MANAGER] = create_pr
        
        elif task_type == TaskType.REFACTORING:
            # Refactoring: Developer + Reviewer (ensure quality maintained)
            agents[cls.PROJECT_MANAGER] = False
            agents[cls.DEVELOPER] = True
            agents[cls.CODE_REVIEWER] = True  # Critical for refactoring
            agents[cls.QA_ENGINEER] = True  # Ensure tests still pass
            agents[cls.PR_MANAGER] = create_pr
        
        elif task_type == TaskType.SECURITY_AUDIT:
            # Security audit: Reviewer (security-focused) + Developer (for fixes)
            agents[cls.PROJECT_MANAGER] = False
            agents[cls.DEVELOPER] = True  # May need to fix issues
            agents[cls.CODE_REVIEWER] = True  # Security-focused review
            agents[cls.QA_ENGINEER] = False
            agents[cls.PR_MANAGER] = create_pr
        
        elif task_type == TaskType.FEATURE_ADDITION:
            # Feature addition: Developer + Reviewer + QA
            agents[cls.PROJECT_MANAGER] = False  # Skip formal planning
            agents[cls.DEVELOPER] = True
            agents[cls.CODE_REVIEWER] = True
            agents[cls.QA_ENGINEER] = True
            agents[cls.PR_MANAGER] = create_pr
        
        return agents
    
    @classmethod
    def get_required_phases(cls, task_type: TaskType, create_pr: bool = True) -> Dict[str, bool]:
        """
        Determine which workflow phases are required for a given task type.
        
        Args:
            task_type: Type of task to perform
            create_pr: Whether a PR will be created
            
        Returns:
            Dictionary mapping phase names to whether they're required
        """
        phases = {
            "planning": False,
            "development": False,
            "code_review": False,
            "testing": False,
            "pr_creation": create_pr
        }
        
        agents = cls.get_required_agents(task_type, create_pr)
        
        phases["planning"] = agents[cls.PROJECT_MANAGER]
        phases["development"] = agents[cls.DEVELOPER]
        phases["code_review"] = agents[cls.CODE_REVIEWER]
        phases["testing"] = agents[cls.QA_ENGINEER]
        
        return phases
    
    @classmethod
    def analyze_and_allocate(cls, manifesto: str, create_pr: bool = True) -> Dict:
        """
        Analyze manifesto and return complete resource allocation.
        
        Args:
            manifesto: Project manifesto/requirements text
            create_pr: Whether a PR will be created
            
        Returns:
            Dictionary with task_type, required_agents, and required_phases
        """
        task_type = cls.analyze_manifesto(manifesto)
        required_agents = cls.get_required_agents(task_type, create_pr)
        required_phases = cls.get_required_phases(task_type, create_pr)
        
        return {
            "task_type": task_type,
            "task_type_name": task_type.value,
            "required_agents": required_agents,
            "required_phases": required_phases,
            "agent_count": sum(1 for required in required_agents.values() if required)
        }
