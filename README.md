# VL (Vibe Language)

**Cut Your AI Coding Costs — Automatically**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange.svg)]()
[![Version: 0.2.0-alpha](https://img.shields.io/badge/Version-0.2.0--alpha-blue.svg)]()

🌐 **[Try VL Live Demo](https://vl-demo-wine.vercel.app)** - Interactive Python ↔ VL converter in your browser

---

## What is VL?

**VL is a token-efficiency toolkit designed to reduce AI coding costs.** It ships two strategies:

1. **Semantic Python minification** (`vl.py_minify`) — strips comments, docstrings and blank lines while guaranteeing identical semantics (AST-verified). **Measured ~20–30% real token savings** with a real LLM tokenizer, zero correctness risk, no language spec needed.
2. **VL v2 macros** (`vl.v2`) — single-line, valid-Python calls that stand for multi-line patterns (JSON I/O, group-by aggregation, HTTP+filter). **Measured 56–93% savings per use**; a conservative detector compresses existing Python into macro form, and the compiler expands macros back to dependency-free Python. Combined with minification: **57% measured on a realistic module**. See [docs/vl2-design.md](docs/vl2-design.md).
3. **The VL v1 language** — a compact syntax that compiles to Python, JavaScript, TypeScript, C, and Rust. Its high-level constructs (data pipelines, API idioms) collapse multi-line patterns into single statements.

> ⚠️ **Honest measurement update (June 2026):** earlier savings figures were based on a chars/token estimate. Re-measured with a real BPE tokenizer, line-by-line VL conversion often costs *more* tokens than plain Python, while minification reliably saves 20–30%. Full analysis and methodology: [docs/token-analysis.md](docs/token-analysis.md).

### Two Ways to Use VL

**1. 🔥 VS Code Extension (Alpha Available) - RECOMMENDED**
- Install extension, use `@vl` in VS Code chat
- Automatic Python → VL conversion before sending to AI
- Analytics dashboard tracks your savings
- **Zero learning curve** - just chat normally
- **Currently supports:** Python (JavaScript/TypeScript coming soon)

**2. Direct Compiler (CLI)**
- Use VL syntax directly for maximum token savings
- Python ↔ VL bidirectional conversion (full-module passthrough for exact roundtrip)
- Ideal for AI code generation workflows

---

## Quick Start

### Option 1: VS Code Extension (Alpha)

**Installation:**

1. Download latest [.vsix from Releases](https://github.com/pmarmaroli/vl/releases)
2. VS Code → Extensions (`Ctrl+Shift+X`) → `...` menu → **Install from VSIX...**
3. Reload VS Code
4. Add your Anthropic API key: Command Palette → `VL: Set Anthropic API Key` (stored in VS Code secure storage)

**Usage:**

```
@vl #file:script.py Can you help optimize this?
```

**Features:**
- 🚀 Automatic Python → VL conversion (significant token reduction)
- 🛡️ Python syntax validation before conversion
- 📊 Analytics dashboard (daily/weekly/monthly savings)
- 💾 CSV export of savings history
- ⚙️ Apply Code buttons for one-click implementation
- ⚡ Claude API with prompt caching (90% savings on cached requests)
- ✅ Import alias preservation (`import numpy as np`)
- 🧠 Smart conversion (only converts if saves tokens)

**Language Support:** Python (alpha) • JavaScript/TypeScript (coming soon)

---

### Option 2: Direct Compiler (CLI)

**Installation:**

```bash
git clone https://github.com/pmarmaroli/vl.git
cd vl
pip install -e .

# Verify — the install provides the vl, vl-minify, vl2 and py2vl commands
vl examples/basic/hello.vl
```

**Minify Python for LLM use (recommended — measured 20–30% savings):**

```bash
# Semantics-preserving minification (AST-verified)
vl-minify script.py -o script.min.py

# Measure real token savings on your own files
pip install -e ".[benchmarks]"
python tests/benchmarks/real_token_benchmark.py script.py
```

**VL v2 macros (56–93% savings on covered patterns):**

```bash
# Print the macro spec to include in your LLM prompt (266 tokens, cacheable)
vl2 --spec

# Compress existing Python patterns into macros before sending to an LLM
vl2 -c script.py

# Expand LLM-generated macro code to dependency-free Python
vl2 generated.py -o runnable.py

# Validate every macro against the real tokenizer
python tests/benchmarks/v2_macro_benchmark.py
```

**Convert Python to VL (v1):**

```bash
# Convert existing Python file
py2vl script.py -o script.vl

# Compile back to Python
vl script.vl -o script_output.py
```

**Compile VL to multiple targets:**

```bash
vl program.vl --target python -o output.py
vl program.vl --target javascript -o output.js
vl program.vl --target typescript -o output.ts
```

---

## Why VL?

### The Problem

AI coding assistants consume significant tokens, which impacts costs.

### The Solution

Measured with a real LLM tokenizer (Mistral Tekken, same BPE family as Claude/GPT tokenizers) on this repository's own source code:

| Strategy | Real token savings |
|---|---|
| **Python minification** (`vl.py_minify`) | **26.1% across all 21 `src/vl` files** (up to 58% on heavily documented code) |
| **VL v2 macros** (`vl.v2`) | **56–93% per macro use**, 13-macro registry (spec amortizes after ~8 uses — see [design](docs/vl2-design.md)) |
| VL v1 line-by-line conversion | −36% to +6% (usually *costs* tokens — see [analysis](docs/token-analysis.md)) |
| VL v1 pipelines (`filter`/`groupBy`/`agg`) | Up to 85% on matching patterns |

**Why:** BPE tokenizers already compress idiomatic Python extremely well (`def `, ` return`, indentation ≈ 1 token each), so compact *characters* don't mean fewer *tokens*. Real savings come from removing what the model doesn't need (comments, docstrings, blank lines) and from collapsing multi-line patterns — not from shorter syntax.

---

## Language Examples

### VL Syntax (Compact)

```vl
# Function definition
F:greet|S|S|ret:'Hello, ${i0}!'

# Data pipeline
data:users|filter:age>18|groupBy:country|agg:sum,revenue

# API call with filtering
F:getActive|S|A|ret:api:GET,i0|filter:status=='active'
```

### Equivalent Python (Verbose)

```python
def greet(name: str) -> str:
    return f'Hello, {name}!'

# Data pipeline requires multiple lines
adult_users = [u for u in users if u['age'] > 18]
grouped = {}
for user in adult_users:
    country = user['country']
    if country not in grouped:
        grouped[country] = []
    grouped[country].append(user)
result = {k: sum(u['revenue'] for u in v) for k, v in grouped.items()}

# API call
def get_active(url: str) -> list:
    response = requests.get(url)
    data = response.json()
    return [item for item in data if item['status'] == 'active']
```

**Token reduction: 47-75%**

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Target Compilation** | Compiles to Python, JavaScript, TypeScript, C, Rust |
| **Python ↔ VL Converter** | Full-module passthrough for exact roundtrip (raw + base64-safe) |
| **Parameter Name Preservation** | Original param names roundtrip correctly (`name: str` → `name:S` → `name: str`) |
| **Docstring Preservation** | Docstrings preserved via full-module passthrough |
| **Python Minifier** | AST-verified semantic minification, ~20–30% real token savings (`vl.py_minify`) |
| **Real-Token Benchmark** | Measures with an actual LLM tokenizer (`tests/benchmarks/real_token_benchmark.py`) |
| **VS Code Integration** | Chat participant with analytics dashboard |
| **Syntax Validation** | Prevents corrupted file conversions |
| **Python FFI** | Call any Python library directly (`py:numpy.array([1,2,3])`) |
| **Try/Except/With Support** | Full exception handling and context managers via `py:` passthrough |
| **Prompt Caching** | 90% savings on repeated VL spec requests |

### Supported Python Features

Full conversion support for:
- Classes with methods, inheritance, decorators
- Context managers (`with` statements) via `py:` passthrough
- Exception handling (`try/except/raise`) with preserved indentation
- Control flow (`break`, `continue`) via passthrough
- List comprehensions and dictionary operations
- Type annotations and parameter names
- All control flow (if/else, for, while)
- Compound operators (`+=`, `-=`, etc.)
- Docstrings (preserved via full-module passthrough)

---

## Project Status

**Version:** 0.2.0-alpha  
**Status:** Alpha - VS Code extension available for testing  
**License:** MIT

### What Works

| Component | Status |
|-----------|--------|
| **Core VL Compiler** | 5 target languages (Python, JS, TS, C, Rust) |
| **Python ↔ VL Converter** | Full-module passthrough; roundtrip harness green (repo + immo-gen utils) |
| **VS Code Extension** | `@vl` chat participant (Python only) |
| **Analytics Dashboard** | Persistent storage with CSV export |
| **Benchmark Suites** | Examples 12/12, Robustness 15/15, Strength/Weakness 15/15. Token efficiency re-measured with a real tokenizer: see [docs/token-analysis.md](docs/token-analysis.md) |
| **LLM Validation** | Claude & Gemini: 100% correctness |

### Known Limitations

| Limitation | Details |
|------------|----------|
| **Alpha Software** | APIs may change between versions |
| **Extension Status** | VS Code extension in alpha testing |
| **Production Use** | Use generated Python/JS code, not VL source files directly |

---

## FAQ

**Q: Do I need to learn VL syntax?**  
A: No! The VS Code extension handles everything automatically. Just use `@vl` in chat.

**Q: How much will I save?**  
A: Measured with a real LLM tokenizer, Python minification saves ~20–30% on typical files (more on heavily documented code). For $200/month AI costs, that's roughly $40–60/month. See [docs/token-analysis.md](docs/token-analysis.md) for methodology.

**Q: Is VL a replacement for Python/JavaScript?**  
A: No! VL is an optimization layer. You still write/execute Python/JS. VL just makes AI interactions cheaper.

**Q: Can I use VL in production?**  
A: Use the transparent mode VS Code extension in production. Don't deploy VL source files directly - compile to Python/JS first.

**Q: Will this work with my existing code?**  
A: The Python→VL converter supports full-module passthrough; use `py:__RAW__` (or base64) to preserve semantics on any module.

**Q: How do I get the extension?**  
A: Download from [Releases](https://github.com/pmarmaroli/vl/releases) or package from source.

---

## Roadmap

| Phase | Status | Deliverables |
|-------|--------|-------------|
| **1. Core Language** | ✅ Complete | Multi-target compiler, Python converter, test suite |
| **2. Transparent Mode** | ✅ Alpha | VS Code extension (Python), analytics dashboard, packaging |
| **2. Marketplace** | 🔄 Next | Public VS Code marketplace release |
| **2. Multi-Language Extension** | 📋 Planned | JavaScript/TypeScript support in extension |
| **3. Multi-IDE** | 📋 Planned | Cursor, JetBrains integration, enterprise features |
| **4. Ecosystem** | 🔮 Future | Community growth, marketplace launch |

---

## Contributing

We welcome:
- Bug reports ([Issues](https://github.com/pmarmaroli/vl/issues))
- Feature requests ([Discussions](https://github.com/pmarmaroli/vl/discussions))
- Code contributions (see [CONTRIBUTING.md](CONTRIBUTING.md))

**Running Tests:**

```bash
cd vl
pip install -e ".[dev]"
pytest
```

---

## Links

- [Token Analysis (real-tokenizer measurements)](docs/token-analysis.md)
- [VL v2 Design (tokenizer-aware macros)](docs/vl2-design.md)
- [Language Specification](docs/specification.md)
- [Releases](https://github.com/pmarmaroli/vl/releases)
- [Issues](https://github.com/pmarmaroli/vl/issues)
- [Discussions](https://github.com/pmarmaroli/vl/discussions)

---

## License

MIT License - Copyright © Patrick Marmaroli

See [LICENSE.md](LICENSE.md) for details.

---

**[⭐ Star this repo](https://github.com/pmarmaroli/vl) to follow development!**

