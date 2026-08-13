# Contributing to Tech News AI Agent

Thank you for your interest in contributing! Please follow these guidelines to help keep the project maintainable.

## How to Contribute

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes** and verify they work by running the test suite:
   ```bash
   python3 test_agent.py
   ```
3. **Commit** with a clear, descriptive message:
   ```bash
   git commit -m "Add: RSS feed for TechRadar"
   ```
4. **Push** the branch and open a **Pull Request** against the `main` branch.

## Coding Standards

- Python 3.10+ — avoid syntax from newer versions.
- Follow **PEP 8** (4-space indentation, meaningful names).
- Keep each module focused: collection, summarization, formatting, delivery, and scheduling are separate files for a reason.
- All user-facing text in the codebase should remain bilingual-friendly where possible.

## Configuration Changes

- New configuration keys must be documented in `README.md` and added to `config.example.json` with a sensible default.
- Never commit real API keys, bot tokens, or chat IDs. Use `config.example.json` as the public template.

## Bug Reports

When reporting a bug, please include:

- The command you ran (e.g., `python3 main.py --once`).
- Relevant log output from the terminal.
- The contents of your `config.json` with secrets removed.

## Feature Requests

Open an issue describing the feature, the problem it solves, and how you envision it working. Discussion is welcome before any implementation.
