# Contributing to VL

Thank you for your interest in contributing! This guide will help you get started.

---

## Quick Start

### 1. Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/pmarmaroli/vl.git
cd vl
export PYTHONPATH="$PWD/src"  # Unix/Mac
$env:PYTHONPATH="$PWD\src"    # Windows

# Verify installation
./vl examples/basic/hello.vl

# Run tests
python tests/codegen/test_codegen_all.py
python tests/benchmarks/run_benchmarks.py
```

### 2. Make Your Changes

```bash
# Create a branch
git checkout -b feature/your-feature

# Make changes and test
python tests/codegen/test_codegen_all.py

# Commit with clear message
git commit -m "feat: add support for X"

# Push and create PR
git push origin feature/your-feature
```

---

## What We Need

**Note:** We're currently focusing contributions on the **core VL compiler**. The VS Code extension is in private alpha and will be open-sourced before public release.

### High Priority

| Area | Examples |
|------|----------|
| **Converters** | JavaScript ↔ VL, TypeScript ↔ VL bidirectional conversion |
| **Compiler** | JS/TS code generator improvements, optimization passes |
| **Language Features** | New VL syntax patterns, domain-specific constructs |
| **Documentation** | Tutorials, examples, video guides |
| **Testing** | Edge cases, real-world code examples, benchmarks |

### Good First Issues

- Add new VL code examples
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
python tests/codegen/test_codegen_all.py
python tests/integration/test_realworld_py2vl.py
python tests/benchmarks/run_benchmarks.py
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

**Example:**
```python
def compile_to_python(ast: ASTNode) -> str:
    """Compile VL AST to Python source code.
    
    Args:
        ast: The VL abstract syntax tree
        
    Returns:
        Generated Python source code
    """
    # Implementation
    pass
```

**File Organization:**
- `src/vl/` - Core compiler code
- `tests/` - All test files
- `examples/` - VL code examples
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
├── src/vl/              # Core compiler
│   ├── lexer.py         # Tokenizer
│   ├── parser.py        # AST generator
│   ├── compiler.py      # Main compiler
│   ├── py2vl.py         # Python → VL converter
│   └── codegen/         # Code generators (5 targets)
├── tests/               # Test suite
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   ├── codegen/         # Code generation tests
│   └── benchmarks/      # Performance benchmarks
├── examples/            # VL code examples
├── docs/                # Documentation
└── vl.bat / vl          # CLI wrappers
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
