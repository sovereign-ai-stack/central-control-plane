# Contributing to Sovereign AI Control Plane

Thank you for investing your time in contributing to the Sovereign AI ecosystem!

This project is dedicated to providing high-performance, private, air-gapped enterprise AI infrastructure. We welcome bug reports, feature enhancements, documentation improvements, and architectural optimizations.

## Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork locally**:
   ```bash
   git clone https://github.com/your-username/central-control-plane.git
   cd central-control-plane
   ```
3. **Create a topic branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Environment

The Control Plane relies on Docker Compose and Python 3.10+.

1. Install local development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest ruff mypy
   ```
2. Set up local testing configuration:
   ```bash
   cp .env.example .env
   ```
3. Start the supporting services:
   ```bash
   docker compose up -d postgres redis weaviate
   ```

## Testing & Quality Assurance

Before submitting a Pull Request, ensure that all automated tests and linters pass:

```bash
# Run unit and integration tests
pytest

# Check code formatting and linting
ruff check .
```

## Pull Request Guidelines

- Ensure your branch is rebased onto the latest `main`.
- Write clear, descriptive commit messages conforming to conventional commits (e.g., `feat: add hybrid search to weaviate adapter`, `fix: handle edge case in rate limiter`).
- Update documentation and environment variables in `.env.example` if your changes introduce new parameters.
- Provide a concise description of what the PR accomplishes and reference any related issues.

## Reporting Bugs

Please open an issue on GitHub with:
- A clear, descriptive title.
- Steps to reproduce the behavior.
- Expected behavior vs. actual behavior.
- Relevant log output (with API keys and secrets redacted).
