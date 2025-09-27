# Changelog

All notable changes to PTools will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive Sphinx documentation with tutorials and API reference
- Extended user guides for all modules
- Architecture documentation
- Contributing guidelines

## [1.0.0] - 2025-01-01

### Added
- Initial release of PTools
- Core CLI framework with modular design
- AI/LLM integration module (`llm`) with support for OpenAI and Google AI
- File system operations module (`fs`) with enhanced navigation and info
- Data processing flow module (`flow`) with functional programming primitives
- JSON utilities module (`json`) with formatting and conversion
- Enhanced rsync module (`rsync`) with watching capabilities
- File watching module (`watch`) with event-driven automation
- Development tools module (`dev`) for project management
- Projects management module (`projects`) for workspace organization  
- Shell utilities module (`shell`) for configuration and aliases
- Secrets management module (`secrets`) for secure credential storage
- Clipboard integration module (`clip`) for data transfer
- Workspace management module (`workspaces`) for Node.js projects

### Features
- **AI Chat Interface**: Interactive and one-shot AI conversations
- **Profile Management**: Customizable AI behavior profiles
- **Chat History**: Persistent conversation storage and management
- **Stream Processing**: Functional data transformation pipelines
- **File System Navigation**: Advanced file search and information
- **Automatic Sync**: File watching with rsync integration
- **Configuration Management**: Hierarchical settings system
- **Secure Storage**: System keyring integration for API keys
- **Cross-platform Support**: Works on macOS, Linux, and Windows
- **Extensible Architecture**: Modular design for easy expansion

### Dependencies
- click>=8.1
- watchdog>=3.0
- keyring>=25.6.0
- pycryptodome>=3.14.0
- pydantic>=2.10
- lark>=1.1
- humanize>=4.8.0

[Unreleased]: https://github.com/omargfh/ptools/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/omargfh/ptools/releases/tag/v1.0.0
