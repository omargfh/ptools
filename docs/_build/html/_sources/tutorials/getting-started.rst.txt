# Getting Started Tutorial

This tutorial walks you through your first steps with PTools, from installation verification to running your first commands.

## Prerequisites

- PTools installed on your system
- Terminal or command prompt access
- Basic familiarity with command-line interfaces

## Step 1: Verify Installation

First, let's make sure PTools is properly installed:

```bash
$ ptools --version
ptools, version 1.0.0

$ ptools --help
Usage: ptools [OPTIONS] COMMAND [ARGS]...

  power tools command line interface.

Options:
  --version   Show the version and exit.
  --help      Show this message and exit.

Commands:
  clip      Clipboard operations
  dev       developer options for power tools.
  flow      Pythonic FP-flavored workflow engine.
  fs        Filesystem manipulation tools.
  json      JSON manipulation tools.
  llm       Interact with a chat interface.
  llm-opts  AI related commands.
  projects  Project management commands.
  rsync     rsync power tools.
  secrets   Secrets management commands.
  shell     Shell commands for ptools.
  watch     Watch for file changes and execute commands.
  ws        Node.js workspace management tools.
```

If you see output similar to this, PTools is correctly installed!

## Step 2: Explore File System Operations

Let's start with some basic file system operations:

```bash
# Get information about the current directory
$ ptools fs info .
Path: .
Type: Directory
Size: 4.0 KB
Modified: 2025-01-01 10:30:45
Permissions: drwxr-xr-x
Owner: username

# List files in current directory with pattern matching
$ ptools fs walkdir --max-depth 1
./README.md
./src/
./docs/
./pyproject.toml

# Find Python files recursively
$ ptools fs walkdir --regex "\.py$"
./src/ptools/__init__.py
./src/ptools/main.py
./src/ptools/llm.py
...
```

**Tip:** Use `--help` with any command to see all available options:
```bash
$ ptools fs --help
$ ptools fs info --help
```

## Step 3: Basic Data Processing

Now let's try the flow module for data processing:

```bash
# Generate a sequence of numbers
$ ptools flow range 1 6
1
2
3
4
5

# Transform the numbers
$ ptools flow range 1 6 | ptools flow map "x * 2"
2
4
6
8
10

# Filter and format
$ ptools flow range 1 10 | ptools flow filter "x % 2 == 0" | ptools flow map "f'Even number: {x}'"
Even number: 2
Even number: 4
Even number: 6
Even number: 8
```

**Tip:** The `x` variable in expressions refers to the current item being processed.

## Step 4: JSON Processing

Work with JSON data:

```bash
# Format JSON nicely
$ echo '{"name":"John","age":30,"city":"New York"}' | ptools json format --indent 2
{
  "name": "John",
  "age": 30,
  "city": "New York"
}

# Convert JSON to YAML
$ echo '{"name":"John","age":30}' | ptools json to-yaml
name: John
age: 30
```

## Step 5: Set Up AI Integration (Optional)

If you want to try the AI features, you'll need to set up API keys:

```bash
# Set up OpenAI API key (you'll be prompted to enter it securely)
$ ptools llm-opts set-api-key --service openai
Enter API key for openai: [key will be hidden]
Set API key for openai in config file.

# Test AI interaction
$ ptools llm "Hello! What's 2 + 2?"
Hello! 2 + 2 equals 4. Is there anything else you'd like to know?

# Try interactive mode
$ ptools llm --interactive
> Hello there!
Hello! How can I help you today?
> /exit
```

**Note:** You can skip this step if you don't have API keys. All other PTools features work without AI integration.

## Step 6: Combining Commands

One of PTools' strengths is combining different modules:

```bash
# Find Python files and get their info
$ ptools fs walkdir --regex "\.py$" | head -3 | xargs -I {} ptools fs info "{}"

# Process file names
$ ptools fs walkdir --regex "\.md$" | ptools flow map "x.split('/')[-1]" | ptools flow map "x.replace('.md', '')"

# Create JSON from file listing
$ ptools fs walkdir --files | ptools flow map "{'file': x, 'extension': x.split('.')[-1] if '.' in x else 'none'}" --flavor json
```

## Step 7: Development Tools

Explore the development utilities:

```bash
# Get project root directory
$ ptools dev root
/path/to/ptools

# Add a project to your project list
$ ptools projects add my-project /path/to/my/project
Added project 'my-project' at '/path/to/my/project'

# List projects
$ ptools projects list
Projects:
  my-project: /path/to/my/project
```

## Step 8: Configuration and Profiles

Set up some basic configuration:

```bash
# Check where your configuration is stored
$ ptools dev root  # This shows the tool's root, config is in ~/.config/ptools/

# List available AI models (if you set up API keys)
$ ptools llm --help  # Look for model choices in the help text

# Create a simple AI profile for coding help
$ ptools llm-opts create-profile
Enter profile name: coding-helper
Enter temperature: 0.3
Enter max tokens: 2000
Enter presence penalty: 0.0
Enter frequency penalty: 0.0
Enter system prompt: You are a helpful programming assistant. Provide clear, concise code examples and explanations.
Created profile "coding-helper".
```

## Common Workflows

### Workflow 1: File Analysis
```bash
# Find large files in a directory
$ ptools fs walkdir --files | head -20 | xargs ls -la | sort -k5 -nr | head -5

# Analyze file extensions
$ ptools fs walkdir --files | ptools flow map "x.split('.')[-1].lower() if '.' in x else 'no-ext'" | ptools flow group "x" --flavor json
```

### Workflow 2: Data Transformation
```bash
# Process CSV-like data
$ echo -e "John,25,Engineer\nJane,30,Designer\nBob,35,Manager" | ptools flow map "x.split(',')" | ptools flow map "{'name': x[0], 'age': int(x[1]), 'role': x[2]}" --flavor json
```

### Workflow 3: AI-Assisted Development (if API keys configured)
```bash
# Get help with a coding problem
$ ptools llm "How do I reverse a list in Python?" --profile coding-helper

# Interactive debugging session
$ ptools llm --interactive --profile coding-helper --history debug-session
```

## Troubleshooting

### Command Not Found
If you get "command not found" errors:
```bash
# Check if ptools is in your PATH
$ which ptools

# If not found, try reinstalling or check your Python installation
$ pip install -e .
```

### Permission Errors
If you get permission errors:
```bash
# Check file permissions
$ ptools fs info /path/to/file

# Use appropriate permissions or run with sudo if needed
```

### API Key Issues (AI features)
If AI commands fail:
```bash
# Check stored API keys
$ ptools llm-opts list-api-keys

# Re-set your API key if needed
$ ptools llm-opts set-api-key --service openai
```

## What's Next?

Now that you have the basics down, you can:

1. **Explore specific modules**: Try the [AI Workflows](ai-workflows.rst) tutorial
2. **Learn data processing**: Work through [Data Processing Pipelines](data-processing-pipelines.rst)
3. **Integrate into your workflow**: See [Development Workflows](development-workflows.rst)
4. **Read the User Guide**: Get detailed information in the [User Guide](../user-guide/index.rst)

## Key Takeaways

- PTools uses a modular design: `ptools <module> <command>`
- Most commands work with pipes and standard Unix conventions
- The `--help` flag provides detailed information for any command
- Commands can be combined to create powerful workflows
- AI features are optional and require API keys
- Flow processing uses `x` to refer to the current item

Congratulations! You've completed your first PTools tutorial. You now have the foundation to explore the more advanced features and integrate PTools into your daily workflow.
