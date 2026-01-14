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

        Your implementation should follow the **TRACER BULLET** approach:
        
        **TRACER BULLET METHODOLOGY (MANDATORY):**
        1. **START SIMPLE**: Begin with the absolute minimum working version
        2. **GET IT WORKING**: Make sure the core functionality works end-to-end first
        3. **ITERATE**: Then add features, error handling, and polish incrementally
        4. **VERIFY AS YOU GO**: Test each iteration to ensure it still works
        
        **IMPLEMENTATION STEPS:**
        1. **FIRST**: Analyze the existing codebase structure (if provided above)
        2. **FOR TEST GENERATION TASKS**: 
           - Identify all files that need unit tests
           - Create test files matching the source file structure
           - Write comprehensive tests for each function and class
           - Ensure tests follow the same directory structure as source code
           - Use proper test naming conventions (test_*.py, *_test.py, etc.)
        3. **TRACER BULLET PHASE**: Create a minimal working version first
           - Start with the simplest possible implementation
           - Get core functionality working end-to-end
           - Verify it works before adding complexity
        4. **ITERATION PHASE**: Build upon the working foundation
           - Add error handling incrementally
           - Add features one at a time
           - Test after each addition
        5. Create all necessary files and directories
        6. Write production-ready code with proper error handling
        7. **STRICTLY ADHERE TO DRY PRINCIPLES**: Never duplicate code. Extract common functionality into reusable functions/modules.
        8. **PRIORITIZE SIMPLICITY**: Write the simplest solution that works. Avoid over-engineering.
        9. **ENSURE ELEGANCE**: Code should be beautiful, readable, and well-structured.
        10. **MAXIMIZE HUMAN READABILITY**: Use descriptive names, clear structure, and helpful comments.
        11. Include documentation and comments (but be concise - token efficient)
        12. Follow best practices for the chosen technology stack
        13. Ensure code is modular and maintainable
        14. Include any necessary configuration files
        15. Implement security best practices (input validation, secure auth, etc.)
        16. Properly handle PII (encryption, access controls, data minimization)
        17. Write unit tests for all critical functions (aim for >80% coverage)
        18. Include CI/CD configuration files (.github/workflows, etc.)
        19. **INCLUDE HUSKY PRE-COMMIT HOOKS**: Add Husky configuration to run tests on commit
           - For Node.js projects: Add .husky/pre-commit hook that runs tests
           - For Python projects: Add pre-commit hooks (via pre-commit framework or husky-like setup)
           - Ensure tests must pass before commits are allowed
        
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
    """Creates a task for rigorous code review of the implementation."""
    reviewer = create_code_reviewer_agent(get_llm())
    
    # Manage context window - summarize if needed
    if context_manager:
        usage = context_manager.check_context_usage(plan, implementation)
        if usage["warning"]:
            plan = context_manager.summarize_for_context(plan, max_tokens=context_manager.max_input_tokens // 4)
            implementation = context_manager.summarize_for_context(implementation, max_tokens=context_manager.max_input_tokens // 2)
    
    return Task(
        description=f"""Perform a RIGOROUS, SYSTEMATIC code review of the following implementation against the original plan.

        Original Plan:
        {plan}

        Implementation:
        {implementation}

        **MANDATORY REVIEW CHECKLIST - Complete ALL sections:**

        **1. CODE QUALITY & ARCHITECTURE (CRITICAL)**
        - [ ] SOLID principles compliance (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion)
        - [ ] DRY violations: Count and list ALL instances of code duplication with specific file paths and line numbers
        - [ ] Code complexity: Flag functions/classes with high cyclomatic complexity (>10)
        - [ ] Design patterns: Verify appropriate use (or flag over-engineering)
        - [ ] Separation of concerns: Check for proper layering (presentation, business logic, data access)
        - [ ] Dependency management: Verify proper dependency injection and loose coupling
        - [ ] Error handling: Check for comprehensive try/catch blocks and proper error propagation
        - [ ] Logging: Verify appropriate logging levels and structured logging
        - [ ] Code organization: Check file structure, module organization, and naming conventions

        **2. ADHERENCE TO PLAN (MANDATORY)**
        - [ ] Feature completeness: Verify ALL features from plan are implemented
        - [ ] Architecture alignment: Check if implementation matches planned architecture
        - [ ] Technology stack: Verify correct technologies are used as specified
        - [ ] Missing components: List any planned features/components not implemented
        - [ ] Scope creep: Flag any unplanned additions that should be discussed

        **3. SECURITY AUDIT (CRITICAL - OWASP Top 10)**
        - [ ] Injection attacks: SQL injection, NoSQL injection, Command injection, LDAP injection
        - [ ] Broken authentication: Weak passwords, session fixation, credential stuffing vulnerabilities
        - [ ] Sensitive data exposure: Unencrypted data, weak encryption, exposed secrets/API keys
        - [ ] XML External Entities (XXE): If XML parsing exists, verify protection
        - [ ] Broken access control: Missing authorization checks, insecure direct object references
        - [ ] Security misconfiguration: Default credentials, exposed debug info, missing security headers
        - [ ] XSS (Cross-Site Scripting): Input sanitization, output encoding
        - [ ] Insecure deserialization: Verify safe deserialization practices
        - [ ] Using components with known vulnerabilities: Check dependency versions
        - [ ] Insufficient logging & monitoring: Security event logging
        - [ ] Input validation: All user inputs validated and sanitized
        - [ ] Rate limiting: API endpoints protected against abuse
        - [ ] CORS configuration: Properly configured if web app
        - [ ] HTTPS enforcement: Verify secure communication

        **4. PII HANDLING COMPLIANCE (CRITICAL)**
        - [ ] Data minimization: Only collect necessary PII
        - [ ] Encryption at rest: PII encrypted in databases/storage
        - [ ] Encryption in transit: TLS/SSL for all PII transmission
        - [ ] Access controls: Role-based access control (RBAC) for PII
        - [ ] Data retention: Policies and automated deletion of expired PII
        - [ ] Consent management: Proper consent tracking and validation
        - [ ] Right to deletion: Implementation of data deletion requests
        - [ ] Audit logging: All PII access logged with timestamps and user IDs
        - [ ] GDPR compliance: Verify GDPR requirements if applicable
        - [ ] CCPA compliance: Verify CCPA requirements if applicable
        - [ ] Anonymization: PII properly anonymized where possible

        **5. TESTING & QUALITY ASSURANCE (MANDATORY)**
        - [ ] Test coverage: Verify >80% code coverage with specific metrics
        - [ ] Unit tests: All functions/classes have corresponding unit tests
        - [ ] Integration tests: API endpoints and services have integration tests
        - [ ] Edge cases: Tests cover boundary conditions, null inputs, error cases
        - [ ] Test quality: Tests are meaningful, not just coverage padding
        - [ ] Test organization: Tests follow proper structure and naming conventions
        - [ ] Mocking: Proper use of mocks/stubs for external dependencies
        - [ ] Test data: Safe test data, no production data in tests
        - [ ] Performance tests: Critical paths have performance benchmarks
        - [ ] Security tests: Security vulnerabilities tested (e.g., SQL injection attempts)

        **6. CI/CD PIPELINE (MANDATORY)**
        - [ ] Pipeline configuration: Proper CI/CD config files present (.github/workflows, etc.)
        - [ ] Automated testing: Tests run automatically on PR/commit
        - [ ] Linting: Code linting automated in pipeline
        - [ ] Security scanning: Automated security vulnerability scanning
        - [ ] Build process: Automated build and artifact generation
        - [ ] Deployment: Proper deployment automation (if applicable)
        - [ ] Environment management: Proper dev/staging/prod environment handling
        - [ ] Rollback strategy: Ability to rollback deployments

        **7. PERFORMANCE & SCALABILITY (IMPORTANT)**
        - [ ] Database queries: Efficient queries, proper indexing, no N+1 problems
        - [ ] Caching: Appropriate caching strategies implemented
        - [ ] Resource usage: Memory leaks, CPU efficiency, resource cleanup
        - [ ] Async operations: Proper use of async/await where beneficial
        - [ ] API response times: Endpoints meet performance requirements
        - [ ] Scalability: Code can handle increased load

        **8. DOCUMENTATION & MAINTAINABILITY (IMPORTANT)**
        - [ ] Code comments: Complex logic properly commented
        - [ ] Function/class docstrings: All public APIs documented
        - [ ] README: Comprehensive README with setup, usage, and architecture
        - [ ] API documentation: API endpoints documented (OpenAPI/Swagger if applicable)
        - [ ] Architecture docs: System architecture documented
        - [ ] Deployment docs: Deployment and operations documentation
        - [ ] Code readability: Code is self-documenting with clear naming

        **9. CODE METRICS (REQUIRED OUTPUT)**
        Provide specific metrics:
        - DRY Violations Count: [number] with file paths and line numbers
        - Code Coverage: [percentage]%
        - Security Issues Found: [number] (Critical: [X], High: [Y], Medium: [Z])
        - PII Compliance Score: [percentage]% (list any gaps)
        - Test Coverage: [percentage]% (unit: [X]%, integration: [Y]%)
        - Complexity Score: Average cyclomatic complexity: [number]

        **10. ACTIONABLE FEEDBACK (MANDATORY)**
        For each issue found:
        - Severity: Critical / High / Medium / Low
        - Location: File path and line number(s)
        - Description: Clear explanation of the issue
        - Recommendation: Specific, actionable fix suggestion
        - Example: Code example showing the fix (if applicable)

        **REVIEW OUTPUT FORMAT:**
        Structure your review as follows:

        ## Code Review Report

        ### Executive Summary
        - Overall assessment: [PASS/FAIL/WITH_ISSUES]
        - Critical issues: [count]
        - Blocking issues: [list]
        - Recommended action: [APPROVE/REQUEST_CHANGES/REJECT]

        ### Detailed Findings
        [Organize by category above]

        ### Metrics Summary
        [Include all metrics from section 9]

        ### Recommendations
        [Prioritized list of improvements]

        **RIGOR REQUIREMENTS:**
        - Be thorough: Check EVERY file, EVERY function, EVERY security concern
        - Be specific: Provide exact file paths, line numbers, and code examples
        - Be actionable: Every issue must have a clear recommendation
        - Be critical: Don't approve code with critical security issues or major quality problems
        - Be constructive: Help the developer improve, don't just criticize
        - Be token-efficient: Be concise but comprehensive

        This is a RIGOROUS review - leave no stone unturned.""",
        agent=reviewer,
        expected_output="Comprehensive, systematic code review report with checklist completion, metrics, security audit, PII compliance check, and prioritized actionable feedback with file paths and line numbers"
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


def create_pr_review_task(pr_number: int, pr_url: str, pr_title: str, pr_body: str, agent, implementation: str = None, agent_name: str = None, context_manager: ContextManager = None):
    """
    Creates a task for an agent to review a pull request and leave comments.
    
    Args:
        pr_number: Pull request number
        pr_url: URL to the PR
        pr_title: PR title
        pr_body: PR description/body
        agent: The agent that will perform the review (required)
        implementation: Optional implementation code to review
        agent_name: Name of the agent performing the review (for comment identification)
        context_manager: Optional context manager for token management
    """
    # Manage context window
    if context_manager and implementation:
        usage = context_manager.check_context_usage(pr_body, implementation)
        if usage["warning"]:
            implementation = context_manager.summarize_for_context(implementation, max_tokens=context_manager.max_input_tokens // 2)
    
    implementation_section = f"\n\nImplementation Code:\n{implementation}" if implementation else ""
    
    return Task(
        description=f"""Review the following pull request and provide feedback:

        PR #{pr_number}: {pr_title}
        URL: {pr_url}
        
        PR Description:
        {pr_body}
        {implementation_section}

        Your task:
        1. Review the PR thoroughly from your expertise perspective
        2. Identify any issues, concerns, or suggestions
        3. Provide constructive feedback
        4. If you find issues, clearly state what needs to be fixed
        5. If everything looks good, provide approval
        
        **IMPORTANT**: When leaving your comment, you MUST identify yourself as "{agent_name or 'Reviewer'}" 
        at the beginning of your comment so it's clear which agent provided the feedback.
        
        Format your feedback as a comment that will be posted on the PR. Be specific, 
        actionable, and professional. Include file paths and line numbers when referencing code.""",
        agent=agent,
        expected_output=f"Review feedback from {agent_name or 'Reviewer'} formatted as a PR comment, with agent identification at the start"
    )


def create_pr_merge_decision_task(pr_number: int, pr_url: str, pr_comments: list, context_manager: ContextManager = None):
    """
    Creates a task for the PR Manager to decide whether a PR is ready to merge.
    
    Args:
        pr_number: Pull request number
        pr_url: URL to the PR
        pr_comments: List of comments on the PR
        context_manager: Optional context manager for token management
    """
    from agents import create_pr_manager_agent, get_llm
    
    pr_manager = create_pr_manager_agent(get_llm())
    
    # Format comments for context
    comments_text = ""
    if pr_comments:
        for comment in pr_comments:
            author = comment.get("author", "unknown")
            body = comment.get("body", "")
            comment_type = comment.get("type", "comment")
            if comment_type == "review_comment":
                path = comment.get("path", "")
                line = comment.get("line", "")
                comments_text += f"\n\n[{comment_type.upper()}] {author} on {path}:{line}:\n{body}"
            else:
                comments_text += f"\n\n[{comment_type.upper()}] {author}:\n{body}"
    else:
        comments_text = "\n\nNo comments on this PR yet."
    
    # Manage context window
    if context_manager:
        usage = context_manager.check_context_usage(comments_text)
        if usage["warning"]:
            comments_text = context_manager.summarize_for_context(comments_text, max_tokens=context_manager.max_input_tokens // 2)
    
    return Task(
        description=f"""Review the pull request and determine if it's ready to merge:

        PR #{pr_number}: {pr_url}
        
        Comments and Feedback:
        {comments_text}

        Your task:
        1. Review all comments and feedback on the PR
        2. Determine if all critical feedback has been addressed
        3. Check if there are any blocking issues
        4. Verify that the PR meets merge criteria:
           - All critical feedback addressed
           - Tests passing (if applicable)
           - CI/CD green (if applicable)
           - Code review approved
           - No blocking issues
        
        5. Make a decision:
           - If ready to merge: Provide a clear "APPROVED FOR MERGE" decision with merge method recommendation
           - If not ready: List specific issues that must be addressed before merging
        
        Format your decision clearly, indicating:
        - Merge decision (APPROVED / NOT_READY)
        - Merge method recommendation (merge, squash, or rebase)
        - Any remaining issues (if NOT_READY)
        - Merge commit message suggestion (if APPROVED)""",
        agent=pr_manager,
        expected_output="Merge decision (APPROVED/NOT_READY), merge method recommendation, and merge commit message if approved"
    )
