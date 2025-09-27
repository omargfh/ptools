# Quick Start Guide

This guide will get you up and running with PTools in minutes. We'll cover the most common use cases and commands to help you start being productive immediately.

## First Steps

After [installation](installation.rst), verify everything is working:

```bash
ptools --version
ptools --help
```

## Essential Commands

### Getting Help
PTools provides comprehensive help for all commands:

```bash
# Top-level help
ptools --help

# Help for specific modules
ptools llm --help
ptools fs --help
ptools flow --help
```

### File System Operations

Explore your file system with enhanced tools:

```bash
# Get detailed info about a file or directory
ptools fs info /path/to/file

# Walk directory tree with filtering
ptools fs walkdir --max-depth 2 --regex "\.py$"

# Find files matching patterns
ptools fs walkdir --path . --regex "config.*\.(json|yaml)$"
```

### AI Chat Interface

Start chatting with AI models (requires API keys):

```bash
# Set up your API key first
ptools llm-opts set-api-key --service openai

# Quick one-off question
ptools llm "What is the capital of France?"

# Interactive chat session
ptools llm --interactive

# Use specific model
ptools llm "Explain Python decorators" --model gpt-4
```

### Data Processing with Flow

Process data through pipelines using the flow module:

```bash
# Generate a range and process it
ptools flow range 1 10 | ptools flow map "x * 2" | ptools flow filter "x > 10"

# Process file contents
cat data.txt | ptools flow map "x.upper()" | ptools flow filter "len(x) > 5"

# Work with JSON data
echo '["apple", "banana", "cherry"]' | ptools flow map "x.upper()" --flavor json
```

### JSON Operations

Handle JSON data with built-in tools:

```bash
# Format JSON with custom indentation
echo '{"name":"John","age":30}' | ptools json format --indent 2

# Convert JSON to YAML
echo '{"key": "value"}' | ptools json to-yaml

# Extract specific fields
echo '{"users": [{"name": "Alice"}, {"name": "Bob"}]}' | ptools json format
```

### Project Management

Organize your development projects:

```bash
# Add a new project
ptools projects add my-project /path/to/project

# List all projects
ptools projects list

# Open a project in your editor
ptools projects open my-project
```

## Common Workflows

### 1. AI-Assisted Development

```bash
# Set up your AI environment
ptools llm-opts set-api-key --service openai
ptools llm-opts create-profile  # Create a custom profile

# Use AI for code review
ptools llm "Review this Python function for best practices" --profile code-reviewer

# Get help with debugging
ptools llm --interactive --history debug-session
```

### 2. Data Processing Pipeline

```bash
# Process log files
cat server.log | \
  ptools flow filter "error" | \
  ptools flow map "x.split(' ')[0]" | \
  ptools flow unique | \
  ptools flow --flavor json

# Transform data formats
cat data.csv | \
  ptools flow map "x.split(',')" | \
  ptools flow map "{'name': x[0], 'age': int(x[1])}" | \
  ptools json format --indent 2
```

### 3. File System Monitoring

```bash
# Watch directory for changes and sync
ptools rsync watch --path ./src -avz ./src/ user@server:/backup/

# Monitor file changes
ptools watch --path ./config --command "echo Config changed: {filepath}"
```

### 4. Development Environment Setup

```bash
# Set up shell aliases
ptools shell alias ll "ls -la"
ptools shell x EDITOR "code"

# Manage development tools
ptools dev install  # Reinstall the tool
ptools dev code     # Open in VS Code
```

## Configuration Quick Setup

### AI Models Configuration

1. **OpenAI Setup**:
   ```bash
   ptools llm-opts set-api-key --service openai
   # Enter your API key when prompted
   ```

2. **Google AI Setup**:
   ```bash
   ptools llm-opts set-api-key --service google
   # Enter your Google AI API key
   ```

3. **Create Custom Profiles**:
   ```bash
   ptools llm-opts create-profile
   # Follow the interactive prompts
   ```

### Project Organization

```bash
# Set up your first project
ptools projects add main ~/code/main-project
ptools projects add utils ~/code/utilities

# List and verify
ptools projects list
```

## Tips for New Users

1. **Use Tab Completion**: Most shells support tab completion for PTools commands

2. **Combine with Unix Tools**: PTools works great with pipes and standard Unix utilities:
   ```bash
   ptools fs walkdir | grep "\.py$" | head -10
   ```

3. **JSON Output**: Many commands support `--flavor json` for machine-readable output

4. **Interactive Mode**: Use `--interactive` flags where available for guided experiences

5. **Help is Always Available**: Every command and subcommand has detailed help with examples

## Next Steps

Now that you have the basics, explore these areas:

- [User Guide](user-guide/index.rst): Detailed documentation for each module
- [Tutorials](tutorials/index.rst): Step-by-step guides for common tasks  
- [CLI Reference](cli-reference/index.rst): Complete command reference
- [API Reference](api-reference/index.rst): Developer documentation

## Troubleshooting Quick Fixes

- **Command not found**: Check installation and PATH
- **Permission denied**: Try with `sudo` or check file permissions
- **API errors**: Verify your API keys with `ptools llm-opts list-api-keys`
- **Import errors**: Install optional dependencies as needed
