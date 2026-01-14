"""
GitHub integration utilities for PR creation and merging.
"""
import os
from github import Github
from git import Repo
import json


class GitHubManager:
    """Manages GitHub operations including PR creation and merging."""
    
    def __init__(self, token: str = None, owner: str = None, repo_name: str = None):
        """
        Initialize GitHub manager.
        
        Args:
            token: GitHub personal access token
            owner: Repository owner (username or org) - optional, can be set later
            repo_name: Repository name - optional, can be set later from manifesto
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.owner = owner  # Don't use env var, will be set from manifesto or authenticated user
        self.repo_name = repo_name  # Don't use env var, will be set from manifesto
        
        if not self.token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN environment variable.")
        
        self.github = Github(self.token)
        self.repo = None
        
        # Only set repo if both owner and repo_name are provided
        if self.owner and self.repo_name:
            try:
                self.repo = self.github.get_repo(f"{self.owner}/{self.repo_name}")
            except Exception:
                # Repo doesn't exist yet, will be created later
                self.repo = None
    
    def set_repository(self, owner: str, repo_name: str):
        """Set or change the target repository."""
        self.owner = owner
        self.repo_name = repo_name
        self.repo = self.github.get_repo(f"{owner}/{repo_name}")
    
    def create_branch(self, branch_name: str, base_branch: str = "main"):
        """Create a new branch from base branch."""
        if not self.repo:
            raise ValueError("Repository not set. Use set_repository() first.")
        
        try:
            # Get base branch reference
            base_ref = self.repo.get_git_ref(f"heads/{base_branch}")
            
            # Create new branch
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=base_ref.object.sha
            )
            return True
        except Exception as e:
            # Branch might already exist
            print(f"Branch creation note: {e}")
            return False
    
    def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False
    ):
        """
        Create a pull request.
        
        Args:
            title: PR title
            body: PR description/body
            head: Source branch name
            base: Target branch name (default: main)
            draft: Whether to create as draft PR
        
        Returns:
            Pull request object
        """
        if not self.repo:
            raise ValueError("Repository not set. Use set_repository() first.")
        
        pr = self.repo.create_pull(
            title=title,
            body=body,
            head=head,
            base=base,
            draft=draft
        )
        
        print(f"Created PR #{pr.number}: {pr.title}")
        print(f"URL: {pr.html_url}")
        
        return pr
    
    def merge_pull_request(
        self,
        pr_number: int,
        merge_method: str = "merge",
        commit_title: str = None,
        commit_message: str = None
    ):
        """
        Merge a pull request.
        
        Args:
            pr_number: Pull request number
            merge_method: One of 'merge', 'squash', or 'rebase'
            commit_title: Custom commit title
            commit_message: Custom commit message
        
        Returns:
            True if merged successfully
        """
        if not self.repo:
            raise ValueError("Repository not set. Use set_repository() first.")
        
        pr = self.repo.get_pull(pr_number)
        
        if pr.merged:
            print(f"PR #{pr_number} is already merged.")
            return True
        
        if not pr.mergeable:
            print(f"PR #{pr_number} is not mergeable. Check for conflicts.")
            return False
        
        result = pr.merge(
            merge_method=merge_method,
            commit_title=commit_title,
            commit_message=commit_message
        )
        
        if result.merged:
            print(f"Successfully merged PR #{pr_number}")
            return True
        else:
            print(f"Failed to merge PR #{pr_number}: {result.message}")
            return False
    
    def list_pull_requests(self, state: str = "open"):
        """List pull requests in the repository."""
        if not self.repo:
            raise ValueError("Repository not set. Use set_repository() first.")
        
        return list(self.repo.get_pulls(state=state))
    
    def get_pull_request(self, pr_number: int):
        """Get a specific pull request by number."""
        if not self.repo:
            raise ValueError("Repository not set. Use set_repository() first.")
        
        return self.repo.get_pull(pr_number)
    
    def add_pr_comment(self, pr_number: int, comment: str, agent_name: str = None):
        """
        Add a comment to a pull request.
        
        Args:
            pr_number: Pull request number
            comment: Comment text
            agent_name: Optional agent name to identify the comment author
        
        Returns:
            Created comment object
        """
        if not self.repo:
            raise ValueError("Repository not set. Use set_repository() first.")
        
        pr = self.repo.get_pull(pr_number)
        
        # Format comment with agent identification if provided
        if agent_name:
            formatted_comment = f"**Comment from {agent_name}:**\n\n{comment}"
        else:
            formatted_comment = comment
        
        issue_comment = pr.create_issue_comment(formatted_comment)
        print(f"Added comment to PR #{pr_number} from {agent_name or 'anonymous'}")
        return issue_comment
    
    def get_pr_comments(self, pr_number: int):
        """
        Get all comments on a pull request.
        
        Args:
            pr_number: Pull request number
        
        Returns:
            List of comment objects
        """
        if not self.repo:
            raise ValueError("Repository not set. Use set_repository() first.")
        
        pr = self.repo.get_pull(pr_number)
        return list(pr.get_issue_comments())
    
    def get_pr_review_comments(self, pr_number: int):
        """
        Get all review comments (line-by-line comments) on a pull request.
        
        Args:
            pr_number: Pull request number
        
        Returns:
            List of review comment objects
        """
        if not self.repo:
            raise ValueError("Repository not set. Use set_repository() first.")
        
        pr = self.repo.get_pull(pr_number)
        return list(pr.get_review_comments())
    
    def has_unresolved_feedback(self, pr_number: int):
        """
        Check if a PR has unresolved feedback (comments that haven't been addressed).
        
        This checks for:
        - Comments containing keywords like "fix", "change", "update", "issue", "problem"
        - Review comments that are not resolved
        - Comments from agents (identified by "Comment from" prefix)
        
        Args:
            pr_number: Pull request number
        
        Returns:
            Tuple of (has_unresolved: bool, unresolved_count: int, unresolved_comments: list)
        """
        if not self.repo:
            raise ValueError("Repository not set. Use set_repository() first.")
        
        pr = self.repo.get_pull(pr_number)
        
        # Keywords that indicate feedback requiring action
        action_keywords = [
            "fix", "change", "update", "modify", "improve", "refactor",
            "issue", "problem", "error", "bug", "concern", "suggestion",
            "should", "must", "need", "required", "missing", "incorrect"
        ]
        
        unresolved_comments = []
        
        # Check regular comments
        for comment in pr.get_issue_comments():
            comment_body = comment.body.lower()
            # Check if comment contains action keywords (but not "fixed", "updated", etc. - past tense)
            has_action = any(keyword in comment_body for keyword in action_keywords)
            # Check if it's from an agent (has "Comment from" prefix)
            is_agent_comment = "comment from" in comment_body
            # Don't count if comment says "looks good", "approved", "resolved", etc.
            is_resolved = any(resolved_word in comment_body for resolved_word in [
                "looks good", "approved", "resolved", "fixed", "addressed", 
                "completed", "done", "lgtm", "no issues"
            ])
            
            if (has_action or is_agent_comment) and not is_resolved:
                unresolved_comments.append({
                    "id": comment.id,
                    "body": comment.body,
                    "author": comment.user.login,
                    "created_at": comment.created_at,
                    "type": "comment"
                })
        
        # Check review comments (line-by-line)
        for review_comment in pr.get_review_comments():
            if not review_comment.in_reply_to_id:  # Only top-level comments
                unresolved_comments.append({
                    "id": review_comment.id,
                    "body": review_comment.body,
                    "author": review_comment.user.login,
                    "created_at": review_comment.created_at,
                    "path": review_comment.path,
                    "line": review_comment.line,
                    "type": "review_comment"
                })
        
        unresolved_count = len(unresolved_comments)
        has_unresolved = unresolved_count > 0
        
        return has_unresolved, unresolved_count, unresolved_comments
    
    def create_repository(
        self,
        repo_name: str,
        description: str = None,
        private: bool = False,
        auto_init: bool = True
    ):
        """
        Create a new GitHub repository.
        
        Args:
            repo_name: Name for the new repository
            description: Repository description
            private: Whether the repository should be private
            auto_init: Whether to initialize with a README
        
        Returns:
            Created repository object
        """
        if not self.token:
            raise ValueError("GitHub token is required to create a repository.")
        
        if not self.owner:
            # Try to get the authenticated user
            user = self.github.get_user()
            self.owner = user.login
        
        # Create the repository
        repo = self.github.get_user().create_repo(
            name=repo_name,
            description=description or f"Project created from manifesto: {repo_name}",
            private=private,
            auto_init=auto_init
        )
        
        # Update internal state
        self.repo_name = repo_name
        self.repo = repo
        
        print(f"✅ Created repository: {self.owner}/{repo_name}")
        print(f"   URL: {repo.html_url}")
        
        return repo


class GitManager:
    """Manages local Git operations."""
    
    def __init__(self, repo_path: str = "."):
        """
        Initialize Git manager.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = repo_path
        try:
            self.repo = Repo(repo_path)
        except Exception:
            self.repo = None
    
    def initialize_repo(self):
        """Initialize a new git repository if one doesn't exist."""
        if self.repo is None:
            self.repo = Repo.init(self.repo_path)
            return True
        return False
    
    def create_branch(self, branch_name: str):
        """Create and checkout a new branch."""
        if self.repo is None:
            self.initialize_repo()
        
        if branch_name in [head.name for head in self.repo.heads]:
            self.repo.git.checkout(branch_name)
        else:
            self.repo.git.checkout('-b', branch_name)
        
        return branch_name
    
    def commit_changes(self, message: str, files: list = None):
        """Commit changes to the repository."""
        if self.repo is None:
            raise ValueError("Repository not initialized")
        
        if files:
            self.repo.index.add(files)
        else:
            self.repo.index.add(self.repo.untracked_files)
            self.repo.index.add([item.a_path for item in self.repo.index.diff(None)])
        
        self.repo.index.commit(message)
    
    def push_branch(self, branch_name: str, remote: str = "origin"):
        """Push branch to remote repository."""
        if self.repo is None:
            raise ValueError("Repository not initialized")
        
        self.repo.git.push(remote, branch_name)
