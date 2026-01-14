"""
Task definitions for the project creation workflow.
"""
from crewai import Task
from agents import (
    create_project_manager_agent,
    create_developer_agent,
    create_code_reviewer_agent,
    create_pr_manager_agent,
    create_testing_agent,
    get_llm
)
from context_manager import ContextManager


def create_planning_task(manifesto: str, context_manager: ContextManager = None):
    """Creates a task for analyzing the manifesto and creating a development plan."""
    project_manager = create_project_manager_agent(get_llm())
    
    # Manage context window
    if context_manager:
        manifesto = context_manager.truncate_to_fit(manifesto, max_tokens=context_manager.max_input_tokens // 2)
    
    return Task(
        description=f"""Analyze the following project manifesto and create a detailed 
        development plan:

        {manifesto}

        Your plan should include:
        1. Project structure and architecture
        2. Technology stack recommendations
        3. File structure and organization
        4. Key features and components to implement
        5. Dependencies and requirements
        6. Step-by-step implementation roadmap
        7. Security considerations and threat modeling
        8. PII handling requirements and compliance
        9. Testing strategy (unit, integration, e2e)
        10. CI/CD pipeline design
        
        Output a comprehensive plan that a developer can follow to build the project.
        Ensure the plan addresses security, PII handling, testing, and CI/CD from the start.""",
        agent=project_manager,
        expected_output="A detailed development plan with architecture, tech stack, file structure, implementation roadmap, security, PII handling, testing, and CI/CD strategy"
    )


def create_development_task(plan: str, context_manager: ContextManager = None, codebase_summary: str = None):
    """Creates a task for implementing the project based on the plan."""
    developer = create_developer_agent(get_llm())
    
    # Manage context window - summarize plan if needed
    if context_manager:
        plan = context_manager.summarize_for_context(plan, max_tokens=context_manager.max_input_tokens // 3)
    
    codebase_section = ""
    if codebase_summary:
        codebase_section = f"""
        
        **EXISTING CODEBASE ANALYSIS:**
        {codebase_summary}
        
        **CRITICAL FOR TEST GENERATION**: 
        - Analyze the existing code structure above
        - **CHECK FOR "EXISTING TEST PATTERNS" in the codebase summary** - if present, copy those patterns EXACTLY
        - For each file that needs tests, create corresponding test files
        - Test files should mirror the source structure (e.g., tests/test_*.py for *.py files)
        - Write tests for all functions and classes listed in the analysis
        - Ensure test coverage targets 80% or higher
        - Use appropriate testing frameworks (pytest for Python, jest for JavaScript, etc.)
        - Follow the exact import setup and structure shown in existing test patterns
        """
    
    return Task(
        description=f"""Based on the following development plan, implement the complete project:

        {plan}
        {codebase_section}

        Your implementation should:
        1. **FIRST**: Analyze the existing codebase structure (if provided above)
        2. **FOR TEST GENERATION TASKS**: 
           - Identify all files that need unit tests
           - Create test files matching the source file structure
           - Write comprehensive tests for each function and class
           - Ensure tests follow the same directory structure as source code
           - Use proper test naming conventions (test_*.py, *_test.py, etc.)
        3. Create all necessary files and directories
        4. Write production-ready code with proper error handling
        5. **STRICTLY ADHERE TO DRY PRINCIPLES**: Never duplicate code. Extract common functionality into reusable functions/modules.
        6. **PRIORITIZE SIMPLICITY**: Write the simplest solution that works. Avoid over-engineering.
        7. **ENSURE ELEGANCE**: Code should be beautiful, readable, and well-structured.
        8. **MAXIMIZE HUMAN READABILITY**: Use descriptive names, clear structure, and helpful comments.
        9. Include documentation and comments (but be concise - token efficient)
        10. Follow best practices for the chosen technology stack
        11. Ensure code is modular and maintainable
        12. Include any necessary configuration files
        13. Implement security best practices (input validation, secure auth, etc.)
        14. Properly handle PII (encryption, access controls, data minimization)
        15. Write unit tests for all critical functions (aim for >80% coverage)
        16. Include CI/CD configuration files (.github/workflows, etc.)
        
        **CRITICAL**: Before writing any code, check if similar functionality already exists. Reuse it instead of duplicating.
        Be token-efficient: be concise, avoid repetition, and focus on delivering value.
        
        **FILE FORMAT - USE THIS EXACT PATTERN:**
        When creating test files:
        1. **FIRST**: Check the codebase summary above for "EXISTING TEST PATTERNS" and copy them EXACTLY
        2. **IF NO PATTERNS**: Use this default format:
        ```python:tests/test_module_name.py
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        
        import pytest
        from module_name import function_name
        
        def test_function():
            \"\"\"Test that function works correctly.\"\"\"
            assert function_name() == expected
        ```
        
        For non-test files, use this format:
        ```python:path/to/file.py
        # Actual code here
        ```
        
        **DO NOT:**
        - Write descriptive text before code blocks like "For the CI/CD configuration, we could have a..."
        - Write "The content of file.py could look like this:"
        - Include any text outside the code block
        - Write example or hypothetical code
        
        **DO:**
        - Write ONLY the code block with the file path
        - Write actual, runnable code
        - Include proper imports and function definitions
        
        Provide the complete file structure with all code files, tests, and CI/CD configs.""",
        agent=developer,
        expected_output="Complete project implementation with all files, code, tests, documentation, security measures, PII handling, and CI/CD configuration"
    )


def create_review_task(implementation: str, plan: str, context_manager: ContextManager = None):
    """Creates a task for reviewing the implementation."""
    reviewer = create_code_reviewer_agent(get_llm())
    
    # Manage context window - summarize if needed
    if context_manager:
        usage = context_manager.check_context_usage(plan, implementation)
        if usage["warning"]:
            plan = context_manager.summarize_for_context(plan, max_tokens=context_manager.max_input_tokens // 4)
            implementation = context_manager.summarize_for_context(implementation, max_tokens=context_manager.max_input_tokens // 2)
    
    return Task(
        description=f"""Review the following implementation against the original plan:

        Original Plan:
        {plan}

        Implementation:
        {implementation}

        Review for:
        1. Code quality and best practices (SOLID, DRY, maintainability)
        2. Adherence to the plan
        3. Completeness of implementation
        4. Security vulnerabilities (OWASP Top 10, injection attacks, auth flaws)
        5. PII handling compliance (encryption, access controls, data retention)
        6. Test coverage and quality (unit tests, edge cases)
        7. CI/CD integration (proper pipeline configuration)
        8. Performance optimizations
        9. Documentation quality
        
        Provide constructive, actionable feedback. Elevate the code quality by suggesting 
        improvements. Work collaboratively with the developer to understand context.""",
        agent=reviewer,
        expected_output="Comprehensive code review with security, PII, testing, and CI/CD feedback, plus actionable suggestions"
    )


def create_testing_task(implementation: str, plan: str, context_manager: ContextManager = None, codebase_summary: str = None):
    """Creates a task for creating and running tests."""
    tester = create_testing_agent(get_llm())
    
    # Manage context window
    if context_manager:
        usage = context_manager.check_context_usage(plan, implementation)
        if usage["warning"]:
            plan = context_manager.summarize_for_context(plan, max_tokens=context_manager.max_input_tokens // 4)
            implementation = context_manager.summarize_for_context(implementation, max_tokens=context_manager.max_input_tokens // 2)
    
    codebase_section = ""
    if codebase_summary:
        codebase_section = f"""
        
        **EXISTING CODEBASE STRUCTURE:**
        {codebase_summary}
        
        **CRITICAL INSTRUCTIONS FOR TEST GENERATION:**
        - The codebase summary above includes EXISTING TEST PATTERNS that you MUST follow exactly
        - If you see "EXISTING TEST PATTERNS" in the summary, copy that format EXACTLY for all new tests
        - For each Python file listed, create a corresponding test file
        - Test files should be in the tests/ directory and named test_<module_name>.py
        - Write actual test code, NOT examples or hypothetical scenarios
        - Import and test the actual functions and classes from the codebase
        - Ensure test coverage targets 80% or higher
        - Use pytest as the testing framework
        """
    
    return Task(
        description=f"""Create comprehensive tests for the following implementation:

        Plan:
        {plan}

        Implementation:
        {implementation}
        {codebase_section}

        Your testing should include:
        1. **REAL TEST FILES**: Write actual test files with real test code, NOT examples
        2. Unit tests for all functions and classes in the codebase (aim for >80% coverage)
        3. Integration tests for API endpoints and services (if applicable)
        4. Security tests (input validation, authentication, authorization)
        5. PII handling validation tests (if applicable)
        6. Test configuration files (pytest.ini, conftest.py, etc.)
        
        **CRITICAL FORMAT REQUIREMENTS - FOLLOW EXACTLY:**
        
        **STEP 1: Check the codebase summary above for "EXISTING TEST PATTERNS"**
        - If patterns are shown, you MUST copy them EXACTLY
        - The patterns show the exact import setup, function structure, and conventions used
        
        **STEP 2: If no patterns shown, use this default format:**
        ```python:tests/test_module_name.py
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        
        import pytest
        from module_name import function_name, ClassName
        
        def test_function_name():
            \"\"\"Test that function_name works correctly.\"\"\"
            # Actual test code here
            result = function_name()
            assert result == expected_value
        ```
        
        **MANDATORY REQUIREMENTS FOR ALL TEST FILES:**
        - Each test file MUST start with the sys.path setup (shown above or in existing patterns)
        - Each test file MUST import pytest
        - Each test file MUST import the actual modules/functions being tested
        - Each test function MUST start with "def test_" and have a descriptive docstring
        - Each test function MUST contain actual assertions (assert statements)
        - For tests that create files/databases, use try/finally blocks for cleanup
        - For optional dependencies, use @pytest.mark.skipif decorators
        
        **ABSOLUTELY FORBIDDEN:**
        - Do NOT write descriptive text before code blocks like "The content of test_file.py could look like this:"
        - Do NOT write "Given the abstract nature..." or similar disclaimers
        - Do NOT write "For the CI/CD configuration, we could have a..." - just write the file directly
        - Do NOT write sentences like "And, this pattern will be followed..." - write ONLY code
        - Do NOT write placeholder text or "TODO" comments - write complete, working tests
        - Write ONLY the code block with the file path, nothing else
        
        Provide:
        - Complete test files in the format shown above
        - Test execution results (run pytest and show actual results)
        - Coverage report (use pytest-cov)
        - Test status (pass/fail)
        
        Ensure all tests pass before marking as complete.""",
        agent=tester,
        expected_output="Complete test suite with actual test files (not examples), execution results, coverage report, and pass/fail status"
    )


def create_pr_creation_task(review: str, test_results: str = None, branch_name: str = None, context_manager: ContextManager = None):
    """Creates a task for preparing PR documentation."""
    pr_manager = create_pr_manager_agent(get_llm())
    
    branch = branch_name or "feature/project-implementation"
    
    # Manage context window
    if context_manager:
        usage = context_manager.check_context_usage(review, test_results or "")
        if usage["warning"]:
            review = context_manager.summarize_for_context(review, max_tokens=context_manager.max_input_tokens // 2)
            if test_results:
                test_results = context_manager.summarize_for_context(test_results, max_tokens=context_manager.max_input_tokens // 4)
    
    test_section = f"\n\nTest Results:\n{test_results}" if test_results else ""
    
    return Task(
        description=f"""Based on the code review and implementation, create a pull request:

        Code Review:
        {review}
        {test_section}

        Create:
        1. A clear PR title
        2. Detailed PR description with:
           - What was implemented
           - Key changes
           - Security considerations
           - PII handling approach
           - Test results and coverage
           - CI/CD pipeline status
           - Related information
        3. Appropriate labels and categorization
        4. Branch name: {branch}
        
        Format the PR information ready for GitHub API submission.""",
        agent=pr_manager,
        expected_output="PR title, description with test results and CI/CD status, and metadata formatted for GitHub API"
    )
