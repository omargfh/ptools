# LLM Commands

```{click} ptools.llm:cli
:prog: ptools llm
:nested: full
```

## Usage

The `llm` module provides AI/LLM integration with support for multiple providers.

```bash
ptools llm [OPTIONS] [MESSAGE]...
```

## Options

- `--model`, `-m`: Language model to use (default: gemini-2.0-flash)
- `--history-transformer`, `-t`: History transformer to use (default: pass_through)
- `--history`, `-h`: Name of the history file to use
- `--profile`, `-p`: Name of the profile to use (default: default)
- `--interactive`, `-i` / `--no-interactive`, `-I`: Use chat interface (default: False)
- `--persist`, `-s` / `--no-persist`, `-S`: Persist chat file to disk (default: False)

## Available Models

- **OpenAI Models**: gpt-3.5-turbo, gpt-4, gpt-4-turbo
- **Google Models**: gemini-2.0-flash, gemini-pro

## Examples

### Basic Usage
```bash
# Simple question
ptools llm "What is the capital of France?"

# Use specific model
ptools llm "Explain Python decorators" --model gpt-4

# Interactive chat
ptools llm --interactive
```

### Advanced Usage
```bash
# Use custom profile
ptools llm "Review this code" --profile code-reviewer

# Persistent chat session
ptools llm --interactive --history project-planning --persist

# Combine with other commands
echo "def hello(): print('world')" | ptools llm "Improve this Python function"
```

---

# LLM Options Commands

```{click} ptools.llm:opts
:prog: ptools llm-opts
:nested: full
```

## Usage

The `llm-opts` module manages AI configuration, profiles, and API keys.

```bash
ptools llm-opts COMMAND [OPTIONS]
```

## Commands

### set-api-key
Set API key for a service.

```bash
ptools llm-opts set-api-key --service SERVICE [KEY]
```

**Options:**
- `--service`, `-s`: Service to set API key for (openai, google, serperdev)

### list-api-keys
List all stored API keys.

```bash
ptools llm-opts list-api-keys
```

### add-profile
Add a new LLM profile from file.

```bash
ptools llm-opts add-profile NAME FILE [OPTIONS]
```

**Options:**
- `--copy`, `-c`: Copy file to config directory instead of linking

### create-profile
Create a new LLM profile interactively.

```bash
ptools llm-opts create-profile
```

### list-profiles
List all LLM profiles.

```bash
ptools llm-opts list-profiles
```

### delete-profile
Delete an LLM profile.

```bash
ptools llm-opts delete-profile NAME
```

### list-chats
List all chat files.

```bash
ptools llm-opts list-chats
```

### prune-chats
Delete all chat files.

```bash
ptools llm-opts prune-chats
```

## Examples

### API Key Management
```bash
# Set OpenAI API key
ptools llm-opts set-api-key --service openai

# List configured keys
ptools llm-opts list-api-keys
```

### Profile Management
```bash
# Create interactive profile
ptools llm-opts create-profile

# Add profile from file
ptools llm-opts add-profile code-reviewer ./profiles/code-review.json

# List all profiles
ptools llm-opts list-profiles
```

### Chat Management
```bash
# List saved chats
ptools llm-opts list-chats

# Clean up old chats
ptools llm-opts prune-chats
```
