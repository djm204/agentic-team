# Agentic Project Creation Team

A reusable CrewAI-based agentic team that takes a project manifesto and creates the complete project, with the ability to create and merge pull requests. Features approval checkpoints, notifications, context management, and industry-standard practices.

## Features

- 🤖 **Multi-Agent Team**: Specialized agents for planning, development, code review, testing, and PR management
- 📋 **Manifesto-Driven**: Simply provide a project manifesto and the team handles the rest
- 🔄 **GitHub Integration**: Automatically create and merge pull requests
- ✅ **Approval Checkpoints**: Check-ins at crucial moments (plan, implementation, pre-PR)
- 🔔 **Notifications**: Get notified when plans complete, tests pass, PRs are created/merged
- 💬 **Discord Integration**: Real-time updates in Discord server for all planning and development activities
- 🤝 **Agent Collaboration**: Standups, peer reviews, and mutual assistance between agents
- 📊 **Agent Performance Management**: Agents judge each other and can be fired/replaced if underperforming
- 📝 **Complete Action Logging**: Every agent action is documented in Discord
- 🚧 **Technical Hurdle Detection**: Automatically detects and escalates technical challenges
- 🧠 **Context Window Management**: Prevents context window over-saturation
- 🔒 **Industry Standards**: Security, PII handling, comprehensive testing, CI/CD integration
- 🤝 **Collaborative**: Agents elevate each other through feedback and collaboration
- 🧪 **Testing**: Comprehensive test suite creation with pass/fail notifications

## Architecture

The team consists of five specialized agents:

1. **Project Manager**: Analyzes manifestos and creates detailed development plans with security, testing, and CI/CD considerations
2. **Developer**: Implements the project with security, PII handling, tests, and CI/CD configuration
3. **Code Reviewer**: Reviews code for quality, security, PII compliance, testing, and CI/CD integration
4. **QA Engineer**: Creates comprehensive test suites and validates test results
5. **PR Manager**: Creates and manages pull requests with comprehensive documentation

### Workflow

1. **Planning Phase** → Approval Checkpoint
2. **Development Phase** → Approval Checkpoint
3. **Code Review Phase**
4. **Testing Phase** → Notification (pass/fail)
5. **PR Creation** → Pre-PR Approval Checkpoint → Notification
6. **PR Merge** (optional) → Notification

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd agentic-team
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```env
OPENAI_API_KEY=your_openai_api_key_here
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_REPO_OWNER=your_username
GITHUB_REPO_NAME=your_repo_name
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here  # Optional: for real-time updates
```

### Discord Setup (Optional but Recommended)

To enable real-time planning updates in Discord:

1. **Create a Discord Webhook:**
   - Go to your Discord server
   - Server Settings → Integrations → Webhooks
   - Click "New Webhook"
   - Choose a channel for updates
   - Copy the webhook URL

2. **Add to `.env`:**
   ```env
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url
   ```

3. **Enable in code:**
   ```python
   team = ProjectCreationTeam(
       discord_webhook_url="your_webhook_url",  # or from env
       enable_discord_streaming=True
   )
   ```

You'll receive real-time updates in Discord for:
- Planning phase progress
- Implementation updates
- Code review status
- Test results
- PR creation and merging
- Technical hurdles
- Approval requests

## Usage

### Basic Usage

```python
from team import ProjectCreationTeam

# Initialize the team with notification callback
def notification_callback(notification_type, data):
    """Handle notifications (email, Slack, etc.)"""
    print(f"Notification: {notification_type.value}")

team = ProjectCreationTeam(
    github_token="your_token",
    github_owner="your_username",
    github_repo="your_repo",
    notification_callback=notification_callback,
    auto_approve=False,  # Set True for automated workflows
    discord_webhook_url="your_discord_webhook_url",  # Optional: for real-time Discord updates
    enable_discord_streaming=True  # Enable real-time streaming to Discord
)

# Create project from manifesto
manifesto = """
Create a Python REST API with FastAPI that handles user authentication
and provides CRUD operations for a blog post system.
"""

result = team.create_project_from_manifesto(
    manifesto=manifesto,
    create_pr=True,
    branch_name="feature/blog-api",
    auto_merge=False,
    write_files=True,  # Write files to disk
    output_dir="./generated_project"  # Output directory
)

print(f"PR created: {result['pr']['url']}")
print(f"Files created: {len(result['files_created'])}")
print(f"Tests passed: {result['tests_passed']}")
```

### Using Environment Variables

