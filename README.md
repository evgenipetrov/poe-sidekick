# POE Sidekick

[![Release](https://img.shields.io/github/v/release/evgenipetrov/poe-sidekick)](https://img.shields.io/github/v/release/evgenipetrov/poe-sidekick)
[![Build status](https://img.shields.io/github/actions/workflow/status/evgenipetrov/poe-sidekick/main.yml?branch=main)](https://github.com/evgenipetrov/poe-sidekick/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/evgenipetrov/poe-sidekick/branch/main/graph/badge.svg)](https://codecov.io/gh/evgenipetrov/poe-sidekick)
[![Commit activity](https://img.shields.io/github/commit-activity/m/evgenipetrov/poe-sidekick)](https://img.shields.io/github/commit-activity/m/evgenipetrov/poe-sidekick)
[![License](https://img.shields.io/github/license/evgenipetrov/poe-sidekick)](https://img.shields.io/github/license/evgenipetrov/poe-sidekick)

## Project Overview

POE Sidekick is an advanced assistant application for Path of Exile 2, designed to enhance gameplay through intelligent automation. Using an event-driven architecture with continuous screen analysis, it provides a modular and extensible system for game automation while maintaining strict compliance with game policies.

### Key Features

- Event-driven screenshot analysis stream
- Independent, self-contained automation modules
- Coordinated workflows for complex operations
- Service-based hardware interaction layer

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Poetry for dependency management
- Path of Exile 2 installed

### Installation

```bash
# Clone the repository
git clone https://github.com/evgenipetrov/poe-sidekick.git
cd poe-sidekick

# Install dependencies
make install
```

## Architecture

### Core Components

#### Screenshot Stream

- Continuous game state monitoring
- Real-time frame distribution
- RxPY-based event system
- Efficient resource management

#### Independent Modules

- Self-contained functional units
- Autonomous state tracking
- Independent decision making
- Examples: Inventory, Stash, Trade, Loot

#### Utility Services

- Vision analysis service
- Keyboard interaction service
- Mouse control service
- Hardware abstraction layer

#### Workflow Orchestration

- Complex operation coordination
- Multi-module workflows
- Error handling and recovery
- Resource cleanup management

### Design Principles

1. **Module Independence**

   - Each module is fully self-contained
   - Modules handle their own state
   - No cross-module dependencies

2. **Event-Driven Architecture**

   - Screenshot stream as primary event source
   - Reactive processing model
   - Efficient resource usage

3. **Workflow Coordination**
   - Complex operations orchestrated through workflows
   - Clear state transitions
   - Coordinated module activation

## Development

### Setup Development Environment

1. Install Python 3.8+
2. Install Poetry
3. Clone the repository
4. Run `make install` to set up the development environment

### Development Rules

#### Code Organization

- Keep the codebase simple and maintainable
- Reuse code through proper abstraction
- Follow the plugin architecture for new features
- Maintain clear separation of concerns

#### Best Practices

- Write comprehensive tests for new features
- Document code using docstrings
- Follow type hints and use mypy
- Keep functions small and focused

#### Code Quality

- Use pre-commit hooks for code quality
- Maintain high test coverage
- Follow PEP 8 style guidelines
- Use meaningful variable and function names

### Running Tests

```bash
# Run all tests
make test

# Run type checking
make type-check

# Run linting
make lint
```

## Technical Details

### Dependencies

- Python 3.8+
- Poetry for dependency management
- pytest for testing
- mypy for type checking
- MkDocs for documentation

### Project Structure

```
poe_sidekick/
├── core/           # Screenshot stream and workflow base
├── modules/        # Self-contained automation modules
├── services/       # Hardware interaction services
├── workflows/      # Complex operation coordination
└── interfaces/     # User interface implementations
```

## Project Status

- Current Version: 0.0.1
- Early development stage
- Active development ongoing

## Links

- [Documentation](https://evgenipetrov.github.io/poe-sidekick/)
- [GitHub Repository](https://github.com/evgenipetrov/poe-sidekick/)

## License

This project is licensed under the terms of the MIT license. See [LICENSE](LICENSE) for more details.

---

Repository initiated with [fpgmaas/cookiecutter-poetry](https://github.com/fpgmaas/cookiecutter-poetry).
