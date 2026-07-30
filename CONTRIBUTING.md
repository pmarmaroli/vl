# Contributing to VL

Thank you for your interest in contributing! This guide will help you get started.

---

## Quick Start

### 1. Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/pmarmaroli/vl.git
cd vl
pip install -e ".[dev]"

# Verify installation
vl-minify --help
vl2 --spec

# Run tests
pytest
```

### 2. Make Your Changes

```bash
# Create a branch
git checkout -b feature/your-feature

# Make changes and test
pytest

# Commit with clear message
git commit -m "feat: add support for X"

# Push and create PR
git push origin feature/your-feature
```

---

## What We Need

### High Priority

| Area | Examples |
|------|----------|
| **New v2 macros** | Frequent multi-line patterns worth a macro (each must beat its expansion on a real tokenizer — see docs/vl2-design.md) |
| **Detector coverage** | More syntactic variants of the known patterns, always conservative |
| **Minifier** | JavaScript/TypeScript minification support |
| **Documentation** | Tutorials, examples, video guides |
| **Testing** | Edge cases, real-world code examples, benchmarks |

### Good First Issues

- Propose and benchmark a new v2 macro
- Improve error messages
- Write documentation
- Add test cases
- Fix typos and formatting

**Check [Issues](https://github.com/pmarmaroli/vl/issues) labeled `good first issue`**

---

## Development Guidelines

### Testing

**Before submitting PR:**

```bash
# Run all tests (must pass 100%)
pytest
```

**Adding new features:**
- Write tests first (TDD)
- Ensure 100% test pass rate
- Add integration tests for complex features

### Code Style

**Python:**
- Follow PEP 8
- Use type hints
- Add docstrings to public functions
- Keep functions focused and small

**File Organization:**
- `src/vl/` - Toolkit code (minifier + v2 macros)
- `tests/` - All test files
- `docs/` - Documentation

### Commit Messages

Use conventional commit format:

```
feat: add JavaScript converter
fix: resolve Python syntax validation bug
docs: update installation instructions
test: add edge cases for data pipelines
```

**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

---

## Pull Request Process

1. **Fork the repository** on GitHub
2. **Create a feature branch** from `main`
3. **Make your changes** with clear commits
4. **Run all tests** (must pass 100%)
5. **Update documentation** if needed
6. **Submit PR** with clear description

**PR Description Should Include:**
- What changed and why
- Related issues (e.g., "Fixes #123")
- Testing performed
- Screenshots/examples (if applicable)

**Review Process:**
- Automated tests must pass
- At least one maintainer approval required
- Address feedback promptly
- Maintainer will merge when ready

---

## Reporting Issues

### Bug Reports

Include:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- VL version and OS
- Code sample (minimal reproduction)

### Feature Requests

Include:
- Use case and motivation
- Proposed syntax/behavior
- Example code showing the feature
- Alternatives considered

**Use [GitHub Issues](https://github.com/pmarmaroli/vl/issues) or [Discussions](https://github.com/pmarmaroli/vl/discussions)**

---

## Project Structure

```
vl/
├── src/vl/              # VL (Very Little) toolkit
│   ├── py_minify.py     # Semantic Python minifier (vl-minify)
│   └── v2/              # v2 macros: registry, expander, detector (vl2)
├── tests/
│   ├── unit/            # Unit tests (minifier, macros, detector)
│   ├── benchmarks/      # Real-tokenizer benchmarks
│   └── experiments/     # LLM-in-the-loop experiments
├── docs/                # Design docs and token analysis
└── vscode-extension/    # VS Code extension (@vl chat participant)
```

---

## Community

- **Questions:** [GitHub Discussions](https://github.com/pmarmaroli/vl/discussions)
- **Bug Reports:** [GitHub Issues](https://github.com/pmarmaroli/vl/issues)
- **Feature Requests:** [GitHub Discussions](https://github.com/pmarmaroli/vl/discussions)

---

## Code of Conduct

**We are committed to a welcoming environment for all contributors.**

✅ **Do:**
- Be respectful and inclusive
- Accept constructive feedback
- Focus on what's best for the project
- Show empathy

❌ **Don't:**
- Harass or insult others
- Publish private information
- Engage in unprofessional conduct

**Violations:** Report to project maintainers. All complaints reviewed promptly.

---

## License

By contributing, you agree your contributions will be licensed under the [MIT License](LICENSE.md).

---

## Recognition

Contributors are:
- Listed in project acknowledgments
- Mentioned in release notes
- Credited in relevant documentation

Significant contributors may be invited to the core team.

---

**Questions?** Open an [issue](https://github.com/pmarmaroli/vl/issues) or [discussion](https://github.com/pmarmaroli/vl/discussions). We're here to help!

**Thank you for contributing to VL!** 🚀
