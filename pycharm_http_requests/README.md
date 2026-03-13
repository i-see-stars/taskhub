# PyCharm HTTP Requests

This directory contains HTTP request files for testing TaskHub API endpoints directly from PyCharm.

## Usage

1. Start the development server:
   ```bash
   make run
   # or
   uv run fastapi dev app/api/main.py
   ```

2. Open any `.http` file in PyCharm
3. Click the green arrow (▶️) next to each request to execute it

## Files

### `auth.http`
Authentication endpoints:
- Register new user
- Login (get access token)
- Get current user info
- Refresh token
- Reset password
- Delete user

### `projects.http`
Project management endpoints:
- Create project
- List all projects
- Get specific project
- Update project
- Delete project

### `issues.http`
Issue management endpoints:
- Create issues (epic, story, task, bug)
- List all issues
- Filter issues by project
- Get specific issue
- Update issue
- Assign issue
- Delete issue

## Workflow

1. **First time setup:**
   - Run requests in `auth.http` to register and login
   - This will save `access_token` to environment variables

2. **Create a project:**
   - Run "Create a new project" in `projects.http`
   - This will save `project_id` for use in issues

3. **Create issues:**
   - Run requests in `issues.http` to create issues in your project
   - Issues can be hierarchical (epic → story → task)

## Environment Variables

The HTTP files automatically save and reuse these variables:
- `access_token` - JWT access token (from login)
- `refresh_token` - JWT refresh token
- `user_id` - Current user ID
- `project_id` - Last created project ID
- `epic_id`, `story_id`, `task_id`, `bug_id` - Issue IDs

These are saved in PyCharm's HTTP Client environment and persist across requests.
