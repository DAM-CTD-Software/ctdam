# Contributing to ctdam

Thank you for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone github.com/DAM-CTD-Software/ctdam.git`
3. Install dependencies: `uv sync`
4. Install pre-commit: `uv run pre-commit install`
5. Create a branch: `git checkout -b feature/my-feature`

## Development Workflow

### Making Changes

1. Make your changes in the appropriate package:
   - `src/ctdam/conv/` - conversion code
   - `src/ctdam/entry/` - cli or gui entrypoints to the software
   - `src/ctdam/parser/` - ctd file parsers
   - `src/ctdam/proc/` - processing functionality
   - `src/ctdam/vis/` - visualization code

2. Write tests:
   - Add tests in `tests/`

3. Run tests:

   ```bash
   uv run pytest
   ```

4. Check code quality:

   ```bash
   uv run ruff check
   ```

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

You can set a commit message template to help in sticking to these rules:

```bash
git config commit.template .gitmessage
```

**Examples:**

```bash
feat(parser): add JSON parser
fix(conv): handle null in conversion
docs(readme): update installation guide
chore(deps): update seabirdscientific to 3.0.0
```

**Breaking Changes:**

```bash
feat(conv): redesign conversion API

BREAKING CHANGE: convert_data() signature changed from
convert_data(data) to convert_data(data, format)
```

### Submitting Changes

1. Push to your fork:

   ```bash
   git push origin feature/my-feature
   ```

2. Create a Pull Request:
   - Use a descriptive title following conventional commits
   - Describe your changes
   - Reference any related issues

3. Wait for review:
   - CI must pass
   - At least one approval required

## Code Style

- Follow PEP 8
- Use type hints
- Maximum line length: 79 characters
- Use Ruff for formatting (auto-fixed by pre-commit)

## Testing

- Write unit tests for new features
- Use pytest fixtures and helper code in conftest for common setup

## Documentation

- Add docstrings to all classes and functions
- Add type hints to all functions

## Questions?

- Open an issue for bugs
- Start a discussion for questions
- Contact maintainers: <emil.michels@iow.de>

## Code of Conduct

Follow the guidelines in CODE_OF_CONDUCT.md
