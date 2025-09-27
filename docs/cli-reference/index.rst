# CLI Reference

Complete command-line interface reference for all PTools commands and options.

```{toctree}
:maxdepth: 2
:caption: CLI Commands:

main
llm
fs
flow
rsync
watch
dev
projects
shell
secrets
json
clip
workspaces
```

## Quick Reference

### Main Command

```bash
ptools [OPTIONS] COMMAND [ARGS]...
```

**Global Options:**
- `--version`: Show version and exit
- `--help`: Show help message and exit

### Command Structure

All PTools commands follow a consistent structure:

```
ptools <module> <command> [options] [arguments]
```

Examples:
```bash
ptools llm chat "Hello there"
ptools fs info /path/to/file  
ptools flow map "x.upper()"
```

## Common Patterns

### Help System

Every command provides comprehensive help:

```bash
ptools --help                    # Top-level help
ptools llm --help               # Module help
ptools llm chat --help          # Command help
```

### Input/Output Options

Many commands support these patterns:

- `--input FILE`: Read from file instead of stdin
- `--output FILE`: Write to file instead of stdout  
- `--flavor FORMAT`: Output format (json, yaml, text)
- `--verbose/-v`: Verbose output
- `--quiet/-q`: Suppress non-essential output

### Configuration Options

- `--config FILE`: Use specific configuration file
- `--profile NAME`: Use named profile (where applicable)
- `--debug`: Enable debug output

## Command Categories

### AI and Language Models
- `ptools llm` - Chat with AI models
- `ptools llm-opts` - Manage AI settings and profiles

### File System Operations
- `ptools fs` - File system utilities
- `ptools rsync` - Enhanced rsync operations  
- `ptools watch` - File monitoring
- `ptools clip` - Clipboard operations

### Data Processing
- `ptools flow` - Stream data processing
- `ptools json` - JSON utilities

### Development Tools
- `ptools dev` - Development utilities
- `ptools projects` - Project management
- `ptools shell` - Shell configuration
- `ptools ws` - Workspace management

### System Integration
- `ptools secrets` - Secrets management

## Exit Codes

PTools uses standard exit codes:

- `0`: Success
- `1`: General error
- `2`: Command line usage error
- `130`: Interrupted by user (Ctrl+C)

## Environment Variables

PTools respects these environment variables:

- `PTOOLS_CONFIG_DIR`: Override default config directory
- `PTOOLS_DEBUG`: Enable debug mode (set to any value)
- `PTOOLS_NO_COLOR`: Disable colored output
- `OPENAI_API_KEY`: OpenAI API key (alternative to keyring storage)
- `GOOGLE_API_KEY`: Google AI API key (alternative to keyring storage)

## Shell Integration

### Bash/Zsh Completion

Enable tab completion by adding to your shell configuration:

```bash
# Add to ~/.bashrc or ~/.zshrc
eval "$(_PTOOLS_COMPLETE=bash_source ptools)"  # Bash
eval "$(_PTOOLS_COMPLETE=zsh_source ptools)"   # Zsh
```

### Aliases and Functions

Common aliases you might want to set up:

```bash
# Short aliases
alias pt="ptools"
alias ptllm="ptools llm"
alias ptfs="ptools fs"
alias ptflow="ptools flow"

# Useful functions
ptfind() { ptools fs walkdir --regex "$1"; }
ptai() { ptools llm "$@" --interactive; }
```