```python
import os
from dotenv import load_dotenv
from team import ProjectCreationTeam

load_dotenv()

team = ProjectCreationTeam()  # Uses env vars automatically

result = team.create_project_from_manifesto(
    manifesto="Your project manifesto here..."
)
```

### Create Pull Request Only

```python
team = ProjectCreationTeam()

pr = team.create_pull_request(
    title="Feature: Add new functionality",
    body="This PR adds new functionality...",
    head="feature/new-feature",
    base="main"
)

print(f"Created PR: {pr.html_url}")
```

### Merge Pull Request

```python
team = ProjectCreationTeam()

# Merge by PR number
merged = team.merge_pull_request(
    pr_number=123,
    merge_method="merge"  # or "squash" or "rebase"
)

if merged:
    print("PR merged successfully!")
```

### List Pull Requests

```python
team = ProjectCreationTeam()

# List open PRs
open_prs = team.list_pull_requests(state="open")

for pr in open_prs:
    print(f"PR #{pr.number}: {pr.title} - {pr.html_url}")
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY` (required): Your OpenAI API key for LLM operations
- `OPENAI_MODEL` (optional): Model to use (default: "gpt-4")
- `OPENAI_TEMPERATURE` (optional): Temperature setting (default: 0.7)
- `GITHUB_TOKEN` (required for PR operations): GitHub personal access token
- `GITHUB_REPO_OWNER` (required for PR operations): Repository owner
- `GITHUB_REPO_NAME` (required for PR operations): Repository name

### GitHub Token Permissions

Your GitHub personal access token needs the following permissions:
- `repo` (Full control of private repositories)
  - `public_repo` (if using public repos)
  - `write:org` (if using organization repos)

## Project Structure

```
agentic-team/
├── agents.py          # Agent definitions
├── tasks.py           # Task definitions
├── team.py            # Main team orchestration
├── github_utils.py    # GitHub integration utilities
├── example.py         # Usage examples
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## How It Works

1. **Planning Phase**: 
   - Project Manager analyzes manifesto and creates detailed plan
   - Technical hurdles are detected
   - **Approval Checkpoint**: You approve the plan before proceeding
   - **Notification**: Plan completion notification

2. **Development Phase**: 
   - Developer implements project with security, PII handling, tests, CI/CD
   - Technical hurdles are detected
   - **Approval Checkpoint**: You approve the implementation before review
   - **Notification**: Implementation completion notification

3. **Review Phase**: 
   - Code Reviewer reviews for quality, security, PII, testing, CI/CD
   - Provides constructive feedback

4. **Testing Phase**: 
   - QA Engineer creates comprehensive test suite
   - Tests are executed
   - **Notification**: Test pass/fail notification

5. **PR Phase**: 
   - **Pre-PR Approval Checkpoint**: You approve before PR creation
   - PR Manager creates pull request with documentation
   - **Notification**: PR created notification
   - **Notification**: PR merged notification (if auto-merge enabled)

## Example Manifesto

```python
manifesto = """
Create a task management web application with:

1. FastAPI backend with REST API
2. SQLite database
3. Task CRUD operations
4. Task status (todo, in-progress, done)
5. Task priorities (low, medium, high)
6. Swagger API documentation
7. Requirements.txt and README

The application should be production-ready with error handling
and input validation.
"""
```

## Error Handling

The team handles errors gracefully:
- If GitHub integration fails, project creation continues without PR
- Missing environment variables are reported with clear error messages
- Branch conflicts are detected before PR creation

## Advanced Features

### Approval Checkpoints

The team checks in with you at crucial moments:
- **Plan Approval**: After plan creation
- **Implementation Approval**: After implementation completion
- **Pre-PR Approval**: Before creating pull request

You can set `auto_approve=True` for automated workflows.

### Notifications

Get notified for:
- Plan completion
- Implementation completion
- Testing passed/failed
- PR created
- PR merged
- Technical hurdles detected

### Discord Real-Time Streaming

When Discord integration is enabled, you'll see real-time updates in your Discord channel:

- **Stage Updates**: When each phase starts/completes (Planning, Development, Review, Testing, PR)
- **Agent Actions**: What each agent is doing in real-time
- **Progress Updates**: Detailed progress information
- **Notifications**: All notifications sent to Discord with rich embeds
- **Approval Requests**: Approval checkpoints with context

The Discord integration provides a live feed of the entire project creation process, making it easy to witness the planning and development in real-time.

### Agent Collaboration & Standups

Agents conduct regular standups to:
- Share progress updates
- Identify collaboration issues
- Help each other solve problems
- Align on project goals

Standups occur:
- Before development phase
- During code review phase
- During testing phase
- Before PR creation (final standup with all agents)

### Peer Reviews & Performance Management

Agents continuously review each other's work:
- **Project Manager** reviews Developer's implementation
- **Code Reviewer** provides formal feedback to Developer
- **QA Engineer** reviews code testability
- **PR Manager** conducts final quality review

**Agent Performance Tracking:**
- Each agent receives peer review ratings (1-5 scale)
- Performance history is tracked
- Agents are evaluated after each phase
- Underperforming agents (rating < 2.0) are automatically fired and replaced

**Agent Firing & Replacement:**
- Agents can be fired for poor performance
- Firing is documented in Discord with reasons
- New agents are automatically created to replace fired ones
- All agent lifecycle events are logged to Discord

### Complete Action Logging

Every agent action is logged to Discord:
- Agent start/progress/complete events
- Decisions made by agents
- Collaboration activities
- Review actions
- Errors and warnings

This provides complete transparency into the agent team's activities.

### Code Quality & DRY Principles

Agents are strictly instructed to:
- **DRY (Don't Repeat Yourself)**: Never duplicate code. Extract common functionality into reusable functions/modules.
- **Simplicity**: Write the simplest solution that works. Avoid over-engineering.
- **Elegance**: Code should be beautiful, readable, and well-structured.
- **Human Readability**: Code must be easy for humans to read and understand.

The Code Reviewer agent specifically checks for:
- DRY violations (counted and reported with line numbers)
- Complexity scores
- Readability scores
- Maintainability scores

All metrics are tracked and displayed in the dashboard.

### Token Efficiency

Agents are instructed to:
- Be concise in responses while maintaining clarity
- Avoid unnecessary verbosity
- Focus on delivering value with minimal token usage
- Reuse context efficiently

Token usage is tracked for:
- Each agent
- Each stage
- Total project usage
- Cost estimates

### Metrics Dashboard

Start the dashboard to view real-time metrics:

```python
from team import ProjectCreationTeam

