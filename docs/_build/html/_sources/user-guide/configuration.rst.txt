# Configuration

PTools uses a hierarchical configuration system to manage settings, profiles, and user preferences across all modules.

## Configuration Hierarchy

Settings are resolved in this order of priority (highest to lowest):

1. **Command-line options**: `--option value`
2. **Environment variables**: `PTOOLS_OPTION=value`
3. **Configuration files**: JSON/YAML files in config directory
4. **Default values**: Built-in defaults

## Configuration Directory

PTools stores configuration in platform-appropriate locations:

### Location by Platform

- **Linux/macOS**: `~/.config/ptools/`
- **Windows**: `%APPDATA%\ptools\`

### Directory Structure

```
~/.config/ptools/
├── config.json              # Main configuration file
├── keys/                     # Encrypted API keys (managed by keyring)
├── profiles/                 # AI model profiles
│   ├── default.json
│   ├── coding-helper.json
│   └── creative-writer.json
├── chats/                    # Chat history files
│   ├── project-planning.json
│   └── debug-session.json
├── projects/                 # Project definitions
│   └── projects.json
└── logs/                     # Application logs
    └── ptools.log
```

## Main Configuration File

The main configuration file (`config.json`) stores global settings:

```json
{
  "version": "1.0.0",
  "logging": {
    "level": "INFO",
    "file_enabled": true,
    "console_enabled": true
  },
  "defaults": {
    "llm_model": "gemini-2.0-flash",
    "output_format": "text",
    "verbose": false
  },
  "modules": {
    "llm": {
      "default_profile": "default",
      "history_transformer": "pass_through",
      "auto_persist": false
    },
    "flow": {
      "debug_mode": false,
      "output_flavor": "text"
    },
    "fs": {
      "default_max_depth": 5,
      "show_hidden": false
    }
  }
}
```

## Environment Variables

PTools recognizes these environment variables:

### Global Settings
- `PTOOLS_CONFIG_DIR`: Override default configuration directory
- `PTOOLS_DEBUG`: Enable debug mode (`1` or `true`)
- `PTOOLS_NO_COLOR`: Disable colored output (`1` or `true`)
- `PTOOLS_LOG_LEVEL`: Set logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

### API Keys (Alternative to Keyring)
- `OPENAI_API_KEY`: OpenAI API key
- `GOOGLE_API_KEY`: Google AI API key
- `SERPERDEV_API_KEY`: SerperDev API key

### Module-Specific
- `PTOOLS_LLM_DEFAULT_MODEL`: Default AI model to use
- `PTOOLS_FLOW_DEBUG`: Enable flow debug mode
- `PTOOLS_FS_MAX_DEPTH`: Default maximum depth for directory walking

## AI Profiles

AI profiles customize language model behavior for different use cases.

### Profile Structure

Profiles are JSON files with this structure:

```json
{
  "temperature": 0.7,
  "max_tokens": 1024,
  "presence_penalty": 0.0,
  "frequency_penalty": 0.0,
  "system_prompt": "You are a helpful assistant."
}
```

### Profile Parameters

- **temperature** (0.0-2.0): Controls randomness/creativity
  - 0.0: Very focused, deterministic
  - 0.7: Balanced (default)
  - 1.5+: Very creative, unpredictable

- **max_tokens** (1-4096): Maximum response length
  - 512: Short responses
  - 1024: Medium responses (default)
  - 2048+: Long, detailed responses

- **presence_penalty** (-2.0 to 2.0): Encourages new topics
  - Negative: More repetition
  - 0.0: Balanced (default)
  - Positive: More topic diversity

- **frequency_penalty** (-2.0 to 2.0): Reduces repetition
  - Negative: More repetitive
  - 0.0: Balanced (default)  
  - Positive: Less repetitive

- **system_prompt** (string): Sets AI behavior and personality

### Built-in Profiles

PTools includes several built-in profiles:

#### Default Profile
```json
{
  "temperature": 0.7,
  "max_tokens": 1024,
  "presence_penalty": 0.0,
  "frequency_penalty": 0.0,
  "system_prompt": "You are a helpful assistant."
}
```

#### Code Reviewer Profile
```json
{
  "temperature": 0.3,
  "max_tokens": 2000,
  "presence_penalty": 0.0,
  "frequency_penalty": 0.0,
  "system_prompt": "You are an expert code reviewer. Focus on best practices, security, performance, and maintainability. Provide specific, actionable feedback."
}
```

#### Creative Writer Profile
```json
{
  "temperature": 1.2,
  "max_tokens": 2000,
  "presence_penalty": 0.8,
  "frequency_penalty": 0.5,
  "system_prompt": "You are a creative writer. Use vivid language, interesting metaphors, and engaging storytelling techniques."
}
```

### Managing Profiles

```bash
# Create new profile interactively
ptools llm-opts create-profile

