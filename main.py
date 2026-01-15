"""
Main entry point for the Project Creation Team.
Run this script to create a project from a manifesto.
"""
import os
import argparse
from dotenv import load_dotenv
from team import ProjectCreationTeam

# Load environment variables
load_dotenv()


def load_manifesto(file_path: str = None) -> str:
    """
    Load manifesto from a file or return example manifesto.
    
    Args:
        file_path: Path to manifesto file (optional)
    
    Returns:
        Manifesto string
    """
    if file_path and os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    # Return example manifesto if no file provided
    return """
    Create a Python web application for task management with the following features:
    
    1. REST API using FastAPI
    2. SQLite database for storing tasks
    3. Task CRUD operations (Create, Read, Update, Delete)
    4. Task status tracking (todo, in-progress, done)
    5. Task priority levels (low, medium, high)
    6. API documentation with Swagger/OpenAPI
    7. Requirements.txt with all dependencies
    8. README with setup instructions
    
    The application should be production-ready with proper error handling,
    input validation, and clean code structure.
    """


def main(manifesto_file: str = None, auto_approve: bool = False, dry_run: bool = False):
    """
    Create a project from a manifesto.
    
    Args:
        manifesto_file: Optional path to manifesto file. If None, uses example manifesto.
        auto_approve: If True, automatically approve all checkpoints (full auto-pilot mode).
        dry_run: If True, validate initialization but skip actual execution.
    """
    
    # Load manifesto - you can provide a file path or use the default example
    if manifesto_file:
        manifesto = load_manifesto(manifesto_file)
        print(f"📄 Loaded manifesto from: {manifesto_file}")
    else:
        manifesto = load_manifesto()  # Uses example manifesto
        print("📄 Using example manifesto (provide a file path to use your own)")
    
    if dry_run:
        print("🔍 DRY RUN MODE: Validating setup without executing workflow...")
    
    if auto_approve:
        print("🤖 Auto-pilot mode enabled: All checkpoints will be automatically approved")
    
    # Initialize the team with notification callback and Discord integration
    def notification_callback(notification_type, data):
        """Custom notification handler."""
        if not auto_approve:  # Only print notifications if not in auto-pilot mode
            print(f"📬 Notification received: {notification_type.value}")
        # You can add custom logic here (email, Slack, etc.)
    
    team = ProjectCreationTeam(
        github_token=os.getenv("GITHUB_TOKEN"),  # Optional: only needed for GitHub operations
        github_owner=None,  # Will be parsed from manifesto or use authenticated user
        github_repo=None,  # Will be parsed from manifesto or created if needed
        repo_path=".",
        notification_callback=notification_callback,
        auto_approve=auto_approve,  # Use the passed parameter
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),  # Discord webhook for real-time updates
        enable_discord_streaming=True  # Enable real-time streaming to Discord
    )
    
    # Generate branch name and project name from manifesto (first line, sanitized)
    import re
    first_line = manifesto.split('\n')[0].strip()[:50]
    project_suffix = re.sub(r'[^a-zA-Z0-9_-]', '-', first_line.lower()).strip('-')
    if not project_suffix:
        project_suffix = "generated-project"
    branch_name = f"feature/{project_suffix}"
    
    # Default output directory: create outside project root in its own independent folder
    # Use parent directory to ensure it's outside the current repo
    default_output_dir = f"../{project_suffix}"
    
    # Check if output_dir is specified in manifesto (will override this default)
    # The team will parse it and use the manifesto value if present
    
    # Create project from manifesto
    # When --yes is provided, enable full automation including auto-merge
    result = team.create_project_from_manifesto(
        manifesto=manifesto,
        create_pr=not dry_run,  # Skip PR creation in dry-run mode
        branch_name=branch_name,  # Auto-generated from manifesto
        auto_merge=False,  # Keep reviews even in auto_approve mode - only merge when all feedback addressed
        write_files=not dry_run,  # Skip file writing in dry-run mode
        output_dir=default_output_dir,  # Default: outside project root in independent folder
        dry_run=dry_run  # Pass dry-run flag
    )
    
    # Print results
    if result.get('dry_run'):
        # Dry-run mode - validation results already printed
        print("\n" + "="*80)
        print("DRY RUN COMPLETE")
        print("="*80)
        if result.get('ready'):
            print("\n✅ System is ready to execute. Run without --dry-run to proceed.")
        else:
            print("\n❌ System has validation errors. Please fix them before running.")
    else:
        # Normal execution results
        print("\n" + "="*80)
        print("PROJECT CREATION COMPLETE")
        print("="*80)
        if result.get('plan'):
            print(f"\nPlan:\n{result['plan'][:500]}...")
        if result.get('implementation'):
            print(f"\nImplementation:\n{result['implementation'][:500]}...")
        
        if result.get('pr'):
            print(f"\nPull Request: {result['pr'].get('url', 'N/A')}")
            print(f"PR Number: {result['pr'].get('number', 'N/A')}")
        
        if result.get('files_created'):
            print(f"\nFiles Created: {len(result['files_created'])} files")
            for file_path in result['files_created'][:10]:  # Show first 10
                print(f"  - {file_path}")
            if len(result['files_created']) > 10:
                print(f"  ... and {len(result['files_created']) - 10} more")
        
        if result.get('test_results'):
            print(f"\nTest Status: {'✅ Passed' if result.get('tests_passed') else '❌ Failed'}")
        
        if result.get('hurdles'):
            plan_hurdles = result['hurdles'].get('plan', [])
            impl_hurdles = result['hurdles'].get('implementation', [])
            if plan_hurdles or impl_hurdles:
                print(f"\nTechnical Hurdles Detected:")
                print(f"  - Plan: {len(plan_hurdles)}")
                print(f"  - Implementation: {len(impl_hurdles)}")
    
    return result


