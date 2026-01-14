"""
Main team orchestration for project creation from manifestos.
"""
try:
    from crewai import Crew, Process
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    Crew = None
    Process = None

from agents import get_llm
from tasks import (
    create_planning_task,
    create_development_task,
    create_review_task,
    create_testing_task,
    create_pr_creation_task
)
from github_utils import GitHubManager, GitManager
from file_utils import write_files_from_implementation
from notifications import NotificationManager, NotificationType, ApprovalCheckpoint
from context_manager import ContextManager
from technical_hurdles import HurdleDetector, should_escalate
from discord_integration import DiscordIntegration, DiscordStreamingHandler, DiscordMessageType
from agent_collaboration import (
    StandupManager, PeerReviewSystem, AgentManager,
    AgentRecord, AgentPerformance, AgentStatus
)
from agents import (
    create_project_manager_agent, create_developer_agent,
    create_code_reviewer_agent, create_testing_agent, create_pr_manager_agent
)
from metrics_engine import MetricsEngine
from codebase_analyzer import CodebaseAnalyzer
from resource_allocator import ResourceAllocation, TaskType
import os
import json
import re
from datetime import datetime
import tiktoken


class ProjectCreationTeam:
    """
    A reusable agentic team that creates projects from manifestos
    and manages pull requests with approval checkpoints and notifications.
    """
    
    def __init__(
        self,
        github_token: str = None,
        github_owner: str = None,
        github_repo: str = None,
        repo_path: str = ".",
        notification_callback: callable = None,
        auto_approve: bool = False,
        discord_webhook_url: str = None,
        enable_discord_streaming: bool = True
    ):
        """
        Initialize the project creation team.
        
        Args:
            github_token: GitHub personal access token
            github_owner: GitHub repository owner
            github_repo: GitHub repository name
            repo_path: Local repository path
            notification_callback: Optional callback for notifications
            auto_approve: Whether to auto-approve checkpoints (for testing)
            discord_webhook_url: Discord webhook URL for real-time updates
            enable_discord_streaming: Whether to stream agent actions to Discord
        """
        self.github_manager = None
        self.repo_path = repo_path  # Store repo path for codebase analysis
        self.git_manager = GitManager(repo_path)
        
        # Initialize Discord integration
        self.discord = DiscordIntegration(discord_webhook_url)
        self.discord_streaming = DiscordStreamingHandler(self.discord) if enable_discord_streaming and self.discord.enabled else None
        
        # Initialize notification manager with Discord
        self.notification_manager = NotificationManager(
            callback=notification_callback,
            discord_integration=self.discord if self.discord.enabled else None
        )
        
        # Initialize agent collaboration systems
        self.standup_manager = StandupManager(self.discord if self.discord.enabled else None)
        self.peer_review_system = PeerReviewSystem(self.discord if self.discord.enabled else None)
        self.agent_manager = AgentManager(self.discord if self.discord.enabled else None)
        
        # Register agent factories
        self.agent_manager.register_agent_factory("Project Manager", create_project_manager_agent)
        self.agent_manager.register_agent_factory("Senior Software Developer", create_developer_agent)
        self.agent_manager.register_agent_factory("Code Reviewer", create_code_reviewer_agent)
        self.agent_manager.register_agent_factory("QA Engineer & Test Specialist", create_testing_agent)
        self.agent_manager.register_agent_factory("PR Manager", create_pr_manager_agent)
        
        self.context_manager = ContextManager(model=os.getenv("OPENAI_MODEL", "gpt-4"))
        self.hurdle_detector = HurdleDetector()
        self.auto_approve = auto_approve
        
        # Initialize metrics engine with SQLite database
        db_path = os.getenv("METRICS_DB_PATH", "metrics.db")
        self.metrics_engine = MetricsEngine(db_path=db_path)
        # Start the database connection
        self.metrics_engine.start()
        
        # Track active agents
        self.active_agents = {}
        
        # Token tracking setup
        try:
            self.token_encoding = tiktoken.encoding_for_model(os.getenv("OPENAI_MODEL", "gpt-4"))
        except:
            self.token_encoding = tiktoken.get_encoding("cl100k_base")
        
        # Store initial values, but repo name will be parsed from manifesto
        self.github_repo = github_repo
        self.github_owner = github_owner
        
        # Initialize GitHub manager only if token is provided
        # Repo name will be set later from manifesto or created if needed
        if github_token or os.getenv("GITHUB_TOKEN"):
            try:
                self.github_manager = GitHubManager(
                    token=github_token or os.getenv("GITHUB_TOKEN"),
                    owner=github_owner,  # May be None, will be set from manifesto or authenticated user
                    repo_name=None  # Will be set from manifesto or created
                )
            except Exception as e:
                print(f"Warning: GitHub integration not available: {e}")
                self.github_manager = None
    
    def create_project_from_manifesto(
        self,
        manifesto: str,
        create_pr: bool = True,
        branch_name: str = None,
        auto_merge: bool = False,
        write_files: bool = False,
        output_dir: str = "."
    ):
        """
        Create a project from a manifesto with approval checkpoints and notifications.
        When auto_approve is True, this will iterate until the task is fully complete.
        
        Args:
            manifesto: Project manifesto/requirements
            create_pr: Whether to create a pull request
            branch_name: Custom branch name (default: auto-generated)
            auto_merge: Whether to automatically merge the PR after creation
            write_files: Whether to write files to disk from implementation
            output_dir: Directory to write files to (if write_files=True)
        
        Returns:
            Dictionary with project details, plan, implementation, and PR info
        """
        # If auto_approve is enabled, iterate until task is complete
        if self.auto_approve:
            return self._create_project_with_iteration(
                manifesto=manifesto,
                create_pr=create_pr,
                branch_name=branch_name,
                auto_merge=auto_merge,
                write_files=write_files,
                output_dir=output_dir
            )
        else:
            # Single pass execution
            return self._create_project_single_pass(
                manifesto=manifesto,
                create_pr=create_pr,
                branch_name=branch_name,
                auto_merge=auto_merge,
                write_files=write_files,
                output_dir=output_dir
            )
    
    def _create_project_single_pass(
        self,
        manifesto: str,
        create_pr: bool = True,
        branch_name: str = None,
        auto_merge: bool = False,
        write_files: bool = False,
        output_dir: str = "."
    ):
        """
        Single pass project creation (original implementation).
        """
        if not CREWAI_AVAILABLE:
            raise ImportError(
                "crewai is required to use ProjectCreationTeam. "
                "Install it with: pip install crewai"
            )
        
        # If auto_approve is enabled, iterate until task is complete
        if self.auto_approve:
            return self._create_project_with_iteration(
                manifesto=manifesto,
                create_pr=create_pr,
                branch_name=branch_name,
                auto_merge=auto_merge,
                write_files=write_files,
                output_dir=output_dir
            )
        else:
            # Single pass execution
            return self._create_project_single_pass(
                manifesto=manifesto,
                create_pr=create_pr,
                branch_name=branch_name,
                auto_merge=auto_merge,
                write_files=write_files,
                output_dir=output_dir
            )
    
    def _create_project_with_iteration(
        self,
        manifesto: str,
        create_pr: bool = True,
        branch_name: str = None,
        auto_merge: bool = False,
        write_files: bool = False,
        output_dir: str = "."
    ):
        """
        Iterate until task is fully complete. Used when auto_approve is True.
        """
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        all_results = []
        
        print("🤖 Auto-pilot mode: Iterating until task is fully complete...")
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*80}")
            print(f"🔄 Iteration {iteration}/{max_iterations}")
            print(f"{'='*80}")
            
            # Monitor context window before each iteration
            context_usage = self.context_manager.check_context_usage(manifesto)
            if context_usage["warning"]:
                print(f"⚠️ Context window usage: {context_usage['usage_percent']:.1f}%")
                # Summarize manifesto if needed
                if context_usage["usage_percent"] > 90:
                    manifesto = self.context_manager.summarize_for_context(
                        manifesto, 
                        max_tokens=self.context_manager.max_input_tokens // 2
                    )
                    print("   Summarized manifesto to fit context window")
            
            # Execute single pass
            result = self._create_project_single_pass(
                manifesto=manifesto,
                create_pr=create_pr,
                branch_name=branch_name,
                auto_merge=auto_merge or self.auto_approve,  # Force auto-merge in auto mode
                write_files=write_files,
                output_dir=output_dir
            )
            
            all_results.append(result)
            
            # Check if task is complete
            is_complete = self._is_task_complete(result, manifesto)
            
            if is_complete:
                print(f"\n✅ Task completed successfully after {iteration} iteration(s)!")
                return result
            
            # If not complete, prepare for next iteration
            print(f"\n⚠️ Task not yet complete. Analyzing what needs to be done...")
            
            # Update manifesto with feedback for next iteration
            feedback = self._extract_feedback_for_next_iteration(result)
            if feedback:
                manifesto = f"{manifesto}\n\n**Previous Iteration Feedback:**\n{feedback}"
                print(f"   Added feedback to manifesto for next iteration")
            
            # Brief pause to avoid rate limits
            import time
            time.sleep(2)
        
        print(f"\n⚠️ Reached maximum iterations ({max_iterations}). Returning last result.")
        return all_results[-1] if all_results else result
    
    def _is_task_complete(self, result: dict, manifesto: str) -> bool:
        """
        Determine if the task is complete based on result and manifesto.
        """
        # Check if PR was created and merged (if PR creation was requested)
        if result.get("pr"):
            pr_info = result["pr"]
            if "merged" in pr_info and pr_info["merged"]:
                print("   ✅ PR merged successfully")
                return True
            if "error" in pr_info:
                print(f"   ❌ PR creation failed: {pr_info['error']}")
                return False
            if "merge_deferred" in pr_info and pr_info.get("merge_deferred"):
                print(f"   ⏸️  PR merge deferred")
                return False
        
        # Check if tests passed (if testing was required)
        if result.get("tests_passed") is False:
            print("   ❌ Tests failed")
            return False
        
        # Check if critical hurdles were resolved
        hurdles = result.get("hurdles", {})
        critical_plan_hurdles = [h for h in hurdles.get("plan", []) if h.get("severity") == "critical"]
        critical_impl_hurdles = [h for h in hurdles.get("implementation", []) if h.get("severity") == "critical"]
        
        if critical_plan_hurdles or critical_impl_hurdles:
            print(f"   ⚠️  Critical hurdles remain: {len(critical_plan_hurdles + critical_impl_hurdles)}")
            return False
        
        # Check if files were created (if write_files was True)
        if result.get("files_created"):
            files_created = len(result["files_created"])
            if files_created > 0:
                print(f"   ✅ {files_created} files created")
        
        # If we have implementation and no blocking issues, consider complete
        if result.get("implementation") and not result.get("pr", {}).get("merge_deferred"):
            print("   ✅ Implementation complete with no blocking issues")
            return True
        
        return False
    
    def _extract_feedback_for_next_iteration(self, result: dict) -> str:
        """
        Extract feedback from result to inform next iteration.
        """
        feedback_parts = []
        
        # Extract PR feedback
        if result.get("pr"):
            pr_info = result["pr"]
            if pr_info.get("merge_deferred"):
                if pr_info.get("unresolved_feedback_count", 0) > 0:
                    feedback_parts.append(f"- PR has {pr_info['unresolved_feedback_count']} unresolved feedback items")
                if pr_info.get("merge_decision"):
                    feedback_parts.append(f"- PR Manager decision: {pr_info['merge_decision'][:200]}")
        
        # Extract test feedback
        if result.get("tests_passed") is False:
            test_results = result.get("test_results", "")
            if test_results:
                feedback_parts.append(f"- Test failures: {test_results[:300]}")
        
        # Extract hurdle feedback
        hurdles = result.get("hurdles", {})
        critical_hurdles = []
        for h in hurdles.get("plan", []) + hurdles.get("implementation", []):
            if h.get("severity") == "critical":
                critical_hurdles.append(h.get("description", "")[:100])
        
        if critical_hurdles:
            feedback_parts.append(f"- Critical hurdles: {', '.join(critical_hurdles[:3])}")
        
        return "\n".join(feedback_parts) if feedback_parts else ""
    
    def _setup_pre_commit_hooks(self, base_path: str, created_files: list):
        """
        Set up Husky (Node.js) or pre-commit hooks (Python) to run tests on commit.
        """
        import os
        from pathlib import Path
        
        base = Path(base_path)
        
        # Check if this is a Node.js project
        has_package_json = any('package.json' in f for f in created_files) or (base / 'package.json').exists()
        has_node_modules = (base / 'node_modules').exists()
        
        # Check if this is a Python project
        has_pyproject = any('pyproject.toml' in f for f in created_files) or (base / 'pyproject.toml').exists()
        has_setup_py = any('setup.py' in f for f in created_files) or (base / 'setup.py').exists()
        has_requirements = any('requirements' in f for f in created_files) or (base / 'requirements.txt').exists()
        has_pytest = any('pytest' in f.lower() or 'test_' in f.lower() for f in created_files)
        
        is_node_project = has_package_json or has_node_modules
        is_python_project = (has_pyproject or has_setup_py or has_requirements) and has_pytest
        
        if is_node_project:
            print("\n🔧 Setting up Husky pre-commit hooks for Node.js project...")
            try:
                # Create .husky directory
                husky_dir = base / '.husky'
                husky_dir.mkdir(exist_ok=True)
                
                # Create pre-commit hook
                pre_commit_hook = husky_dir / 'pre-commit'
                with open(pre_commit_hook, 'w') as f:
                    f.write("""#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

# Run tests before commit
npm test || exit 1
""")
                
                # Make it executable
                os.chmod(pre_commit_hook, 0o755)
                
                # Update package.json to include husky if it exists
                package_json_path = base / 'package.json'
                if package_json_path.exists():
                    import json
                    try:
                        with open(package_json_path, 'r') as f:
                            package_json = json.load(f)
                        
                        # Add husky to devDependencies if not present
                        if 'devDependencies' not in package_json:
                            package_json['devDependencies'] = {}
                        if 'husky' not in package_json['devDependencies']:
                            package_json['devDependencies']['husky'] = '^8.0.3'
                        
                        # Add prepare script to install husky
                        if 'scripts' not in package_json:
                            package_json['scripts'] = {}
                        if 'prepare' not in package_json['scripts']:
                            package_json['scripts']['prepare'] = 'husky install'
                        
                        with open(package_json_path, 'w') as f:
                            json.dump(package_json, f, indent=2)
                        
                        print("   ✅ Updated package.json with Husky configuration")
                    except Exception as e:
                        print(f"   ⚠️ Could not update package.json: {e}")
                
                print("   ✅ Husky pre-commit hook created")
            except Exception as e:
                print(f"   ⚠️ Could not set up Husky: {e}")
        
        elif is_python_project:
            print("\n🔧 Setting up pre-commit hooks for Python project...")
            try:
                # Create .pre-commit-config.yaml
                pre_commit_config = base / '.pre-commit-config.yaml'
                with open(pre_commit_config, 'w') as f:
                    f.write("""repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        stages: [commit]
""")
                
                # Create .git/hooks/pre-commit if .git exists
                git_hooks_dir = base / '.git' / 'hooks'
                if git_hooks_dir.exists():
                    pre_commit_git_hook = git_hooks_dir / 'pre-commit'
                    with open(pre_commit_git_hook, 'w') as f:
                        f.write("""#!/bin/bash
# Run pytest before commit
pytest || exit 1
""")
                    os.chmod(pre_commit_git_hook, 0o755)
                    print("   ✅ Git pre-commit hook created")
                
                print("   ✅ Pre-commit configuration created")
            except Exception as e:
                print(f"   ⚠️ Could not set up pre-commit hooks: {e}")
    
    def _create_project_single_pass(
        self,
        manifesto: str,
        create_pr: bool = True,
        branch_name: str = None,
        auto_merge: bool = False,
        write_files: bool = False,
        output_dir: str = "."
    ):
        """
        Single pass project creation (original implementation).
        """
        print("🚀 Starting project creation from manifesto...")
        
        # Monitor context window for manifesto
        context_usage = self.context_manager.check_context_usage(manifesto)
        if context_usage["warning"]:
            print(f"⚠️ Context window usage: {context_usage['usage_percent']:.1f}%")
        
        # Analyze manifesto to determine optimal resource allocation
        print("\n🎯 Analyzing project requirements for optimal resource allocation...")
        allocation = ResourceAllocation.analyze_and_allocate(manifesto, create_pr)
        task_type = allocation["task_type"]
        required_agents = allocation["required_agents"]
        required_phases = allocation["required_phases"]
        agent_count = allocation["agent_count"]
        
        print(f"   Task Type: {task_type.value}")
        print(f"   Required Agents: {agent_count}")
        active_agent_names = [name for name, required in required_agents.items() if required]
        print(f"   Agents: {', '.join(active_agent_names) if active_agent_names else 'None'}")
        active_phases = [phase for phase, required in required_phases.items() if required]
        print(f"   Phases: {', '.join(active_phases) if active_phases else 'None'}")
        print(f"   Resource Optimization: {'✅ Optimized' if agent_count < 5 else '⚠️ Full team'}")
        
        # Send Discord notification for start
        if self.discord_streaming:
            self.discord_streaming.on_stage_start("Project Creation")
            from discord_integration import DiscordMessageType
            self.discord.send_message(
                title="🚀 Project Creation Started",
                description=f"Starting project creation from manifesto...\n\n**Task Type:** {task_type.value}\n**Agents:** {', '.join(active_agent_names) if active_agent_names else 'None'}\n**Optimization:** {'✅ Optimized' if agent_count < 5 else '⚠️ Full team'}\n\n**Manifesto Preview:**\n```\n{manifesto[:300]}\n```",
                message_type=DiscordMessageType.INFO
            )
        
        # Check context window for manifesto
        self.context_manager.check_context_usage(manifesto)
        
        # Parse output directory from manifesto if specified
        # Look for patterns like "output_dir: ./" or "output directory: ./" or "write to: ./"
        output_dir_patterns = [
            r'output_dir\s*[:=]\s*([^\s\n]+)',
            r'output\s+directory\s*[:=]\s*([^\s\n]+)',
            r'write\s+to\s*[:=]\s*([^\s\n]+)',
            r'output\s*[:=]\s*([^\s\n]+)'
        ]
        
        parsed_output_dir = None
        for pattern in output_dir_patterns:
            match = re.search(pattern, manifesto, re.IGNORECASE)
            if match:
                parsed_output_dir = match.group(1).strip().strip('"').strip("'")
                # Normalize "./" to "." (current directory)
                if parsed_output_dir == "./" or parsed_output_dir == ".":
                    parsed_output_dir = "."
                break
        
        # Use parsed output_dir if found, otherwise use the provided one
        if parsed_output_dir:
            output_dir = parsed_output_dir
            print(f"📁 Output directory specified in manifesto: {output_dir}")
            # Auto-enable write_files if output_dir is specified in manifesto
            if not write_files:
                write_files = True
                print(f"   (Auto-enabled write_files since output_dir was specified)")
        
        # Parse GitHub repository info from manifesto if specified
        # Look for patterns like "github_repo: repo_name" or "repo: repo_name" or "repository: repo_name"
        repo_patterns = [
            r'github_repo\s*[:=]\s*([^\s\n]+)',
            r'github\s+repo\s*[:=]\s*([^\s\n]+)',
            r'repo\s*[:=]\s*([^\s\n]+)',
            r'repository\s*[:=]\s*([^\s\n]+)'
        ]
        
        parsed_github_repo = None
        for pattern in repo_patterns:
            match = re.search(pattern, manifesto, re.IGNORECASE)
            if match:
                parsed_github_repo = match.group(1).strip().strip('"').strip("'")
                break
        
        # Parse GitHub owner from manifesto if specified
        # Look for patterns like "github_owner: owner" or "owner: owner"
        owner_patterns = [
            r'github_owner\s*[:=]\s*([^\s\n]+)',
            r'github\s+owner\s*[:=]\s*([^\s\n]+)',
            r'owner\s*[:=]\s*([^\s\n]+)'
        ]
        
        parsed_github_owner = None
        for pattern in owner_patterns:
            match = re.search(pattern, manifesto, re.IGNORECASE)
            if match:
                parsed_github_owner = match.group(1).strip().strip('"').strip("'")
                break
        
        # Use parsed repo/owner if found, otherwise use the ones from __init__
        if parsed_github_repo:
            self.github_repo = parsed_github_repo
            print(f"📦 GitHub repository specified in manifesto: {parsed_github_repo}")
        
        if parsed_github_owner:
            self.github_owner = parsed_github_owner
            print(f"👤 GitHub owner specified in manifesto: {parsed_github_owner}")
        
        # If repo is not provided, initialize git locally (and optionally create GitHub repo)
        if not self.github_repo:
            print("\n📦 No GitHub repository specified in manifesto. Initializing local git repository...")
            
            # Initialize local git repo if needed
            if self.git_manager.repo is None:
                self.git_manager.initialize_repo()
                print("   ✅ Initialized local git repository")
            
            # Generate repo name from manifesto or use a default
            if parsed_github_repo:
                repo_name = parsed_github_repo
            else:
                # Generate a repo name from the first line of manifesto
                first_line = manifesto.split('\n')[0].strip()[:50]
                repo_name = re.sub(r'[^a-zA-Z0-9_-]', '-', first_line.lower()).strip('-')
                if not repo_name:
                    repo_name = "new-project"
                print(f"   Generated repository name: {repo_name}")
            
            # Create GitHub repository if we have a token AND create_pr is True
            if create_pr and self.github_manager and self.github_manager.token:
                try:
                    # Get owner from parsed value or authenticated user
                    owner = parsed_github_owner
                    if not owner:
                        # Try to get from existing github_manager or authenticated user
                        if self.github_manager.owner:
                            owner = self.github_manager.owner
                        else:
                            from github import Github
                            github = Github(self.github_manager.token)
                            user = github.get_user()
                            owner = user.login
                    
                    # Create the repository
                    repo = self.github_manager.create_repository(
                        repo_name=repo_name,
                        description=f"Project created from manifesto",
                        private=False,
                        auto_init=True
                    )
                    
                    self.github_repo = repo_name
                    self.github_owner = owner
                    
                    # Update github_manager with new repo
                    self.github_manager.set_repository(owner, repo_name)
                    
                    # Add remote if local repo exists
                    if self.git_manager.repo:
                        try:
                            remote_url = repo.clone_url.replace('https://', f'https://{self.github_manager.token}@')
                            self.git_manager.repo.create_remote('origin', remote_url)
                            print(f"   ✅ Added remote 'origin' to local repository")
                        except Exception as e:
                            print(f"   ⚠️ Could not add remote: {e}")
                    
                    print(f"   ✅ Created GitHub repository: {owner}/{repo_name}")
                    
                except Exception as e:
                    print(f"   ⚠️ Could not create GitHub repository: {e}")
                    print(f"   Continuing with local git repository only...")
            elif create_pr:
                print(f"   ℹ️  No GitHub token available. Using local git repository only.")
                print(f"   Set GITHUB_TOKEN in environment to create a GitHub repository automatically.")
            else:
                print(f"   ℹ️  Using local git repository only (create_pr=False).")
                print(f"   Set create_pr=True and GITHUB_TOKEN to create a GitHub repository automatically.")
        
        # Analyze existing codebase if this is a test generation or enhancement task
        codebase_summary = None
        is_test_task = "test" in manifesto.lower() or "coverage" in manifesto.lower() or "unit test" in manifesto.lower()
        
        # Determine write path (will be used later when writing files)
        # Store it so we can use it in the file writing section
        final_write_path = output_dir
        
        if is_test_task:
            print("\n🔍 Analyzing existing codebase for test generation...")
            try:
                # For test tasks, determine where to analyze and where to write
                # If output_dir is "." or "./", analyze and write to the same directory
                if output_dir == "." or output_dir == "./":
                    # Working in current directory - analyze and write to same place
                    analysis_path = os.getcwd()
                    final_write_path = "."  # Write to current directory
                    print(f"   Working in current directory: {os.path.abspath(analysis_path)}")
                    print(f"   (Test files will be written to the same directory)")
                else:
                    # output_dir is a different directory - analyze current project, write to output_dir
                    if self.repo_path and os.path.exists(self.repo_path) and self.repo_path != ".":
                        analysis_path = self.repo_path
                    else:
                        analysis_path = os.getcwd()
                    final_write_path = output_dir
                    print(f"   Analyzing existing codebase at: {os.path.abspath(analysis_path)}")
                    print(f"   (Test files will be written to: {os.path.abspath(final_write_path)})")
                
                analyzer = CodebaseAnalyzer(base_path=analysis_path)
                code_files = analyzer.find_code_files()
                print(f"   Found {len(code_files)} code files to analyze")
                
                if len(code_files) > 0:
                    codebase_summary = analyzer.get_codebase_summary(max_files=50)
                    analysis_result = analyzer.analyze_codebase()
                    files_without_tests = analysis_result['test_coverage']['files_without_tests']
                    print(f"✅ Analyzed codebase: {len(code_files)} code files found")
                    print(f"   Files needing tests: {files_without_tests}")
                    
                    if self.discord_streaming:
                        self.discord_streaming.send_message(
                            title="Codebase Analysis Complete",
                            description=f"Analyzed {len(code_files)} code files in existing codebase. {files_without_tests} files need tests.",
                            message_type=DiscordMessageType.INFO
                        )
                else:
                    print(f"⚠️ No code files found in {os.path.abspath(analysis_path)}")
                    codebase_summary = f"No code files found in {os.path.abspath(analysis_path)}. Proceed with standard implementation."
                    
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"⚠️ Could not analyze codebase: {e}")
                print(f"   Error details: {error_details[:500]}")
                codebase_summary = f"Codebase analysis failed: {str(e)}. Proceed with standard implementation."
        
        # Step 1: Planning (conditional)
        plan = None
        pm_record = None
        
        if required_phases["planning"]:
            print("\n📋 Step 1: Creating development plan...")
            if self.discord_streaming:
                self.discord_streaming.on_stage_start("Planning Phase")
                self.discord_streaming.on_agent_start("Project Manager", "Analyzing manifesto and creating development plan")
            
            # Include codebase summary in planning if available
            planning_manifesto = manifesto
            if codebase_summary and is_test_task:
                planning_manifesto = f"{manifesto}\n\n**Existing Codebase Structure:**\n{codebase_summary}"
            
            # Monitor context window for planning
            planning_context_usage = self.context_manager.check_context_usage(planning_manifesto)
            if planning_context_usage["warning"]:
                print(f"⚠️ Context window usage for planning: {planning_context_usage['usage_percent']:.1f}%")
                if planning_context_usage["usage_percent"] > 90:
                    planning_manifesto = self.context_manager.summarize_for_context(
                        planning_manifesto,
                        max_tokens=self.context_manager.max_input_tokens // 2
                    )
                    print("   Summarized manifesto for planning phase")
            
            planning_task = create_planning_task(planning_manifesto, self.context_manager)
            pm_agent = planning_task.agent  # Get the Project Manager agent from the task
            
            # Create and register Project Manager agent record
            pm_record = AgentRecord("Project Manager", pm_agent)
            self.standup_manager.register_agent("Project Manager", pm_agent)
            self.active_agents["Project Manager"] = pm_record
            
            planning_crew = Crew(
                agents=[planning_task.agent],
                tasks=[planning_task],
                process=Process.sequential,
                verbose=True
            )
            
            # Stream planning progress to Discord
            if self.discord_streaming:
                self.discord_streaming.on_agent_progress("Project Manager", "Analyzing requirements and creating plan...")
            
            plan_result = planning_crew.kickoff()
            plan = str(plan_result)
            
            if self.discord_streaming:
                self.discord_streaming.on_agent_complete("Project Manager", f"Plan created: {len(plan)} characters")
                self.discord_streaming.on_stage_complete("Planning Phase", "Development plan created successfully")
            
            # Detect technical hurdles in plan
            print("\n🔍 Detecting technical hurdles in plan...")
            plan_hurdles = self.hurdle_detector.detect_hurdles(plan, context="planning")
            critical_hurdles = [h for h in plan_hurdles if should_escalate(h)]
            
            if critical_hurdles:
                for hurdle in critical_hurdles:
                    self.notification_manager.notify(
                        NotificationType.TECHNICAL_HURDLE,
                        hurdle.to_dict(),
                        require_approval=True
                    )
            
            # Notify plan completion and request approval
            print("\n✅ Plan created!")
            approved = self.notification_manager.notify(
                NotificationType.PLAN_COMPLETE,
                {"plan": plan, "hurdles": [h.to_dict() for h in plan_hurdles]},
                require_approval=True
            )
            
            if not approved:
                approval = self.notification_manager.request_approval(
                    ApprovalCheckpoint.PLAN_APPROVAL,
                    {"plan": plan, "auto_approve": self.auto_approve}
                )
                if not approval:
                    return {"error": "Plan approval rejected by user", "plan": plan}
        else:
            # Skip planning phase - use manifesto as plan for simple tasks
            print("\n⏭️  Skipping planning phase (not required for this task type)")
            plan = manifesto  # Use manifesto directly as plan for simple tasks
        
        # Step 2: Development (conditional)
        implementation = None
        dev_record = None
        
        if required_phases["development"]:
            print("\n💻 Step 2: Implementing project...")
            
            # Create and register Developer agent
            developer_agent = create_developer_agent(get_llm())
            dev_record = AgentRecord("Senior Software Developer", developer_agent)
            self.standup_manager.register_agent("Senior Software Developer", developer_agent)
            self.active_agents["Senior Software Developer"] = dev_record
            
            # Conduct standup with available agents
            standup_agents = [pm_record] if pm_record else []
            standup_agents.append(dev_record)
            if standup_agents:
                self.standup_manager.conduct_standup(
                    standup_agents,
                    context="Development phase standup - Developer needs plan clarification"
                )
            
            if self.discord_streaming:
                self.discord_streaming.on_stage_start("Development Phase")
                self.discord_streaming.on_agent_start("Senior Software Developer", "Implementing project based on plan")
                self.discord_streaming.log_agent_action(
                    "Senior Software Developer", "COLLABORATION", "Consulting with Project Manager",
                    {"collaboration_type": "standup", "participants": ["Project Manager", "Developer"] if pm_record else ["Developer"]}
                )
        
            # Monitor context window for development
            dev_context_inputs = [plan]
            if codebase_summary:
                dev_context_inputs.append(codebase_summary)
            dev_context_usage = self.context_manager.check_context_usage(*dev_context_inputs)
            if dev_context_usage["warning"]:
                print(f"⚠️ Context window usage for development: {dev_context_usage['usage_percent']:.1f}%")
                if dev_context_usage["usage_percent"] > 90:
                    plan = self.context_manager.summarize_for_context(
                        plan,
                        max_tokens=self.context_manager.max_input_tokens // 2
                    )
                    if codebase_summary:
                        codebase_summary = self.context_manager.summarize_for_context(
                            codebase_summary,
                            max_tokens=self.context_manager.max_input_tokens // 4
                        )
                    print("   Summarized plan and codebase for development phase")
            
            development_task = create_development_task(plan, self.context_manager, codebase_summary=codebase_summary)
            development_task.agent = developer_agent  # Use registered agent
            development_crew = Crew(
                agents=[development_task.agent],
                tasks=[development_task],
                process=Process.sequential,
                verbose=True
            )
            
            if self.discord_streaming:
                self.discord_streaming.on_agent_progress("Senior Software Developer", "Writing code, implementing features, adding tests...")
                self.discord_streaming.log_agent_action(
                    "Senior Software Developer", "PROGRESS", "Writing code",
                    {"progress": "Implementing features, writing tests, adding CI/CD config"}
                )
            
            implementation_result = development_crew.kickoff()
            implementation = str(implementation_result)
            
            if self.discord_streaming:
                file_count = len(re.findall(r'```\w*:?([^\n]+)', implementation))
                self.discord_streaming.on_agent_complete("Senior Software Developer", f"Implementation complete: {file_count} files")
                self.discord_streaming.log_agent_action(
                    "Senior Software Developer", "COMPLETE", "Implementation complete",
                    {"files_created": file_count, "result": "All code written and tested"}
                )
                self.discord_streaming.on_stage_complete("Development Phase", f"Implementation complete with {file_count} files")
            
            # Peer review: Project Manager reviews Developer's work (if PM exists)
            if pm_record:
                print("\n📝 Project Manager reviewing Developer's work...")
                self.peer_review_system.conduct_peer_review(
                    reviewer_agent=pm_record,
                    reviewed_agent=dev_record,
                    work_product=implementation[:1000],
                    context="Reviewing implementation against plan"
                )
            
            # Detect technical hurdles in implementation
            print("\n🔍 Detecting technical hurdles in implementation...")
            impl_hurdles = self.hurdle_detector.detect_hurdles(implementation, context="implementation")
            critical_impl_hurdles = [h for h in impl_hurdles if should_escalate(h)]
            
            if critical_impl_hurdles:
                for hurdle in critical_impl_hurdles:
                    self.notification_manager.notify(
                        NotificationType.TECHNICAL_HURDLE,
                        hurdle.to_dict(),
                        require_approval=True
                    )
            
            # Calculate implementation stats
            file_count = len(re.findall(r'```\w*:?([^\n]+)', implementation))
            loc_estimate = len(implementation.split('\n'))
            
            # Notify implementation completion and request approval
            print("\n✅ Implementation complete!")
            approved = self.notification_manager.notify(
                NotificationType.IMPLEMENTATION_COMPLETE,
                {
                    "summary": implementation[:500],
                    "file_count": file_count,
                    "loc": loc_estimate,
                    "hurdles": [h.to_dict() for h in impl_hurdles]
                },
                require_approval=True
            )
            
            if not approved:
                approval = self.notification_manager.request_approval(
                    ApprovalCheckpoint.IMPLEMENTATION_APPROVAL,
                    {
                        "summary": implementation[:500],
                        "file_count": file_count,
                        "loc": loc_estimate,
                        "auto_approve": self.auto_approve
                    }
                )
                if not approval:
                    return {
                        "error": "Implementation approval rejected by user",
                        "plan": plan,
                        "implementation": implementation
                    }
        else:
            # Skip development phase - use empty implementation or existing code
            print("\n⏭️  Skipping development phase (not required for this task type)")
            implementation = ""  # Will be populated by other phases if needed
        
        # Step 3: Code Review (conditional)
        review = None
        reviewer_record = None
        
        if required_phases["code_review"]:
            print("\n🔍 Step 3: Reviewing code...")
            
            # Create and register Code Reviewer agent
            reviewer_agent = create_code_reviewer_agent(get_llm())
            reviewer_record = AgentRecord("Code Reviewer", reviewer_agent)
            self.standup_manager.register_agent("Code Reviewer", reviewer_agent)
            self.active_agents["Code Reviewer"] = reviewer_record
            
            # Standup with available agents
            standup_agents = []
            if pm_record:
                standup_agents.append(pm_record)
            if dev_record:
                standup_agents.append(dev_record)
            standup_agents.append(reviewer_record)
            self.standup_manager.conduct_standup(
                standup_agents,
                context="Code review phase - Reviewer needs context from Developer"
            )
            
            if self.discord_streaming:
                self.discord_streaming.on_stage_start("Code Review Phase")
                self.discord_streaming.on_agent_start("Code Reviewer", "Reviewing code for quality, security, and compliance")
                self.discord_streaming.log_agent_action(
                    "Code Reviewer", "START", "Beginning code review",
                    {"review_scope": "Security, PII, Testing, CI/CD"}
                )
            
            # Monitor context window for review
            review_context_usage = self.context_manager.check_context_usage(implementation, plan)
            if review_context_usage["warning"]:
                print(f"⚠️ Context window usage for review: {review_context_usage['usage_percent']:.1f}%")
                if review_context_usage["usage_percent"] > 90:
                    # Summarize implementation more aggressively than plan
                    implementation = self.context_manager.summarize_for_context(
                        implementation,
                        max_tokens=self.context_manager.max_input_tokens // 2
                    )
                    plan = self.context_manager.summarize_for_context(
                        plan,
                        max_tokens=self.context_manager.max_input_tokens // 4
                    )
                    print("   Summarized implementation and plan for review phase")
            
            # Monitor context window for review
            review_context_usage = self.context_manager.check_context_usage(implementation, plan)
            if review_context_usage["warning"]:
                print(f"⚠️ Context window usage for review: {review_context_usage['usage_percent']:.1f}%")
                if review_context_usage["usage_percent"] > 90:
                    # Summarize implementation more aggressively than plan
                    implementation = self.context_manager.summarize_for_context(
                        implementation,
                        max_tokens=self.context_manager.max_input_tokens // 2
                    )
                    plan = self.context_manager.summarize_for_context(
                        plan,
                        max_tokens=self.context_manager.max_input_tokens // 4
                    )
                    print("   Summarized implementation and plan for review phase")
            
            review_task = create_review_task(implementation, plan, self.context_manager)
            review_task.agent = reviewer_agent  # Use registered agent
            review_crew = Crew(
                agents=[review_task.agent],
                tasks=[review_task],
                process=Process.sequential,
                verbose=True
            )
            
            if self.discord_streaming:
                self.discord_streaming.on_agent_progress("Code Reviewer", "Reviewing security, PII handling, testing, and CI/CD...")
                self.discord_streaming.log_agent_action(
                    "Code Reviewer", "PROGRESS", "Analyzing code",
                    {"checks": ["Security", "PII compliance", "Test coverage", "CI/CD"]}
                )
            
            review_result = review_crew.kickoff()
            review = str(review_result)
            
            if self.discord_streaming:
                self.discord_streaming.on_agent_complete("Code Reviewer", "Code review complete")
                self.discord_streaming.log_agent_action(
                    "Code Reviewer", "COMPLETE", "Code review finished",
                    {"review_length": len(review), "result": "Review complete with feedback"}
                )
                self.discord_streaming.on_stage_complete("Code Review Phase", "Code review completed")
            
            print("\n✅ Code review complete!")
            
            # Peer review: Code Reviewer reviews Developer's work (if dev exists)
            if dev_record:
                print("\n📝 Code Reviewer providing peer feedback to Developer...")
                self.peer_review_system.conduct_peer_review(
                    reviewer_agent=reviewer_record,
                    reviewed_agent=dev_record,
                    work_product=review[:1000],
                    context="Formal code review with feedback"
                )
            
            # Extract code quality metrics from review
            dry_violations = 0
            complexity_score = 5.0
            readability_score = 5.0
            maintainability_score = 5.0
            
            # Try to parse metrics from review
            if "DRY Violations Count:" in review:
                try:
                    lines = review.split('\n')
                    for i, line in enumerate(lines):
                        if "DRY Violations Count:" in line:
                            dry_violations = int(re.search(r'\d+', line).group())
                        elif "Complexity Score:" in line:
                            match = re.search(r'(\d+(?:\.\d+)?)', line)
                            if match:
                                complexity_score = float(match.group())
                        elif "Readability Score:" in line:
                            match = re.search(r'(\d+(?:\.\d+)?)', line)
                            if match:
                                readability_score = float(match.group())
                        elif "Maintainability Score:" in line:
                            match = re.search(r'(\d+(?:\.\d+)?)', line)
                            if match:
                                maintainability_score = float(match.group())
                except:
                    pass
            
            # Record code quality metrics (if dev exists)
            if dev_record:
                self.metrics_engine.record_code_quality(
                    "Senior Software Developer",
                    dry_violations=dry_violations,
                    complexity_score=complexity_score,
                    readability_score=readability_score,
                    maintainability_score=maintainability_score
                )
                
                # Evaluate Developer performance
                if self.agent_manager.evaluate_agent("Senior Software Developer", threshold=2.0):
                    print("⚠️ Developer performance below threshold - agent may be replaced")
        else:
            # Skip code review phase
            print("\n⏭️  Skipping code review phase (not required for this task type)")
        
        # Step 4: Testing (conditional)
        test_results = None
        qa_record = None
        
        if required_phases["testing"]:
            print("\n🧪 Step 4: Creating and running tests...")
            
            # Create and register QA Engineer agent
            qa_agent = create_testing_agent(get_llm())
            qa_record = AgentRecord("QA Engineer & Test Specialist", qa_agent)
            self.standup_manager.register_agent("QA Engineer & Test Specialist", qa_agent)
            self.active_agents["QA Engineer & Test Specialist"] = qa_record
            
            # Standup with available agents
            standup_agents = []
            if dev_record:
                standup_agents.append(dev_record)
            standup_agents.append(qa_record)
            self.standup_manager.conduct_standup(
                standup_agents,
                context="Testing phase - QA needs to understand implementation"
            )
            
            if self.discord_streaming:
                self.discord_streaming.on_stage_start("Testing Phase")
                self.discord_streaming.on_agent_start("QA Engineer & Test Specialist", "Creating and running comprehensive test suite")
                self.discord_streaming.log_agent_action(
                    "QA Engineer & Test Specialist", "COLLABORATION", "Consulting with Developer",
                    {"purpose": "Understanding implementation for test creation"}
                )
            
            testing_task = create_testing_task(implementation, plan, self.context_manager, codebase_summary=codebase_summary)
            testing_task.agent = qa_agent  # Use registered agent
            testing_crew = Crew(
                agents=[testing_task.agent],
                tasks=[testing_task],
                process=Process.sequential,
                verbose=True
            )
            
            if self.discord_streaming:
                self.discord_streaming.on_agent_progress("QA Engineer & Test Specialist", "Writing tests, executing test suite...")
                self.discord_streaming.log_agent_action(
                    "QA Engineer & Test Specialist", "PROGRESS", "Creating tests",
                    {"test_types": ["Unit", "Integration", "Security", "PII validation"]}
                )
            
            test_result = testing_crew.kickoff()
            test_results = str(test_result)
            
            if self.discord_streaming:
                self.discord_streaming.on_agent_complete("QA Engineer & Test Specialist", "Test suite complete")
                self.discord_streaming.log_agent_action(
                    "QA Engineer & Test Specialist", "COMPLETE", "Test suite finished",
                    {"test_results": test_results[:200]}
                )
                self.discord_streaming.on_stage_complete("Testing Phase", "Testing phase completed")
            
            # Peer review: QA reviews Developer's testability (if dev exists)
            if dev_record:
                self.peer_review_system.conduct_peer_review(
                    reviewer_agent=qa_record,
                    reviewed_agent=dev_record,
                    work_product=test_results[:1000],
                    context="Reviewing code testability and test coverage"
                )
            
            # Parse test results
            tests_passed = self._parse_test_results(test_results)
            
            if tests_passed:
                self.notification_manager.notify(
                    NotificationType.TESTING_PASSED,
                    {"test_results": test_results}
                )
            else:
                self.notification_manager.notify(
                    NotificationType.TESTING_FAILED,
                    {"test_results": test_results, "test_failures": "See test results above"}
                )
                print("⚠️ Some tests failed. Review test results before proceeding.")
        else:
            # Skip testing phase
            print("\n⏭️  Skipping testing phase (not required for this task type)")
            tests_passed = True  # Default to passed if no testing
        
        # Optional: Write files to disk
        created_files = []
        if write_files:
            print("\n📁 Writing files to disk...")
            try:
                # If creating a PR, write files to the repo_path to ensure they can be committed
                if create_pr and self.github_manager and self.repo_path:
                    if final_write_path == "." or final_write_path == "./":
                        write_path = self.repo_path if self.repo_path != "." else os.getcwd()
                    else:
                        # If output_dir is specified and different from repo_path, use repo_path for PR
                        write_path = self.repo_path if self.repo_path != "." else final_write_path
                    print(f"   Writing to repository directory: {os.path.abspath(write_path)}")
                else:
                    # Use the determined write path (final_write_path was set during analysis or defaults to output_dir)
                    if final_write_path == "." or final_write_path == "./":
                        write_path = os.getcwd()
                        print(f"   Writing to current directory: {os.path.abspath(write_path)}")
                    else:
                        write_path = final_write_path
                        print(f"   Writing to: {os.path.abspath(write_path)}")
                
                # Write files from implementation (development phase)
                impl_files = write_files_from_implementation(implementation, write_path)
                created_files.extend(impl_files)
                
                # Also write test files from test_results (testing phase)
                # This is especially important for test generation tasks
                if test_results:
                    test_files = write_files_from_implementation(test_results, write_path)
                    created_files.extend(test_files)
                    if test_files:
                        print(f"   Created {len(test_files)} test files from testing phase")
                
                # Set up Husky/pre-commit hooks if applicable
                self._setup_pre_commit_hooks(write_path, created_files)
                
                print(f"✅ Created {len(created_files)} total files")
            except Exception as e:
                import traceback
                print(f"⚠️ Error writing files: {e}")
                print(f"   Error details: {traceback.format_exc()[:500]}")
        
        # Step 5: PR Creation (if requested)
        pr_info = None
        if create_pr and self.github_manager:
            print("\n📝 Step 5: Creating pull request...")
            
            # Create and register PR Manager agent
            pr_agent = create_pr_manager_agent(get_llm())
            pr_record = AgentRecord("PR Manager", pr_agent)
            self.standup_manager.register_agent("PR Manager", pr_agent)
            self.active_agents["PR Manager"] = pr_record
            
            # Final standup with all active agents
            all_agents = []
            if pm_record:
                all_agents.append(pm_record)
            if dev_record:
                all_agents.append(dev_record)
            if reviewer_record:
                all_agents.append(reviewer_record)
            if qa_record:
                all_agents.append(qa_record)
            all_agents.append(pr_record)
            if all_agents:
                self.standup_manager.conduct_standup(
                    all_agents,
                    context="Final standup before PR creation - all agents align"
                )
            
            if self.discord_streaming:
                self.discord_streaming.on_stage_start("PR Creation Phase")
                self.discord_streaming.on_agent_start("PR Manager", "Creating pull request")
                self.discord_streaming.log_agent_action(
                    "PR Manager", "COLLABORATION", "Gathering info from all agents",
                    {"sources": ["Developer", "Code Reviewer", "QA Engineer"]}
                )
            
            branch = branch_name or f"feature/project-{hash(manifesto) % 10000}"
            
            # Request approval before creating PR
            approval = self.notification_manager.request_approval(
                ApprovalCheckpoint.PRE_PR_APPROVAL,
                {
                    "title": "Project Implementation",
                    "branch": branch,
                    "body": f"Implementation of project from manifesto.\n\nTest Status: {'✅ Passed' if tests_passed else '❌ Failed'}",
                    "auto_approve": self.auto_approve
                }
            )
            
            if not approval:
                return {
                    "error": "PR creation approval rejected by user",
                    "plan": plan,
                    "implementation": implementation,
                    "review": review,
                    "test_results": test_results
                }
            
            if self.discord_streaming:
                self.discord_streaming.on_agent_progress("PR Manager", "Preparing PR documentation and metadata...")
                self.discord_streaming.log_agent_action(
                    "PR Manager", "PROGRESS", "Compiling PR information",
                    {"sources": ["Code review", "Test results", "Implementation"]}
                )
            
            # Use available review and test results (may be None if phases were skipped)
            pr_review = review if review else "No code review performed (phase skipped)"
            pr_test_results = test_results if test_results else "No testing performed (phase skipped)"
            pr_task = create_pr_creation_task(pr_review, pr_test_results, branch, self.context_manager)
            pr_task.agent = pr_agent  # Use registered agent
            pr_crew = Crew(
                agents=[pr_task.agent],
                tasks=[pr_task],
                process=Process.sequential,
                verbose=True
            )
            pr_result = pr_crew.kickoff()
            pr_data = str(pr_result)
            
            if self.discord_streaming:
                self.discord_streaming.on_agent_complete("PR Manager", "PR documentation ready")
                self.discord_streaming.log_agent_action(
                    "PR Manager", "COMPLETE", "PR documentation finished",
                    {"pr_data_length": len(pr_data)}
                )
            
            # Final peer reviews
            print("\n📝 Conducting final peer reviews...")
            # PR Manager reviews all agents' collaboration (if dev exists)
            if dev_record:
                self.peer_review_system.conduct_peer_review(
                    reviewer_agent=pr_record,
                    reviewed_agent=dev_record,
                    work_product=pr_data[:1000],
                    context="Final review of overall project quality"
                )
            
            # Evaluate all agents
            print("\n📊 Evaluating agent performance...")
            for agent_name in ["Project Manager", "Senior Software Developer", "Code Reviewer", "QA Engineer & Test Specialist", "PR Manager"]:
                if agent_name in self.active_agents:
                    should_fire = self.agent_manager.evaluate_agent(agent_name, threshold=2.0)
                    if should_fire:
                        print(f"⚠️ {agent_name} performance below threshold")
            
            # Parse PR information
            try:
                pr_info = self._parse_pr_info(pr_data, branch)
                
                # Commit and push files before creating PR
                if write_files and created_files:
                    print(f"\n📝 Committing {len(created_files)} files to branch '{branch}'...")
                    try:
                        # Ensure we're in the right directory (repo_path)
                        original_cwd = os.getcwd()
                        repo_dir = self.repo_path if self.repo_path != "." else os.getcwd()
                        
                        if not os.path.exists(repo_dir):
                            raise ValueError(f"Repository directory does not exist: {repo_dir}")
                        
                        # Update git manager to use the correct repo path
                        self.git_manager = GitManager(repo_dir)
                        
                        # Initialize repo if needed
                        if self.git_manager.repo is None:
                            self.git_manager.initialize_repo()
                        
                        os.chdir(repo_dir)
                        
                        # Create/checkout branch locally
                        self.git_manager.create_branch(branch)
                        
                        # Convert absolute paths to relative paths for git
                        relative_files = []
                        for file_path in created_files:
                            if os.path.isabs(file_path):
                                # Make relative to repo directory
                                rel_path = os.path.relpath(file_path, repo_dir)
                            else:
                                rel_path = file_path
                            # Only include if file exists
                            if os.path.exists(os.path.join(repo_dir, rel_path)):
                                relative_files.append(rel_path)
                        
                        if not relative_files:
                            print("⚠️ Warning: No files found to commit. Files may have been written to a different location.")
                        else:
                            # Commit the created files
                            commit_message = f"Add project implementation\n\n{pr_info.get('title', 'Project Implementation')}\n\nFiles created: {len(relative_files)}"
                            self.git_manager.commit_changes(commit_message, files=relative_files)
                            
                            # Push branch to remote
                            print(f"📤 Pushing branch '{branch}' to remote...")
                            self.git_manager.push_branch(branch)
                            
                            print(f"✅ Committed and pushed {len(relative_files)} files to branch '{branch}'")
                        
                        # Restore original directory
                        os.chdir(original_cwd)
                    except Exception as git_error:
                        import traceback
                        print(f"⚠️ Warning: Could not commit/push files locally: {git_error}")
                        print(f"   Error details: {traceback.format_exc()[:300]}")
                        print("   Attempting to create PR anyway (files may need to be committed manually)")
                        # Restore directory even on error
                        try:
                            os.chdir(original_cwd)
                        except:
                            pass
                
                # Create the branch on GitHub (if not already exists from local push)
                try:
                    self.github_manager.create_branch(branch)
                except Exception as e:
                    # Branch might already exist from local push, that's OK
                    print(f"   Branch '{branch}' already exists on remote (from local push)")
                
                # Create the PR
                pr = self.github_manager.create_pull_request(
                    title=pr_info.get("title", "Project Implementation"),
                    body=pr_info.get("body", pr_data),
                    head=branch,
                    base="main"
                )
                
                pr_info.update({
                    "number": pr.number,
                    "url": pr.html_url,
                    "branch": branch
                })
                
                self.notification_manager.notify(
                    NotificationType.PR_CREATED,
                    {
                        "number": pr.number,
                        "url": pr.html_url,
                        "branch": branch
                    }
                )
                
                print(f"\n✅ Pull request created: {pr.html_url}")
                
                if self.discord_streaming:
                    self.discord_streaming.on_stage_complete("PR Creation Phase", f"PR #{pr.number} created successfully")
                
                # Step 6: PR Review and Feedback (always run reviews, even in auto_approve mode)
                # Reviews are essential for quality - we only skip if explicitly auto-merging
                if not auto_merge:
                    print("\n🔍 Step 6: Triggering PR review by agents...")
                    
                    if self.discord_streaming:
                        self.discord_streaming.on_stage_start("PR Review Phase")
                    
                    # Get agents that should review the PR
                    reviewing_agents = []
                    if reviewer_record:
                        reviewing_agents.append(("Code Reviewer", reviewer_record))
                    if dev_record:
                        reviewing_agents.append(("Senior Software Developer", dev_record))
                    if qa_record:
                        reviewing_agents.append(("QA Engineer & Test Specialist", qa_record))
                    
                    # Monitor context window before reviews
                    review_context_usage = self.context_manager.check_context_usage(
                        pr_info.get("body", ""),
                        implementation if implementation else ""
                    )
                    if review_context_usage["warning"]:
                        print(f"⚠️ Context window usage before reviews: {review_context_usage['usage_percent']:.1f}%")
                    
                    # Have each agent review the PR and leave comments
                    for agent_name, agent_record in reviewing_agents:
                        print(f"\n📝 {agent_name} reviewing PR...")
                        
                        if self.discord_streaming:
                            self.discord_streaming.on_agent_start(agent_name, f"Reviewing PR #{pr.number}")
                        
                        # Create PR review task for this agent
                        from tasks import create_pr_review_task
                        
                        # Monitor and manage context for review task
                        review_body = pr_info.get("body", pr_data)
                        review_implementation = implementation if implementation else None
                        if review_implementation:
                            review_context_check = self.context_manager.check_context_usage(
                                review_body, review_implementation
                            )
                            if review_context_check["warning"]:
                                review_implementation = self.context_manager.summarize_for_context(
                                    review_implementation,
                                    max_tokens=self.context_manager.max_input_tokens // 3
                                )
                                print(f"   Summarized implementation for {agent_name} review")
                        
                        pr_review_task = create_pr_review_task(
                            pr_number=pr.number,
                            pr_url=pr.html_url,
                            pr_title=pr_info.get("title", "Project Implementation"),
                            pr_body=review_body,
                            agent=agent_record.agent,
                            implementation=review_implementation,
                            agent_name=agent_name,
                            context_manager=self.context_manager
                        )
                        
                        # Execute review
                        from crewai import Crew, Process
                        review_crew = Crew(
                            agents=[agent_record.agent],
                            tasks=[pr_review_task],
                            process=Process.sequential,
                            verbose=True
                        )
                        review_result = str(review_crew.kickoff())
                        
                        # Post comment to PR
                        try:
                            self.github_manager.add_pr_comment(
                                pr_number=pr.number,
                                comment=review_result,
                                agent_name=agent_name
                            )
                            print(f"✅ {agent_name} posted review comment on PR #{pr.number}")
                            
                            if self.discord_streaming:
                                self.discord_streaming.log_agent_action(
                                    agent_name, "REVIEW", f"Posted review comment on PR #{pr.number}",
                                    {"pr_url": pr.html_url, "comment_length": len(review_result)}
                                )
                        except Exception as comment_error:
                            print(f"⚠️ Could not post comment from {agent_name}: {comment_error}")
                    
                    # Step 7: PR Manager reviews feedback and decides on merge
                    print("\n🤔 Step 7: PR Manager evaluating feedback and merge readiness...")
                    
                    if self.discord_streaming:
                        self.discord_streaming.on_agent_start("PR Manager", "Evaluating PR feedback and merge readiness")
                    
                    # Get all comments on the PR
                    try:
                        pr_comments = self.github_manager.get_pr_comments(pr.number)
                        review_comments = self.github_manager.get_pr_review_comments(pr.number)
                        
                        # Monitor context window for comments
                        comments_text = "\n".join([c.body for c in pr_comments] + [c.body for c in review_comments])
                        if comments_text:
                            comments_context_usage = self.context_manager.check_context_usage(comments_text)
                            if comments_context_usage["warning"]:
                                print(f"⚠️ Context window usage for comments: {comments_context_usage['usage_percent']:.1f}%")
                        
                        # Format comments for merge decision task
                        all_comments = []
                        for comment in pr_comments:
                            all_comments.append({
                                "author": comment.user.login,
                                "body": comment.body,
                                "created_at": comment.created_at,
                                "type": "comment"
                            })
                        for review_comment in review_comments:
                            all_comments.append({
                                "author": review_comment.user.login,
                                "body": review_comment.body,
                                "created_at": review_comment.created_at,
                                "path": review_comment.path,
                                "line": review_comment.line,
                                "type": "review_comment"
                            })
                        
                        # Check for unresolved feedback
                        has_unresolved, unresolved_count, unresolved_list = self.github_manager.has_unresolved_feedback(pr.number)
                        
                        print(f"   Found {len(all_comments)} total comments, {unresolved_count} unresolved feedback items")
                        
                        # Create merge decision task
                        from tasks import create_pr_merge_decision_task
                        
                        # Summarize comments if context window is getting full
                        if len(all_comments) > 20:  # Many comments, might need summarization
                            comments_summary = self.context_manager.summarize_for_context(
                                "\n".join([c.get("body", "") for c in all_comments]),
                                max_tokens=self.context_manager.max_input_tokens // 4
                            )
                            # Keep only most recent comments if too many
                            all_comments = all_comments[-10:]  # Keep last 10 comments
                        
                        merge_decision_task = create_pr_merge_decision_task(
                            pr_number=pr.number,
                            pr_url=pr.html_url,
                            pr_comments=all_comments,
                            context_manager=self.context_manager
                        )
                        merge_decision_task.agent = pr_agent
                        
                        # Execute merge decision
                        merge_crew = Crew(
                            agents=[pr_agent],
                            tasks=[merge_decision_task],
                            process=Process.sequential,
                            verbose=True
                        )
                        merge_decision = str(merge_crew.kickoff())
                        
                        # Parse merge decision
                        merge_decision_lower = merge_decision.lower()
                        should_merge = "approved" in merge_decision_lower and "merge" in merge_decision_lower
                        should_merge = should_merge and "not_ready" not in merge_decision_lower
                        
                        if should_merge and not has_unresolved:
                            print(f"\n✅ PR #{pr.number} approved for merge by PR Manager")
                            
                            # Extract merge method from decision (default to "merge")
                            merge_method = "merge"
                            if "squash" in merge_decision_lower:
                                merge_method = "squash"
                            elif "rebase" in merge_decision_lower:
                                merge_method = "rebase"
                            
                            # Extract commit message if provided
                            commit_message = None
                            if "commit message" in merge_decision_lower or "merge message" in merge_decision_lower:
                                # Try to extract message from decision text
                                lines = merge_decision.split("\n")
                                for i, line in enumerate(lines):
                                    if "commit message" in line.lower() or "merge message" in line.lower():
                                        if i + 1 < len(lines):
                                            commit_message = lines[i + 1].strip()
                                            break
                            
                            # Merge the PR
                            print(f"🔄 Merging PR #{pr.number} using {merge_method} method...")
                            
                            if self.discord_streaming:
                                self.discord_streaming.on_stage_start("PR Merge")
                                self.discord_streaming.on_agent_start("PR Manager", f"Merging PR #{pr.number}")
                            
                            merged = self.github_manager.merge_pull_request(
                                pr_number=pr.number,
                                merge_method=merge_method,
                                commit_message=commit_message
                            )
                            
                            if merged:
                                self.notification_manager.notify(
                                    NotificationType.PR_MERGED,
                                    {
                                        "number": pr.number,
                                        "url": pr.html_url
                                    }
                                )
                                if self.discord_streaming:
                                    self.discord_streaming.on_stage_complete("PR Merge", f"PR #{pr.number} merged successfully")
                                    self.discord_streaming.on_agent_complete("PR Manager", f"Successfully merged PR #{pr.number}")
                                print(f"✅ PR #{pr.number} merged successfully!")
                                pr_info["merged"] = True
                                pr_info["merge_method"] = merge_method
                            else:
                                print(f"⚠️ Failed to merge PR #{pr.number}. Check for conflicts or permissions.")
                                pr_info["merge_attempted"] = True
                                pr_info["merge_failed"] = True
                        else:
                            if has_unresolved:
                                print(f"\n⏸️  PR #{pr.number} has {unresolved_count} unresolved feedback items. Merge deferred.")
                                pr_info["merge_deferred"] = True
                                pr_info["unresolved_feedback_count"] = unresolved_count
                            else:
                                print(f"\n⏸️  PR #{pr.number} not approved for merge by PR Manager.")
                                pr_info["merge_deferred"] = True
                                pr_info["merge_decision"] = merge_decision
                            
                            # Post merge decision comment
                            try:
                                decision_comment = f"**PR Manager Merge Decision:**\n\n{merge_decision}"
                                self.github_manager.add_pr_comment(
                                    pr_number=pr.number,
                                    comment=decision_comment,
                                    agent_name="PR Manager"
                                )
                            except Exception as comment_error:
                                print(f"⚠️ Could not post merge decision comment: {comment_error}")
                    
                    except Exception as review_error:
                        import traceback
                        print(f"⚠️ Error during PR review/merge process: {review_error}")
                        print(f"   Error details: {traceback.format_exc()[:300]}")
                        pr_info["review_error"] = str(review_error)
                
                # Auto-merge if explicitly requested (bypasses review)
                elif auto_merge:
                    print("\n🔄 Auto-merging PR (bypassing review)...")
                    if self.discord_streaming:
                        self.discord_streaming.on_stage_start("PR Merge")
                    merged = self.github_manager.merge_pull_request(pr.number)
                    if merged:
                        self.notification_manager.notify(
                            NotificationType.PR_MERGED,
                            {
                                "number": pr.number,
                                "url": pr.html_url
                            }
                        )
                        if self.discord_streaming:
                            self.discord_streaming.on_stage_complete("PR Merge", f"PR #{pr.number} merged successfully")
                        print("✅ PR merged successfully!")
                        pr_info["merged"] = True
                    else:
                        print("⚠️ Auto-merge failed. Will retry in next iteration if auto_approve is enabled.")
                        pr_info["merge_attempted"] = True
                        pr_info["merge_failed"] = True
                
            except Exception as e:
                print(f"⚠️ Error creating PR: {e}")
                pr_info = {"error": str(e)}
        
        # Record project completion
        if pr_info and "error" not in pr_info:
            self.metrics_engine.update_project_metric("projects_completed", 1)
        elif pr_info and "error" in pr_info:
            self.metrics_engine.update_project_metric("projects_failed", 1)
        
        return {
            "manifesto": manifesto,
            "plan": plan,
            "implementation": implementation,
            "review": review,
            "test_results": test_results,
            "tests_passed": tests_passed,
            "pr": pr_info,
            "files_created": created_files if write_files else [],
            "hurdles": {
                "plan": [h.to_dict() for h in plan_hurdles],
                "implementation": [h.to_dict() for h in impl_hurdles]
            }
        }
    
    def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False
    ):
        """
        Create a pull request directly.
        
        Args:
            title: PR title
            body: PR description
            head: Source branch
            base: Target branch
            draft: Whether to create as draft
        
        Returns:
            Pull request object
        """
        if not self.github_manager:
            raise ValueError("GitHub manager not initialized")
        
        pr = self.github_manager.create_pull_request(
            title=title,
            body=body,
            head=head,
            base=base,
            draft=draft
        )
        
        self.notification_manager.notify(
            NotificationType.PR_CREATED,
            {
                "number": pr.number,
                "url": pr.html_url,
                "branch": head
            }
        )
        
        return pr
    
    def merge_pull_request(
        self,
        pr_number: int,
        merge_method: str = "merge"
    ):
        """
        Merge a pull request.
        
        Args:
            pr_number: PR number
            merge_method: Merge method ('merge', 'squash', or 'rebase')
        
        Returns:
            True if merged successfully
        """
        if not self.github_manager:
            raise ValueError("GitHub manager not initialized")
        
        merged = self.github_manager.merge_pull_request(
            pr_number=pr_number,
            merge_method=merge_method
        )
        
        if merged:
            pr = self.github_manager.get_pull_request(pr_number)
            self.notification_manager.notify(
                NotificationType.PR_MERGED,
                {
                    "number": pr_number,
                    "url": pr.html_url
                }
            )
        
        return merged
    
    def list_pull_requests(self, state: str = "open"):
        """List pull requests in the repository."""
        if not self.github_manager:
            raise ValueError("GitHub manager not initialized")
        
        return self.github_manager.list_pull_requests(state=state)
    
    def _parse_pr_info(self, pr_data: str, branch: str) -> dict:
        """
        Parse PR information from agent output.
        Attempts to extract title and body from structured or unstructured text.
        """
        # Try to parse as JSON first
        try:
            return json.loads(pr_data)
        except:
            pass
        
        # Try to extract from markdown or structured text
        lines = pr_data.split('\n')
        title = None
        body_lines = []
        
        for i, line in enumerate(lines):
            if 'title' in line.lower() and ':' in line:
                title = line.split(':', 1)[1].strip()
            elif 'description' in line.lower() or 'body' in line.lower():
                body_lines = lines[i+1:]
                break
        
        if not title:
            # Use first line as title or generate one
            title = lines[0].strip() if lines else "Project Implementation"
            if len(title) > 100:
                title = title[:97] + "..."
        
        body = '\n'.join(body_lines) if body_lines else pr_data
        
        return {
            "title": title,
            "body": body
        }
    
    def _parse_test_results(self, test_results: str) -> bool:
        """Parse test results to determine if tests passed."""
        test_results_lower = test_results.lower()
        
        # Look for pass indicators
        pass_indicators = ['all tests passed', 'tests passed', '✓', '✅', 'passed:']
        fail_indicators = ['tests failed', 'failed:', '❌', '✗', 'error:', 'failure']
        
        has_pass = any(indicator in test_results_lower for indicator in pass_indicators)
        has_fail = any(indicator in test_results_lower for indicator in fail_indicators)
        
        # If we see explicit failures, return False
        if has_fail and not has_pass:
            return False
        
        # If we see passes and no failures, return True
        if has_pass and not has_fail:
            return True
        
        # Default to True if ambiguous (assume tests were created successfully)
        return True
    
    def start_dashboard(self, host='0.0.0.0', port=5000, debug=False):
        """
        Start the metrics dashboard server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            debug: Enable debug mode
        """
        from dashboard import run_dashboard
        # Pass metrics engine to dashboard
        import dashboard
        dashboard.metrics_engine = self.metrics_engine
        run_dashboard(host=host, port=port, debug=debug)
