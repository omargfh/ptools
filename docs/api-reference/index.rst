# API Reference

Complete API documentation for all PTools modules, classes, and functions.

```{toctree}
:maxdepth: 3
:caption: API Documentation:

core-modules
lib-modules
utilities
models
```

## Overview

The PTools API is organized into several layers:

- **Core Modules**: Main command-line interface modules (`ptools.llm`, `ptools.fs`, etc.)
- **Library Modules**: Shared implementation libraries (`ptools.lib.*`)
- **Utilities**: Common utility functions (`ptools.utils.*`)  
- **Models**: Data models and configuration (`ptools.models.*`)

## Module Organization

```
ptools/
├── main.py              # CLI entry point
├── llm.py              # LLM/AI integration
├── fs.py               # File system operations  
├── flow.py             # Data processing
├── json.py             # JSON utilities
├── rsync.py            # Rsync operations
├── watch.py            # File watching
├── dev.py              # Development tools
├── projects.py         # Project management
├── shell.py            # Shell utilities
├── secrets.py          # Secrets management
├── clip.py             # Clipboard operations
├── workspaces.py       # Workspace management
├── lib/                # Shared libraries
│   ├── llm/           # LLM implementations
│   ├── flow/          # Flow processing engine
│   └── node_workspaces/ # Node.js workspace handling
├── utils/              # Utility functions
├── models/             # Data models
└── formats/            # Data format handlers
```

## Import Patterns

### Core Modules
```python
# Import main CLI groups
from ptools import llm, fs, flow, json

# Import specific commands  
from ptools.llm import cli as llm_cli
from ptools.fs import info, walkdir
```

### Library Modules
```python
# LLM library
from ptools.lib.llm.client import ChatClient, OpenAIChatClient
from ptools.lib.llm.session import ChatSession
from ptools.lib.llm.entities import LLMProfile, LLMMessage

# Flow processing
from ptools.lib.flow.runner import FlowRunner
from ptools.lib.flow.values import StreamValue, OutputValue
```

### Utilities
```python
# Common utilities
from ptools.utils.config import ConfigFile
from ptools.utils.print import FormatUtils
from ptools.utils.require import require_library, require_key
```

## Key Classes and Functions

### AI/LLM Integration
- `ChatClient`: Abstract base for AI providers
- `ChatSession`: Manages conversation state  
- `LLMProfile`: Configuration for AI behavior

### Data Processing
- `FlowRunner`: Executes data processing pipelines
- `StreamValue`: Represents items in data streams
- `HistoryTransformer`: Transforms chat history

### Configuration Management
- `ConfigFile`: Handles configuration persistence
- `Projects`: Manages project information
- `DecoratorCompositor`: Composes Click decorators

### File Operations
- File system utilities in `fs.py`
- Rsync integration in `rsync.py`
- File watching in `watch.py`

## Extension Points

PTools is designed to be extensible:

### Adding New Modules
1. Create module with Click CLI group
2. Add to `main.py` imports and command registration
3. Follow existing patterns for consistency

### Custom Data Processors
1. Inherit from appropriate base classes
2. Implement required interface methods
3. Register with factory classes

### Custom AI Providers  
1. Inherit from `ChatClient`
2. Implement provider-specific methods
3. Add to client factory

## Type Hints and Validation

PTools uses modern Python type hints and Pydantic for validation:

```python
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class LLMProfile(BaseModel):
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, gt=0)
    system_prompt: Optional[str] = None
```

## Error Handling

PTools implements consistent error handling patterns:

- Custom exception classes for different error types
- Graceful degradation when optional dependencies are missing  
- User-friendly error messages with suggested solutions
- Proper cleanup of resources and temporary files
