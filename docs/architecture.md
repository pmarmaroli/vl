# VL Architecture Overview

## High-Level Flow

```
┌─────────────┐
│   VS Code   │  User: @vl #file:script.py optimize this
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  VL Chat Handler    │  • Extract Python code
│  (@vl participant)  │  • Convert to VL
└──────┬──────────────┘  • Calculate savings
       │
       ▼
┌─────────────────────┐
│   VL Converter      │  Smart Conversion:
│   (py_to_vl.py)     │  • Only if saves tokens
└──────┬──────────────┘  • Preserve imports
       │                  • Validate syntax
       ▼
┌─────────────────────┐
│   Claude API        │  Send VL code
│  (with caching)     │  Get response
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Show Results      │  • AI response
│   + Analytics       │  • Token savings
└─────────────────────┘
```

---

## Token Savings Example

**Before VL (Python):**
```python
def calculate_total(items):
    total = 0
    for item in items:
        if item['price'] > 0:
            total += item['price']
    return total
```
→ **91 tokens**

**After VL (Compressed):**
```vl
F:calculate_total|A|I|
t=0|
for:x,i0|
if:x.price>0|t+=x.price|
ret:t
```
→ **48 tokens**

**Savings:** 43 tokens (same functionality, half the size)

---

## Component Structure

```
vibe-vscode/
│
├── Extension Core
│   └── extension.ts
│       • Registers @vl participant
│       • Initializes components
│
├── Chat Integration
│   └── chatParticipant.ts
│       • Handles @vl commands
│       • Extracts file context
│       • Orchestrates conversion
│       • Returns AI response
│
├── VL Converter
│   └── vlConverter.ts
│       • Spawns Python subprocess
│       • Calls py2vl.py
│       • Smart conversion logic
│       • Import preservation
│
├── Claude API
│   └── claudeClient.ts
│       • API communication
│       • Prompt caching
│       • Cache management
│
├── Analytics
│   ├── manager.ts      # Dashboard & reporting
│   └── storage.ts      # Persistent data
│
└── Bundled Compiler (Portable)
    └── vl-compiler/src/vl/
        ├── py2vl.py           # CLI entry
        ├── py_to_vl.py        # Core converter
        │   • Smart conversion
        │   • Import detection
        │   • Token optimization
        └── compiler.py        # VL→Python
```

---

## Key Innovation: Smart Conversion

The converter only uses VL if it actually saves tokens:

```python
def convert_python_to_vl(python_code: str) -> str:
    vl_code = converter.convert(python_code)
    
    # Compare token counts
    original_tokens = len(python_code) / 2.58
    vl_tokens = len(vl_code) / 2.58
    
    # Smart decision
    if vl_tokens >= original_tokens:
        return python_code  # Keep original
    return vl_code          # Use VL
```

**Result:** Zero files made larger across 153 production files tested

---

## Import Alias Preservation

**Problem:** Standard conversion loses import aliases:
```python
import numpy as np
data = np.array([1, 2, 3])  # ❌ Breaks: np not defined
```

**Solution:** Detect and preserve aliases:
```python
# Detected: import alias "np"
# Output: py:__RAW_B64__('aW1wb3J0IG51bXB5IGFzIG5w')
# Result: ✅ Works: np.array() still valid
```

---

## Prompt Caching Strategy

```
First Request:
├── User prompt: 100 tokens
├── File context (VL): 500 tokens  
└── VL spec (cached): 2693 tokens
    Total: 3293 tokens

Subsequent Requests:
├── User prompt: 100 tokens
├── File context (VL): 500 tokens
└── VL spec (cache hit): 2693 tokens (substantial discount)
    Effective cost: ~900 tokens
```

---

## Production Validation

**Tested:** 153 real-world Python files
- vocametrix-platform: 99 files
- RANCH: 22 files  
- xKozmos-signalprocessing: 32 files

**Results:**
- 100% success rate
- 127,871 tokens saved
- Zero files made larger
- Import aliases: 99% preserved

---

## Technical Specifications

**Language Support:**
- Current: Python (production)
- Planned: JavaScript, TypeScript

**Compilation Targets:**
- Python
- JavaScript
- TypeScript
- C
- Rust

**VS Code Integration:**
- Chat participant (@vl)
- Status bar widget
- Analytics dashboard
- CSV export

**Deployment:**
- Bundled compiler (portable)
- No external dependencies
- 100% local processing (free tier)
- Works offline

---

## Distribution

**Extension Package:**
- File: `vl-cost-optimizer-0.2.1-alpha.vsix`
- Size: ~994 KB (includes compiler)
- Installation: VS Code Extensions → Install from VSIX

**Demo Website:**
- URL: https://vl-demo-wine.vercel.app
- Features: Live Python↔VL conversion
- Technology: Vercel serverless + bundled compiler
