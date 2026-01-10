# Contributing to Calendar MCP Server

Thank you for your interest in contributing to the Calendar MCP Server! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Project Structure](#project-structure)
5. [Coding Standards](#coding-standards)
6. [Making Changes](#making-changes)
7. [Testing](#testing)
8. [Submitting Changes](#submitting-changes)
9. [Documentation](#documentation)
10. [Future Features](#future-features)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors. We expect all participants to:

- Be respectful and considerate
- Be collaborative and constructive
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discriminatory language
- Personal attacks or trolling
- Publishing others' private information
- Any conduct that would be inappropriate in a professional setting

---

## Getting Started

### Prerequisites

Before you start contributing, ensure you have:

- Python 3.12 or higher
- Git
- A GitHub account
- Basic knowledge of Python and async programming
- Familiarity with the Model Context Protocol (MCP)

### Finding Issues

Good first issues for new contributors:
- Issues labeled `good first issue`
- Issues labeled `documentation`
- Issues labeled `help wanted`

Check the [GitHub Issues](https://github.com/Monipoo0904/calendar-mcp-server/issues) page.

**Note**: If you'd like to contribute but no existing issue matches your idea, please create a new issue first to discuss the proposed changes with maintainers before starting work.

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/calendar-mcp-server.git
cd calendar-mcp-server

# Add upstream remote
git remote add upstream https://github.com/Monipoo0904/calendar-mcp-server.git
```

### 2. Create Virtual Environment

```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install project dependencies
pip install -r requirements.txt

# Install development dependencies (when added)
pip install -r requirements-dev.txt

# Or using uv
uv pip install -r requirements.txt
```

### 4. Verify Setup

```bash
# Test local server
python test_local.py

# Should output something like:
# {'statusCode': 200, 'body': '{"result": "Event \'Demo\' added for 2026-01-01."}'}
```

### 5. Create Feature Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
```

---

## Project Structure

```
calendar-mcp-server/
├── api/
│   └── mcp.py              # Vercel API handler
├── main.py                 # MCP server and tools
├── test_local.py           # Local testing script
├── pyproject.toml          # Project configuration
├── requirements.txt        # Python dependencies
├── vercel.json            # Vercel deployment config
├── README.md              # Project overview
├── ARCHITECTURE.md        # System architecture docs
├── CALENDAR_SYNC.md       # OAuth 2.0 and sync docs
├── API_REFERENCE.md       # API documentation
└── CONTRIBUTING.md        # This file
```

### Component Responsibilities

**main.py**:
- MCP server initialization
- Tool definitions (add_event, view_events, delete_event)
- Prompt definitions (summarize_events)
- Event storage and business logic

**api/mcp.py**:
- HTTP request handling
- Request validation
- Tool routing
- Response formatting
- Error handling

**test_local.py**:
- Local development testing
- Mock request simulation
- Manual verification

---

## Coding Standards

### Python Style Guide

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these specifics:

**Indentation**: 4 spaces (not tabs)

**Line Length**: 
- Maximum 100 characters per line
- 80 characters for docstrings

**Imports**:
```python
# Standard library imports
import json
import sys
from datetime import datetime

# Third-party imports
from mcp.server.fastmcp import FastMCP
import httpx

# Local imports
from . import utils
```

**Naming Conventions**:
- Functions and variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

**Example**:
```python
# Good
def add_event(title: str, date: str, description: str = "") -> str:
    """Add a calendar event."""
    pass

# Bad
def AddEvent(Title, Date, Description=""):
    pass
```

### Type Hints

Always use type hints for function parameters and return values:

```python
from typing import List, Dict, Optional

def get_events(user_id: Optional[str] = None) -> List[Dict[str, str]]:
    """Retrieve events, optionally filtered by user."""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def add_event(title: str, date: str, description: str = "") -> str:
    """
    Add a new calendar event.
    
    Args:
        title: Event title/name
        date: Event date in YYYY-MM-DD format
        description: Optional event description
    
    Returns:
        Success message or error message
    
    Raises:
        ValueError: If date format is invalid
    
    Example:
        >>> add_event("Meeting", "2026-01-15", "Team sync")
        "Event 'Meeting' added for 2026-01-15."
    """
    pass
```

### Code Comments

**Do**: Comment why, not what
```python
# Good: Explains reasoning
# Use case-insensitive comparison to improve user experience
events[:] = [e for e in events if e["title"].lower() != title.lower()]

# Bad: States the obvious
# Compare titles in lowercase
events[:] = [e for e in events if e["title"].lower() != title.lower()]
```

**Don't**: Over-comment obvious code
```python
# Bad: Unnecessary comment
# Add 1 to counter
counter += 1
```

### Error Handling

Always handle errors gracefully:

```python
# Good
try:
    datetime.strptime(date, "%Y-%m-%d")
except ValueError:
    return "Invalid date format. Use YYYY-MM-DD."

# Bad
datetime.strptime(date, "%Y-%m-%d")  # Can crash
```

### Async/Await

Use async/await for I/O operations:

```python
# Good
async def fetch_events(user_id: str) -> List[Dict]:
    """Fetch events asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/users/{user_id}/events")
        return response.json()

# Bad: Blocking I/O in async function
async def fetch_events(user_id: str) -> List[Dict]:
    response = requests.get(f"/users/{user_id}/events")  # Blocks!
    return response.json()
```

---

## Making Changes

### Development Workflow

1. **Create issue** (if one doesn't exist)
2. **Create branch** from main
3. **Make changes** following coding standards
4. **Test locally** using test_local.py
5. **Update documentation** if needed
6. **Commit changes** with clear messages
7. **Push to your fork**
8. **Create pull request**

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(api): add OAuth 2.0 authentication support

Implement OAuth 2.0 authorization code flow for Google Calendar
and Microsoft Outlook integration. Includes token storage and
refresh mechanism.

Closes #42

---

fix(tools): handle empty event list in view_events

Previously would throw error when no events exist.
Now returns user-friendly message.

Fixes #38

---

docs(readme): update installation instructions

Add uv package manager as alternative to pip.
Include troubleshooting section.
```

### Branch Naming

Use descriptive branch names:

```bash
# Features
feature/oauth-authentication
feature/ics-import-export

# Bug fixes
fix/date-validation-error
fix/delete-event-case-sensitivity

# Documentation
docs/api-reference-update
docs/contributing-guide

# Refactoring
refactor/extract-calendar-client
refactor/simplify-error-handling
```

---

## Testing

### Manual Testing

Always test your changes locally:

```bash
# Test basic functionality
python test_local.py

# Test MCP server directly
python main.py
```

### Unit Tests (Future)

When adding new features, include unit tests:

```python
# tests/test_tools.py
import pytest
from main import add_event, view_events, delete_event

def test_add_event():
    """Test adding an event."""
    result = add_event("Test", "2026-01-15", "Test event")
    assert "Event 'Test' added" in result

def test_invalid_date():
    """Test date validation."""
    result = add_event("Test", "invalid-date", "Test")
    assert "Invalid date format" in result

def test_view_empty_events():
    """Test viewing empty calendar."""
    # Clear events first
    events.clear()
    result = view_events()
    assert result == "No events scheduled."

def test_delete_event():
    """Test deleting an event."""
    add_event("Test", "2026-01-15")
    result = delete_event("Test")
    assert "deleted" in result.lower()
```

### Integration Tests (Future)

Test API endpoints:

```python
# tests/test_api.py
import pytest
from api.mcp import handler

class MockRequest:
    method = "POST"
    json = None

@pytest.mark.asyncio
async def test_add_event_endpoint():
    """Test add_event via API."""
    request = MockRequest()
    request.json = {
        "tool": "add_event",
        "input": {
            "title": "Test",
            "date": "2026-01-15"
        }
    }
    
    response = await handler(request)
    assert response["statusCode"] == 200
    assert "added" in response["body"]
```

### Test Coverage

Aim for:
- **Unit tests**: 80%+ coverage
- **Integration tests**: Key workflows covered
- **Edge cases**: Tested explicitly

---

## Submitting Changes

### Pull Request Process

1. **Update your branch**:
```bash
git fetch upstream
git rebase upstream/main
```

2. **Push to your fork**:
```bash
git push origin feature/your-feature-name
```

3. **Create Pull Request**:
   - Go to GitHub repository
   - Click "New Pull Request"
   - Select your branch
   - Fill out PR template

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (specify)

## Testing
- [ ] Tested locally with test_local.py
- [ ] Added unit tests (if applicable)
- [ ] Updated documentation

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No breaking changes (or documented)

## Related Issues
Closes #(issue number)

## Screenshots (if applicable)
```

### Review Process

1. **Automated checks** run (linting, tests)
2. **Maintainer review** (1-2 business days)
3. **Address feedback** if requested
4. **Approval and merge**

### After Merge

1. **Delete your branch**:
```bash
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

2. **Update your fork**:
```bash
git checkout main
git pull upstream main
git push origin main
```

---

## Documentation

### When to Update Documentation

Update documentation when you:
- Add new features
- Change API behavior
- Fix bugs that affect usage
- Add configuration options
- Change architecture

### Documentation Files

**README.md**: 
- High-level overview
- Installation instructions
- Basic usage examples
- Keep concise

**ARCHITECTURE.md**:
- System design
- Component interactions
- Data flow diagrams
- Design decisions

**CALENDAR_SYNC.md**:
- OAuth 2.0 details
- Calendar API integration
- ICS file support
- Implementation guides

**API_REFERENCE.md**:
- Complete API documentation
- All endpoints and tools
- Request/response examples
- Error codes

**CONTRIBUTING.md**:
- Development guidelines
- Contribution process
- Coding standards

### Documentation Style

- Use clear, concise language
- Include code examples
- Add diagrams for complex concepts
- Keep examples up-to-date
- Test all code examples

---

## Future Features

### Planned Enhancements

See [CALENDAR_SYNC.md](CALENDAR_SYNC.md) for detailed plans.

**High Priority**:
1. OAuth 2.0 authentication
2. Google Calendar integration
3. Microsoft Outlook integration
4. Persistent storage (database)

**Medium Priority**:
5. ICS file import/export
6. Recurring events
7. Event reminders
8. Time zone support

**Low Priority**:
9. Event categories/tags
10. Calendar sharing
11. Event attachments
12. Advanced search

### Contributing to Future Features

If you want to work on planned features:

1. Check if an issue exists
2. Comment on the issue to claim it
3. Wait for maintainer approval
4. Follow the implementation plan in CALENDAR_SYNC.md
5. Break large features into smaller PRs

---

## Getting Help

### Resources

- **Documentation**: Start with README.md and ARCHITECTURE.md
- **GitHub Issues**: Search existing issues
- **Discussions**: GitHub Discussions (if enabled)
- **Email**: Contact maintainers directly

### Asking Questions

When asking for help:
- Check documentation first
- Search existing issues
- Provide context and code samples
- Include error messages
- Describe what you've tried

**Good Question**:
```
I'm trying to add OAuth 2.0 authentication following CALENDAR_SYNC.md.
When I call initiate_oauth("google"), I get:

Error: Missing GOOGLE_CLIENT_ID environment variable

I've set it in .env file but it's not being loaded. Here's my code:
[code sample]

What am I missing?
```

**Bad Question**:
```
OAuth doesn't work. Help!
```

---

## Recognition

Contributors will be:
- Listed in repository contributors
- Mentioned in release notes
- Credited in documentation (for significant contributions)

Thank you for contributing to Calendar MCP Server! 🎉

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Last Updated**: January 2026
