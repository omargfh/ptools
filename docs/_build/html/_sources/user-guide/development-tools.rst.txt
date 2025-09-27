# Development Tools

PTools provides a comprehensive set of development tools to help manage projects, development environments, and workflows.

## Core Development Module (`dev`)

The `dev` module provides essential development utilities for maintaining and working with PTools itself.

### Basic Development Commands

```bash
# Get the project root directory
ptools dev root
/path/to/ptools

# Open the project in VS Code
ptools dev code

# Reinstall PTools in development mode
ptools dev install

# Update PTools to latest version from git
ptools dev update
```

### Development Workflow

#### Making Changes to PTools

1. **Open in editor**:
   ```bash
   ptools dev code
   ```

2. **Make your changes** to the source code

3. **Reinstall to test**:
   ```bash
   ptools dev install
   ```

4. **Test your changes**:
   ```bash
   ptools your-module --help
   ```

#### Updating PTools

```bash
# Pull latest changes and reinstall
ptools dev update
```

This command:
- Pulls latest changes from git
- Automatically runs `ptools dev install`
- Updates all dependencies

## Project Management (`projects`)

The projects module helps you organize and quickly access your development projects.

### Adding Projects

```bash
# Add a new project
ptools projects add my-webapp /home/user/code/webapp

# Add project with description
ptools projects add api-server /home/user/code/api --description "REST API backend"

# Add project with tags
ptools projects add mobile-app /home/user/code/mobile --tags "react-native,ios,android"
```

### Managing Projects

```bash
# List all projects
ptools projects list

# Get detailed project information
ptools projects info my-webapp

# Remove a project
ptools projects remove old-project

# Update project details
ptools projects update my-webapp --description "Updated description"
```

### Working with Projects

```bash
# Open project directory in file manager
ptools projects open my-webapp

# Get project path for use in scripts
PROJECT_PATH=$(ptools projects path my-webapp)
cd "$PROJECT_PATH"

# List projects with specific tags
ptools projects list --tag python
ptools projects list --tag web,frontend
```

### Project Integration Examples

```bash
# Use with other PTools modules
ptools projects list | ptools flow map "x.split()[0]" | head -5

# Backup all projects
ptools projects list | while read name path; do
    ptools rsync do -avz "$path/" "/backup/$name/"
done

# Find Python projects and run tests
ptools projects list --tag python | while read name path; do
    echo "Testing $name..."
    cd "$path" && python -m pytest
done
```

## Shell Integration (`shell`)

The shell module helps manage shell configuration, aliases, and environment variables.

### Managing Aliases

```bash
# Add a new alias
ptools shell alias ll "ls -la"

# Add alias for common git commands
ptools shell alias gst "git status"
ptools shell alias gco "git checkout"

# List all aliases
ptools shell alias list

# Remove an alias
ptools shell alias remove old-alias
```

### Environment Variables

```bash
# Add export statement to shell config
ptools shell x EDITOR "code"
ptools shell x PATH "/new/path:$PATH"

# Force overwrite existing variable
ptools shell x NODE_ENV "development" --force

# List exported variables
ptools shell x list
```

### Shell Configuration

```bash
# Set default shell configuration file
ptools shell set-default-shell ~/.zshrc

# View current shell configuration
ptools shell info
```

### Integration with Development Workflow

```bash
# Set up development environment
ptools shell x PYTHONPATH "/home/user/code/myproject:$PYTHONPATH"
ptools shell alias pt "ptools"
ptools shell alias serve "python -m http.server"

# Project-specific aliases
ptools shell alias build-web "cd ~/code/webapp && npm run build"
ptools shell alias test-api "cd ~/code/api && python -m pytest"
```

## Workspace Management (`ws`)

The workspace module provides tools for managing Node.js workspaces and monorepos.

### Workspace Discovery

```bash
# Find workspaces in current directory
ptools ws find

# Find workspaces with specific pattern
ptools ws find --pattern "packages/*"

# Analyze workspace structure
ptools ws analyze
```

### Package Management

```bash
# List all packages in workspace
ptools ws packages

# Get package dependencies
ptools ws deps package-name

# Find packages with specific dependency
ptools ws find-dep react
```

### Workspace Operations

```bash
# Install dependencies for all packages
ptools ws install

# Run script across all packages
ptools ws run build

# Run script for specific package
ptools ws run test --package api-client
```

## Development Workflow Examples

### Full-Stack Development Setup

```bash
# Add your projects
ptools projects add frontend ~/code/webapp --tags "react,typescript,web"
ptools projects add backend ~/code/api --tags "python,fastapi,api"
ptools projects add mobile ~/code/mobile --tags "react-native,ios,android"

# Set up shell environment
ptools shell x NODE_ENV "development"
ptools shell x API_URL "http://localhost:8000"
ptools shell alias serve-api "cd ~/code/api && uvicorn main:app --reload"
ptools shell alias serve-web "cd ~/code/webapp && npm start"

# Watch for changes and auto-rebuild
ptools watch --path ~/code/api/src --command "ptools projects path backend | xargs -I {} sh -c 'cd {} && python -m pytest'"
```

