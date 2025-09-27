Introduction
============

**PTools** (Power Tools) is a comprehensive command-line toolkit designed to enhance productivity for developers, system administrators, and power users. Built with Python and leveraging the Click framework, PTools provides a unified interface for a wide variety of common and specialized tasks.

Philosophy
----------

PTools follows a modular, Unix-philosophy approach where each tool does one thing well, but tools can be composed together to create powerful workflows. The toolkit is designed around several core principles:

- **Modularity**: Each functionality is a separate module that can be used independently
- **Composability**: Tools can be chained together using pipes and standard Unix conventions
- **Extensibility**: Easy to add new modules and extend existing functionality
- **User-Friendly**: Consistent interface with helpful error messages and documentation
- **Modern**: Integration with AI services, modern data formats, and cloud services

Core Capabilities
-----------------

File System & Data Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Advanced file system navigation and manipulation (``fs`` module)
- Intelligent rsync operations with watching capabilities (``rsync`` module)  
- JSON and YAML processing with format conversion (``json`` module)
- Clipboard integration for seamless data transfer (``clip`` module)

AI & Language Models
~~~~~~~~~~~~~~~~~~~
- Interactive chat interfaces with OpenAI and Google AI models (``llm`` module)
- Profile-based AI configurations for different use cases
- Chat history management and persistence
- API key management with secure storage

Development Tools
~~~~~~~~~~~~~~~~~
- Project management and workspace organization (``projects`` module)
- Development environment utilities (``dev`` module)
- Shell configuration and alias management (``shell`` module)
- File watching and automated synchronization (``watch`` module)

Data Processing & Workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Flow-based data processing with functional programming primitives (``flow`` module)
- Stream processing capabilities for handling large datasets
- Expression evaluation with rich built-in functions
- Support for complex data transformations

Configuration & Security
~~~~~~~~~~~~~~~~~~~~~~~~
- Centralized configuration management
- Secure secrets storage using system keyring
- Environment variable management
- Cross-platform compatibility

Architecture Overview
---------------------

PTools is structured as a collection of modules, each providing specific functionality:

.. code-block:: text

   ptools/
   ├── main.py          # Main CLI entry point
   ├── llm.py          # AI/LLM integration
   ├── fs.py           # File system operations
   ├── flow.py         # Data processing workflows
   ├── rsync.py        # Enhanced rsync operations
   ├── json.py         # JSON/data format utilities
   ├── projects.py     # Project management
   ├── dev.py          # Development tools
   ├── shell.py        # Shell utilities
   ├── watch.py        # File watching
   ├── secrets.py      # Secrets management
   ├── clip.py         # Clipboard operations
   ├── workspaces.py   # Workspace management
   └── lib/            # Shared libraries
       ├── llm/        # LLM-specific implementations
       ├── flow/       # Flow processing engine
       └── node_workspaces/ # Node.js workspace handling

Each module is self-contained and provides its own CLI commands, but they share common utilities and can interact with each other when needed.

Design Patterns
---------------

Decorator-Based Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
PTools uses a sophisticated decorator system for handling common CLI patterns like input validation, configuration loading, and error handling:

.. code-block:: python

   @click.command()
   @require.library('openai', prompt_install=True)
   @require.key(['OPENAI_API_KEY'], stores=[os.environ, key_store])
   def some_command():
       pass

Modular CLI Structure
~~~~~~~~~~~~~~~~~~~~
Each module provides its own CLI group that gets composed into the main application:

.. code-block:: python

   # In main.py
   cli.add_command(llm.cli, name="llm")
   cli.add_command(flow.cli, name="flow")
   # etc.

Stream Processing
~~~~~~~~~~~~~~~~
The flow module implements a stream processing paradigm for handling data transformations:

.. code-block:: bash

   # Process data through a pipeline
   ptools flow map "x.upper()" | ptools flow filter "len(x) > 5"

This introduction provides the foundation for understanding how PTools works and how to use it effectively. The following sections will dive deeper into installation, configuration, and usage patterns.
