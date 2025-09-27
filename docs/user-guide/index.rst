# User Guide

The User Guide provides comprehensive documentation for all PTools modules and features. Each section covers a specific area of functionality with detailed explanations, examples, and best practices.

```{toctree}
:maxdepth: 2
:caption: User Guide Sections:

core-concepts
ai-integration
file-operations
data-processing
development-tools
configuration
workflow-automation
```

## Overview

PTools is organized into several core modules, each serving a specific purpose:

- **AI Integration**: Chat with language models, manage profiles and conversations
- **File Operations**: Enhanced file system navigation, rsync, and monitoring
- **Data Processing**: Stream-based data transformation and analysis
- **Development Tools**: Project management and development workflows
- **Configuration**: Settings, secrets, and environment management
- **Workflow Automation**: Automated tasks and monitoring

## Getting Started

If you're new to PTools, start with:

1. [Core Concepts](core-concepts.rst) - Understand the fundamental principles
2. [Configuration](configuration.rst) - Set up your environment
3. Choose the module most relevant to your needs

## Module Cross-References

Many PTools modules work together. Here are common integration patterns:

- **AI + Data Processing**: Use LLM responses as input to flow pipelines
- **File Operations + Workflow**: Monitor files and trigger automated actions
- **Development Tools + AI**: Use AI assistance in development workflows
- **Configuration + All Modules**: Centralized settings affect all tools

## Best Practices

Throughout this guide, you'll find best practices for:

- Organizing your configuration and profiles
- Creating efficient data processing pipelines
- Integrating PTools into your existing workflows
- Troubleshooting common issues