### Code Quality Workflow

```bash
# Set up aliases for code quality tools
ptools shell alias lint "pylint src/"
ptools shell alias format "black src/ && isort src/"
ptools shell alias type-check "mypy src/"

# Watch for changes and run quality checks
ptools watch --path src/ --regex "\.py$" --command "ptools shell alias format && ptools shell alias lint"
```

### Multi-Project Synchronization

```bash
# Sync multiple projects to remote server
ptools projects list --tag production | while read name path; do
    echo "Syncing $name..."
    ptools rsync watch --path "$path" -avz --exclude node_modules/ "$path/" "user@server:/deploy/$name/"
done
```

## Advanced Development Patterns

### Custom Development Scripts

Create custom development commands by combining PTools modules:

```bash
# Create a script: ~/bin/dev-setup
#!/bin/bash
PROJECT_NAME=$1
PROJECT_PATH=$2

# Add project to PTools
ptools projects add "$PROJECT_NAME" "$PROJECT_PATH"

# Set up development environment
ptools shell x "${PROJECT_NAME^^}_PATH" "$PROJECT_PATH"

# Create useful aliases
ptools shell alias "cd-$PROJECT_NAME" "cd $PROJECT_PATH"
ptools shell alias "test-$PROJECT_NAME" "cd $PROJECT_PATH && npm test"

echo "Development environment set up for $PROJECT_NAME"
```

### AI-Assisted Development

```bash
# Create AI profile for code review
ptools llm-opts create-profile
# Name: code-reviewer
# Temperature: 0.3
# Max tokens: 2000
# System prompt: You are an expert code reviewer...

# Use AI for code review
git diff | ptools llm "Review these changes" --profile code-reviewer

# AI-assisted debugging
ptools llm --interactive --profile debugger --history current-bug
```

### Automated Testing and Deployment

```bash
# Watch for changes and run tests
ptools watch --path src/ --regex "\.py$" --command "python -m pytest tests/ --verbose"

# Automated deployment on successful tests
ptools watch --path src/ --command "
    if python -m pytest; then
        echo 'Tests passed, deploying...'
        ptools rsync do -avz ./ user@server:/app/
    else
        echo 'Tests failed, skipping deployment'
    fi
"
```

## Integration with External Tools

### IDE Integration

```bash
# VS Code integration
ptools shell alias code-project "ptools projects path $1 | xargs code"

# Vim integration
ptools shell alias vim-project "ptools projects path $1 | xargs -I {} sh -c 'cd {} && vim'"
```

### CI/CD Integration

```bash
# Export project information for CI
ptools projects info my-project --format json > project-info.json

# Use in GitHub Actions or similar
PROJECT_PATH=$(ptools projects path my-project)
echo "PROJECT_PATH=$PROJECT_PATH" >> $GITHUB_ENV
```

### Docker Integration

```bash
# Watch and rebuild Docker images
ptools watch --path src/ --command "docker build -t my-app:latest ."

# Sync with Docker containers
ptools rsync watch --path ./ -avz ./ /container/path/
```

## Best Practices

### Project Organization

1. **Use consistent naming**: Follow a naming convention for projects
2. **Add meaningful tags**: Tag projects by technology, status, priority
3. **Keep projects current**: Remove old, unused projects regularly
4. **Document projects**: Add descriptions for complex projects

### Shell Configuration

1. **Test aliases before adding**: Make sure commands work as expected
2. **Use meaningful names**: Alias names should be clear and memorable
3. **Avoid conflicts**: Check existing aliases before adding new ones
4. **Group related aliases**: Use prefixes for related functionality

### Development Workflow

1. **Use version control**: Always work with version-controlled projects
2. **Automate repetitive tasks**: Use watch and automation features
3. **Set up consistent environments**: Use shell variables for configuration
4. **Monitor changes**: Use file watching for continuous feedback

### Security Considerations

1. **Protect sensitive data**: Don't add secrets to shell aliases or projects
2. **Use appropriate permissions**: Ensure project directories have correct permissions
3. **Review shell changes**: Check shell configuration files before using
4. **Clean up regularly**: Remove unused aliases and projects

## Troubleshooting

### Common Issues

1. **Project not found**:
   ```bash
   # Check project exists
   ptools projects list | grep project-name
   
   # Re-add if missing
   ptools projects add project-name /correct/path
   ```

2. **Shell aliases not working**:
   ```bash
   # Check shell configuration
   cat ~/.bashrc | grep alias
   
   # Reload shell configuration
   source ~/.bashrc
   ```

3. **Workspace commands failing**:
   ```bash
   # Check if in Node.js workspace
   ls package.json
   
   # Verify workspace structure
   ptools ws find
   ```

4. **Development tools not found**:
   ```bash
   # Check PTools installation
   ptools dev root
   
   # Reinstall if needed
   ptools dev install
   ```
