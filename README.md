# VL (Vibe Language)

**Cut Your AI Coding Costs — Automatically**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange.svg)]()
[![Version: 0.2.0-alpha](https://img.shields.io/badge/Version-0.2.0--alpha-blue.svg)]()

🌐 **[Try VL Live Demo](https://vl-demo-wine.vercel.app)** - Interactive Python ↔ VL converter in your browser

---

## What is VL?

**VL is a token-efficient programming language designed to reduce AI coding costs.** It achieves **significant token reduction** across diverse codebases by using a compact syntax that compiles to Python, JavaScript, TypeScript, C, and Rust.

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

1. Download latest [.vsix from Releases](https://github.com/pmarmaroli/vibe-language/releases)
2. VS Code → Extensions (`Ctrl+Shift+X`) → `...` menu → **Install from VSIX...**
3. Reload VS Code
4. Add Anthropic API key: Settings → `vl.anthropicApiKey`

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
git clone https://github.com/pmarmaroli/vibe-language.git
cd vibe-language

# Set Python path
export PYTHONPATH="$PWD/src"  # Unix/Mac
$env:PYTHONPATH="$PWD\src"    # Windows

# Verify
./vl examples/basic/hello.vl
```

**Convert Python to VL:**

```bash
# Convert existing Python file
python -m vl.py2vl script.py -o script.vl

# Work with LLM on VL version (~47% fewer tokens)

# Compile back to Python
./vl script.vl -o script_output.py
```

**Compile VL to multiple targets:**

```bash
./vl program.vl --target python -o output.py
./vl program.vl --target javascript -o output.js
./vl program.vl --target typescript -o output.ts
```

---

## Why VL?

### The Problem

AI coding assistants consume significant tokens, which impacts costs.

### The Solution

VL's compact syntax reduces tokens significantly:

**Production validation:** 153 real-world files tested (vocametrix-platform, RANCH, xKozmos-signalprocessing)
- 100% success rate
- 127,871 tokens saved
- Zero files made larger (smart conversion)

**Real impact:**
- Measurable cost reduction for AI-powered development
- Scales with team size and codebase complexity
- Proven on production codebases

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
| **VS Code Integration** | Chat participant with analytics dashboard |
| **Syntax Validation** | Prevents corrupted file conversions |
| **Token Estimation** | Calibrated with actual Claude tokenizer (2.58 chars/token) |
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
| **Benchmark Suites** | Examples 12/12, Robustness 15/15, Strength/Weakness 15/15, Token efficiency 13/13 (232 vs 440 tokens → 47.3% savings; 45.1% overall avg) |
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
A: Latest benchmarks show ~47% token reduction. For $200/month AI costs, that's about $94/month saved.

**Q: Is VL a replacement for Python/JavaScript?**  
A: No! VL is an optimization layer. You still write/execute Python/JS. VL just makes AI interactions cheaper.

**Q: Can I use VL in production?**  
A: Use the transparent mode VS Code extension in production. Don't deploy VL source files directly - compile to Python/JS first.

**Q: Will this work with my existing code?**  
A: The Python→VL converter supports full-module passthrough; use `py:__RAW__` (or base64) to preserve semantics on any module.

**Q: How do I get the extension?**  
A: Download from [Releases](https://github.com/pmarmaroli/vibe-language/releases) or package from source.

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
- Bug reports ([Issues](https://github.com/pmarmaroli/vibe-language/issues))
- Feature requests ([Discussions](https://github.com/pmarmaroli/vibe-language/discussions))
- Code contributions (see [CONTRIBUTING.md](CONTRIBUTING.md))

**Running Tests:**

```bash
cd vibe-language
export PYTHONPATH="$PWD/src"
python tests/codegen/test_codegen_all.py
python tests/benchmarks/run_benchmarks.py
```

---

## Links

- [Language Specification](docs/specification.md)
- [Releases](https://github.com/pmarmaroli/vibe-language/releases)
- [Issues](https://github.com/pmarmaroli/vibe-language/issues)
- [Discussions](https://github.com/pmarmaroli/vibe-language/discussions)
- [Artifacts (logs/scratch outputs)](artifacts)
- [Helper scripts](scripts) (one-off maintenance utilities)
- [Legacy root tests/fixtures](tests/manual/root-legacy)

---

## License

MIT License - Copyright © Patrick Marmaroli

See [LICENSE.md](LICENSE.md) for details.

---

**[⭐ Star this repo](https://github.com/pmarmaroli/vibe-language) to follow development!**

