# Main Command

```{click} ptools.main:cli
:prog: ptools
:nested: full
```

## Usage

The main `ptools` command serves as the entry point for all PTools functionality.

```bash
ptools [OPTIONS] COMMAND [ARGS]...
```

## Global Options

- `--version`: Show the version and exit
- `--help`: Show help message and exit

## Available Commands

The main command provides access to all PTools modules:

### Core Modules
- `llm` - AI/LLM integration and chat interface
- `llm-opts` - AI configuration and profile management
- `fs` - File system operations and utilities
- `flow` - Data processing and transformation pipelines
- `json` - JSON parsing, formatting, and conversion

### System Operations  
- `rsync` - Enhanced rsync operations with watching
- `watch` - File system monitoring and automated actions
- `clip` - Clipboard integration for data transfer

### Development Tools
- `dev` - Development environment utilities
- `projects` - Project management and organization  
- `shell` - Shell configuration and aliases
- `ws` - Workspace management (workspaces)

### Configuration
- `secrets` - Secure secrets and credential management

## Examples

### Getting Help
```bash
# Show all available commands
ptools --help

# Get help for specific module
ptools llm --help

# Get help for specific command
ptools llm chat --help
```

### Version Information
```bash
# Show version
ptools --version
```

### Module Access Patterns
```bash
# Direct module access
ptools llm "Hello, AI!"
ptools fs info /path/to/file
ptools flow map "x.upper()"

# Chain commands using pipes
ptools fs walkdir | ptools flow filter "'.py' in x"
echo "data" | ptools flow map "x.upper()" | ptools clip copy
```

## Environment Variables

The main command respects these environment variables:

- `PTOOLS_DEBUG`: Enable debug mode for all operations
- `PTOOLS_CONFIG_DIR`: Override the default configuration directory
- `PTOOLS_NO_COLOR`: Disable colored output in all modules

## Configuration

The main command initializes the global PTools configuration system, which:

- Creates configuration directories on first run
- Loads default settings and profiles  
- Initializes secure credential storage
- Sets up logging and error handling

Configuration files are stored in:
- **Linux/macOS**: `~/.config/ptools/`
- **Windows**: `%APPDATA%\ptools\`