team = ProjectCreationTeam(...)

# Start dashboard in a separate process/thread
import threading
dashboard_thread = threading.Thread(
    target=team.start_dashboard,
    kwargs={"host": "0.0.0.0", "port": 5000}
)
dashboard_thread.daemon = True
dashboard_thread.start()

# Or run dashboard separately
# python dashboard.py
```

Then visit `http://localhost:5000` to see:
- Token usage by agent and stage
- Cost estimates
- Agent performance metrics
- Code quality scores (DRY violations, complexity, readability, maintainability)
- Project metrics
- Stage performance
- Efficiency scores

The dashboard auto-refreshes every 5 seconds.

### Database Storage

All metrics are stored in a local SQLite database (`metrics.db` by default). You can customize the database path:

```python
team = ProjectCreationTeam(...)
# Metrics are automatically stored in metrics.db

# Or specify custom path via environment variable:
# METRICS_DB_PATH=/path/to/custom.db
```

The database includes:
- **token_usage**: All token usage records with timestamps
- **agent_actions**: All agent actions and events
- **stage_metrics**: Stage performance data
- **project_metrics**: Project statistics
- **code_quality**: Code quality metrics over time

All data is stored locally - no network calls required. You can query the database directly using SQLite tools or Python's sqlite3 module.

### Context Window Management

The system automatically manages context windows:
- Monitors token usage
- Summarizes content when approaching limits
- Prevents over-saturation
- Warns when usage is high

### Technical Hurdle Detection

Automatically detects and escalates:
- Technical challenges
- Missing dependencies
- Security concerns
- Architecture issues
- Integration complexities

Critical hurdles require your approval before proceeding.

### Industry Standards

All agents adhere to:
- **Security**: OWASP Top 10, input validation, secure authentication
- **PII Handling**: Encryption, access controls, GDPR/CCPA compliance
- **Testing**: >80% coverage, unit/integration/e2e tests
- **CI/CD**: Automated pipelines, linting, security scanning

### Inter-Agent Collaboration

Agents work together:
- Provide feedback to each other
- Elevate code quality through suggestions
- Collaborate on complex problems
- Share best practices

## Limitations

- The implementation is generated as text output - you'll need to parse and create actual files
- GitHub operations require proper authentication and repository access
- Large projects may require multiple iterations
- Approval checkpoints require interactive input (use `auto_approve=True` for automation)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.