def example_create_pr_only():
    """Example: Create a PR without full project creation."""
    team = ProjectCreationTeam(
        github_token=os.getenv("GITHUB_TOKEN"),
        github_owner=None,  # Will be parsed from manifesto
        github_repo=None  # Will be parsed from manifesto
    )
    
    # Create a PR directly
    pr = team.create_pull_request(
        title="Feature: Add new functionality",
        body="This PR adds new functionality to the project.",
        head="feature/new-feature",
        base="main"
    )
    
    print(f"Created PR: {pr.html_url}")
    return pr


def example_merge_pr():
    """Example: Merge an existing PR."""
    team = ProjectCreationTeam(
        github_token=os.getenv("GITHUB_TOKEN"),
        github_owner=None,  # Will be parsed from manifesto
        github_repo=None  # Will be parsed from manifesto
    )
    
    # List open PRs
    prs = team.list_pull_requests(state="open")
    print(f"Found {len(prs)} open PRs")
    
    if prs:
        # Merge the first PR
        pr_number = prs[0].number
        merged = team.merge_pull_request(pr_number, merge_method="merge")
        
        if merged:
            print(f"Successfully merged PR #{pr_number}")
        else:
            print(f"Failed to merge PR #{pr_number}")


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Create a project from a manifesto using an agentic team",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py manifesto.txt
  python main.py manifesto.txt --yes
  python main.py --yes manifesto.txt
  python main.py manifesto.txt --dry-run
  
The --yes flag enables auto-pilot mode, automatically approving all checkpoints.
The --dry-run flag validates setup without executing the workflow.
        """
    )
    
    parser.add_argument(
        "manifesto_file",
        nargs="?",
        default=None,
        help="Path to manifesto file (optional, uses example if not provided)"
    )
    
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Auto-approve all checkpoints (full auto-pilot mode)"
    )
    
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Dry run mode: validate setup without executing workflow"
    )
    
    args = parser.parse_args()
    
    # Run the main function with parsed arguments
    main(manifesto_file=args.manifesto_file, auto_approve=args.yes, dry_run=args.dry_run)
    
    # Uncomment to try other examples:
    # example_create_pr_only()
    # example_merge_pr()