# Add profile from file
ptools llm-opts add-profile my-profile profile.json

# List all profiles
ptools llm-opts list-profiles

# Delete profile
ptools llm-opts delete-profile old-profile
```

## Project Configuration

The projects system tracks your development projects:

### Projects File Structure

`~/.config/ptools/projects/projects.json`:

```json
{
  "projects": {
    "ptools": {
      "path": "/home/user/code/ptools",
      "description": "Power tools CLI",
      "tags": ["python", "cli", "tools"],
      "created": "2025-01-01T10:00:00Z",
      "last_accessed": "2025-01-01T15:30:00Z"
    },
    "my-website": {
      "path": "/home/user/code/website",
      "description": "Personal website",
      "tags": ["javascript", "web", "react"],
      "created": "2025-01-01T11:00:00Z",
      "last_accessed": "2025-01-01T14:20:00Z"
    }
  }
}
```

### Managing Projects

```bash
# Add project
ptools projects add my-project /path/to/project

# List projects
ptools projects list

# Remove project
ptools projects remove my-project

# Open project directory
ptools projects open my-project
```

## Security Configuration

### API Key Storage

API keys are stored securely using the system keyring:

- **macOS**: Keychain Access
- **Linux**: Secret Service (GNOME Keyring, KWallet)
- **Windows**: Windows Credential Manager

Keys are never stored in plain text configuration files.

### Encryption

Sensitive data uses encryption:
- AES-256 encryption for local data
- Platform-specific secure storage APIs
- Automatic key rotation where supported

## Advanced Configuration

### Custom Configuration Files

You can create module-specific configuration files:

`~/.config/ptools/llm.json`:
```json
{
  "default_model": "gpt-4",
  "profiles_directory": "/custom/path/profiles",
  "chat_history_retention_days": 30
}
```

### Configuration Validation

PTools validates all configuration files on startup:

- Schema validation using Pydantic models
- Type checking for all values
- Range validation for numeric values
- Path validation for file/directory references

### Configuration Migration

PTools automatically migrates configuration when upgrading:

- Backup old configuration before migration
- Add new default values for new settings
- Remove deprecated settings with warnings
- Preserve user customizations

## Troubleshooting Configuration

### Common Issues

1. **Configuration not found**:
   ```bash
   # Check configuration directory
   echo $HOME/.config/ptools
   
   # Recreate default configuration
   ptools dev install
   ```

2. **Invalid configuration**:
   ```bash
   # Validate configuration
   ptools --debug --help  # Will show config validation errors
   
   # Reset to defaults
   rm ~/.config/ptools/config.json
   ptools --help  # Will recreate defaults
   ```

3. **API key issues**:
   ```bash
   # Check stored keys
   ptools llm-opts list-api-keys
   
   # Re-add keys
   ptools llm-opts set-api-key --service openai
   ```

4. **Permission problems**:
   ```bash
   # Fix permissions
   chmod -R 700 ~/.config/ptools
   ```

### Debug Configuration

Enable debug mode to see configuration loading:

```bash
export PTOOLS_DEBUG=1
ptools --help
```

This will show:
- Configuration file paths being checked
- Values being loaded from each source
- Validation errors and warnings
- Final resolved configuration

### Reset Configuration

To completely reset configuration:

```bash
# Backup current configuration
cp -r ~/.config/ptools ~/.config/ptools.backup

# Remove configuration directory
rm -rf ~/.config/ptools

# Restart ptools to recreate defaults
ptools --help
```
