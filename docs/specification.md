# VL Language Specification v0.1

**Status:** Draft  
**Version:** 0.1.3-alpha  
**Last Updated:** February 3, 2026  

**Repository:** https://github.com/pmarmaroli/vl  
**Documentation:** See README.md for setup and getting started  


-----

## Table of Contents

1. [Introduction](#introduction)
1. [Getting Started](#getting-started)
1. [Design Principles](#design-principles)
1. [Lexical Structure](#lexical-structure)
1. [Type System](#type-system)
1. [Core Constructs](#core-constructs)
1. [Domain-Specific Constructs](#domain-specific-constructs)
1. [Examples](#examples)
1. [Grammar Reference](#grammar-reference)

-----

## Getting Started

### Quick Setup

```bash
# 1. Clone repository
git clone https://github.com/pmarmaroli/vl.git
cd vl

# 2. Set Python path (required for compiler)
pip install -e .

# 3. Run your first program
./vl examples/basic/hello.vl
```

### Your First Program

Create `test.vl`:
```vl
msg='Hello, VL!'
@print(msg)
```

Compile and run:
```bash
./vl test.vl                           # Run via Python
./vl test.vl --target python -o test.py && python test.py
./vl test.vl --target javascript -o test.js && node test.js
```

### Basic Syntax Overview

```vl
# Variables (implicit, no prefix needed)
name='Alice'
age=30
scores=[95, 87, 92]

# Functions (F: prefix, single-char types)
F:greet|S|S|ret:'Hello, ${i0}!'

# Function calls
@print(@greet('World'))

# Conditionals
result=if:age>=18?'adult':'minor'

# Data pipelines
data:scores|filter:item>90|map:item*1.1
```

**Type Shortcuts:** `I`=int, `S`=str, `N`=float, `B`=bool, `A`=array, `O`=object

See [Core Constructs](#core-constructs) for complete syntax reference.

-----

## Introduction

VL (Vibe Language) is a high-level, intent-based programming language optimized for AI-assisted development. It is designed to minimize token usage in LLM code generation while maintaining complete semantic expressiveness.

### Goals

- **Token Efficiency**: 50-70% fewer tokens than equivalent Python/JavaScript
- **Semantic Clarity**: Unambiguous constructs eliminate interpretation errors
- **Intent-Based**: Express *what* the code should do, not *how*
- **Cross-Platform**: Single codebase for web, mobile, server, and embedded
- **FFI-First**: Native interoperability with existing language ecosystems

### Multi-Target Architecture

VL is a **universal intermediate representation (IR)** that compiles to multiple target languages:

**Currently Implemented:**
- ✅ **Python** - 100% operational (51/51 tests passing)
- ✅ **JavaScript** - 100% operational (14/14 tests passing)

**Fully Implemented:**
- ✅ **TypeScript** - Type-safe code generation with full type annotations
- ✅ **C** - ANSI C code generation with header management
- ✅ **Rust** - Safe Rust code generation with std library

**Configuration System:**

VL uses a centralized configuration module (`vl_config.py`) to control compilation behavior:

```python
# Boolean optimization settings
BOOLEAN_CHAIN_MIN_LENGTH = 3  # Min chain length for all()/any()
OPTIMIZE_BOOLEAN_CHAINS = True  # Enable/disable optimization

# Target-specific settings
TARGET_SETTINGS = {
    'python': {'boolean_optimization': True, 'supports_type_hints': True},
    'javascript': {'boolean_optimization': False, 'requires_semicolons': True},
    # ... per-target configuration
}
```

This allows fine-grained control over optimization strategies and target-specific code generation

**VL Philosophy:** Like LLVM, WebAssembly, or Java bytecode, VL serves as a single source of truth that compiles to optimized native code for each platform. Write once, compile everywhere.

**Target-Specific Optimization:**

Each codegen backend optimizes for its target language's idioms:
- **Python**: Uses `all()`/`any()` for boolean chains (Pythonic + token efficient)
- **JavaScript/TypeScript**: Uses native `&&`/`||` operators (idiomatic)
- **C/Rust**: Uses native operators with explicit parentheses (safe)

This means the same VL code generates optimal output for each platform automatically.

### Non-Goals

VL is not designed to:

- Replace domain-specific languages (SQL, HTML, CSS)
- Compete with shell scripting (Bash, PowerShell)
- Be the most human-readable language (optimization is for LLMs)

-----

## How VL Saves Tokens and Money

### The Token Efficiency Model

**IMPORTANT:** VL saves tokens during LLM code generation, NOT during execution. Understanding this distinction is critical.

#### Where Token Costs Occur (LLM API Calls)

Token costs happen when Large Language Models (LLMs) like Claude, GPT, or Gemini:

- **Read/analyze code** (input tokens)
- **Generate code** (output tokens)
- **Modify code** (input + output tokens)
- **Review code** (input tokens)
- **Explain code** (input tokens)

**Example Cost Comparison:**

Traditional approach (Python):

```python
def fetch_active_users(api_url):
    """Fetch users from API and filter for active users"""
    response = requests.get(api_url)
    data = response.json()
    return [item for item in data if item['status'] == 'active']
```

**LLM Token Cost:** ~39 tokens to generate

VL approach (with infix operators and expression pipelines):

```vl
F:fetchActive|S|A|v:result=api:GET,i0|ret:$result|filter:status=='active'
```

**LLM Token Cost:** ~30 tokens to generate

**Savings: 23.1% fewer tokens = 23.1% lower API costs**

**Real-World Benchmark Results (Updated Feb 2, 2026):**

Based on the latest benchmark run:
- **Token Efficiency Benchmark (13 cases):** 47.3% average savings (232 VL vs 440 Python tokens)
- **Strength/Weakness Analysis (15 scenarios):** 21.4% average savings; 15/15 compile
- **Examples:** 100% (12/12 example programs pass)
- **Robustness:** 100% (15/15 complex patterns pass)
- **Best Case:** 75.5% savings (multi-stage data pipelines)
- **Overall token efficiency (latest run):** 45.1% average across suites
- **Scenarios with >20% savings:** 8; **>10% overhead:** 0

**Syntax Features (v0.1.2):**
- Implicit variables: `x=5` (no `v:` prefix needed)
- Implicit function calls: `print('hi')` (no `@` prefix needed)
- Compound operators: `+=`, `-=`, `*=`, `/=`
- Range shorthand: `0..10` instead of `range(0,10)`
- **Compact keywords:** `F:` for functions, `M:` for meta, `E:` for export
- **Single-char types:** `I`=int, `S`=str, `N`=float, `B`=bool, `A`=arr, `O`=obj
- **Positional function syntax:** `F:name|types|type|body` (no `i:`/`o:` markers)

**Standard Syntax Example:**
```vl
# Function with two int inputs, int output
F:add|I,I|I|ret:i0+i1

# Data pipeline with array
F:process|A|A|ret:data:i0|filter:item>5|map:item*2

# Full program
M:myapp,function,python
F:greet|S|S|ret:'Hello, ${i0}!'
E:greet
```

-----

#### Where Token Costs Do NOT Occur (Local Machine Operations)

These operations happen on the user’s machine with **ZERO token costs:**

1. **VL Compilation** (Zero Tokens)
   
   ```bash
   vl compile --target python program.vl
   # This runs locally on your machine
   # No LLM API calls
   # No token costs
   ```
1. **Code Execution** (Zero Tokens)
   
   ```bash
   python program.py
   # Or: node program.js
   # Or: ./program (compiled C)
   # No LLM involved
   # No token costs
   ```
1. **FFI Library Calls** (Zero Tokens)
   
   ```vl
   ffi:python,numpy.array,[1,2,3]
   # This calls Python's numpy library locally
   # No LLM API calls
   # No token costs
   ```

-----

#### Complete Workflow: Where Costs Occur

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: LLM Code Generation (USES TOKENS $$)                │
├─────────────────────────────────────────────────────────────┤
│ Human: "Create a function that fetches users"               │
│    ↓                                                         │
│ LLM generates VL code (20 tokens):                          │
│ F:getUsers|S|A|api:GET,$i                                   │
│                                                              │
│ COST: 20 tokens × $0.003/1K = $0.00006                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: VL Compilation (NO TOKENS - FREE)                   │
├─────────────────────────────────────────────────────────────┤
│ User's machine: vl compile --target python program.vl       │
│    ↓                                                         │
│ VL Compiler generates Python/JS/C code locally              │
│                                                              │
│ COST: $0 (runs locally, no LLM calls)                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Code Execution (NO TOKENS - FREE)                   │
├─────────────────────────────────────────────────────────────┤
│ User's machine: python program.py                           │
│    ↓                                                         │
│ Compiled code runs, fetches data, produces results          │
│                                                              │
│ COST: $0 (normal program execution, no LLM)                 │
└─────────────────────────────────────────────────────────────┘
```

**Total LLM Cost: $0.00006 (only Step 1 uses tokens)**

Compare to traditional approach generating Python directly:

- LLM generates 80 tokens × $0.003/1K = $0.00024
- **VL is 75% cheaper!**

-----

#### Real-World Scenario: Iterative Development

**Scenario:** Developer asks LLM to modify code 10 times during development.

**Traditional (Python/JavaScript):**

```
Generation #1: 80 tokens output
Modification #2: 80 tokens input + 85 tokens output
Modification #3: 85 tokens input + 90 tokens output
...
Modification #10: ...

TOTAL: ~1,500 tokens
COST: ~$0.0045
```

**VL Approach:**

```
Generation #1: 20 tokens output
Modification #2: 20 tokens input + 22 tokens output
Modification #3: 22 tokens input + 23 tokens output
...
Modification #10: ...

TOTAL: ~400 tokens
COST: ~$0.0012
```

**Savings: $0.0033 per development session**

**At scale (1M developers, 100 sessions each):**

- Traditional: $450,000 in LLM API costs
- VL: $120,000 in LLM API costs
- **Savings: $330,000**

-----

#### Key Takeaway

**VL saves money by being compact when LLMs read/write code.**  
**VL costs nothing extra to compile or execute (happens locally).**

Think of VL like file compression:

- **Compressed file (VL):** Small, cheap to transfer (LLM generation)
- **Decompression (compilation):** Happens locally, free
- **Uncompressed file (Python/C):** Full functionality, runs normally

The compilation step is like unzipping a file on your computer—it’s free and happens locally!

-----

## Design Principles

### 1. Token Efficiency Over Verbosity

Traditional languages optimize for human readability:

```python
def calculate_average(numbers):
    """Calculate the average of a list of numbers"""
    return sum(numbers) / len(numbers)
```

VL optimizes for token efficiency:

```vl
F:avg|A|N|ret:op:/(agg:sum,i,agg:count,i)
```

### 2. Intent Over Implementation

VL describes the desired outcome, not the implementation steps:

```vl
# VL: What you want
api:GET,/users|filter:age>=18|map:name,email

# Not: How to do it (Python equivalent)
response = requests.get('/users')
users = response.json()
adults = [u for u in users if u['age'] >= 18]
result = [{'name': u['name'], 'email': u['email']} for u in adults]
```

### 3. Domain-Specific Constructs

Rather than general-purpose primitives, VL provides high-level operations for common domains:

- API/HTTP operations
- UI component composition
- Data transformations
- File I/O

### 4. Unambiguous Semantics

Every VL construct has exactly one interpretation:

```vl
# Clear: This is an API call followed by filtering
api:GET,/data|filter:x>0

# Not ambiguous: No confusion about execution order
```

-----

## Lexical Structure

### Keywords

Reserved words in VL:

**Core:**
`meta`, `deps`, `export`, `fn`, `i`, `o`, `ret`, `v`, `op`, `if`, `for`, `while`

**API Domain:**
`api`, `async`, `filter`, `map`, `parse`

**UI Domain:**
`ui`, `state`, `props`, `on`, `render`

**Data Domain:**
`data`, `groupBy`, `agg`, `sort`

**File Domain:**
`file`, `dir`, `path`

**Interop:**
`ffi`

### Operators

**Arithmetic:** `+`, `-`, `*`, `/`, `%`, `**`  
**Comparison:** `==`, `!=`, `<`, `>`, `<=`, `>=`  
**Logical:** `&&`, `||`, `!`  
**String:** `concat`, `split`, `join`

### Delimiters

- `:` (colon) - Key-value separator, type annotation
- `|` (pipe) - Statement separator, chaining operator
- `,` (comma) - List separator
- `=` (equals) - Assignment
- `?` `:` (ternary) - Conditional expression
- `$` (dollar) - Variable reference
- `()` (parentheses) - Grouping, function arguments
- `{}` (braces) - Object/map literals
- `[]` (brackets) - Array literals

### Literals

**Numbers:**

```vl
42          # Integer
3.14        # Float
-10         # Negative
1.5e10      # Scientific notation
```

**Strings:**

```vl
'hello'                  # Single quotes
"world"                  # Double quotes (equivalent)
'hello ${name}'          # Template string
'line1\nline2'          # Escape sequences
```

**Booleans:**

```vl
true
false
```

**Arrays:**

```vl
[1,2,3]
['a','b','c']
[]
```

**Objects:**

```vl
{key:'value',num:42}
{}
```

### Comments

```vl
# Single line comment

## 
Multi-line comment
Everything between ## markers
##
```

### Identifiers

- Must start with letter or underscore: `[a-zA-Z_]`
- Can contain letters, digits, underscore, hyphen: `[a-zA-Z0-9_-]*`
- Case-sensitive
- Cannot be keywords

**Valid:**

```vl
myVar
user_name
getData
my-component
_private
```

**Invalid:**

```vl
123abc      # Starts with digit
my var      # Contains space
fn          # Keyword
```

-----

## Type System

### Primitive Types

|Type   |Description           |Example Values          |
|-------|----------------------|------------------------|
|`int`  |Integer numbers       |`42`, `-10`, `0`        |
|`float`|Floating-point numbers|`3.14`, `-0.5`, `1.5e10`|
|`str`  |Text strings          |`'hello'`, `"world"`    |
|`bool` |Boolean values        |`true`, `false`         |

### Collection Types

|Type |Description    |Example               |
|-----|---------------|----------------------|
|`arr`|Ordered list   |`[1,2,3]`             |
|`obj`|Key-value pairs|`{name:'John',age:30}`|
|`map`|Hash map       |Similar to `obj`      |
|`set`|Unique values  |`{1,2,3}`             |

### Special Types

|Type     |Description    |Use Case         |
|---------|---------------|-----------------|
|`any`    |Any type       |Dynamic typing   |
|`void`   |No return value|Side effects only|
|`promise`|Async operation|Async functions  |
|`func`   |Function type  |Callbacks        |
|`node`   |React node     |UI components    |

### Type Inference

VL supports type inference - types can often be omitted:

```vl
# Explicit typing
v:count:int=0

# Inferred (int from literal)
v:count=0

# Inferred (arr from literal)
v:items=[1,2,3]
```

-----

## Core Constructs

### File Structure

Every VL file follows this structure:

```vl
M:name,type,target_language
deps:[dependencies]
[main content]
E:name
```

**Example:**

```vl
M:calculator,function,python
deps:math
F:add|I,I|I|ret:i0+i1
E:add
```

### Metadata Declaration

```vl
M:name,type,target
```

**Parameters:**

- `name` - Program/module name
- `type` - One of: `function`, `api_function`, `ui_component`, `data_processor`, `file_handler`
- `target` - Target language: `python`, `javascript`, `node`, `react`, `c`, `rust`

### Dependencies

```vl
deps:[dep1,dep2,dep3]
```

**Examples:**

```vl
deps:requests
deps:[numpy,pandas,sklearn]
deps:express,axios
```

### Functions

```vl
F:name|input_types|output_type|body
```

**Components:**

- `F:name` - Function name
- `input_types` - Input parameter types (comma-separated): `I,I` for two ints
- `output_type` - Return type: `I`, `S`, `A`, etc.
- `body` - Function body (can span multiple lines with `|`)

**Type Shortcuts:**
| Short | Full | Description |
|-------|------|-------------|
| `I` | int | Integer |
| `S` | str | String |
| `N` | float | Number (float) |
| `B` | bool | Boolean |
| `A` | arr | Array |
| `O` | obj | Object |
| `V` | void | Void |
| `P` | promise | Promise |
| `L` | func | Lambda/Function |

**Examples:**

```vl
# Simple function
F:double|I|I|ret:i0*2

# Multiple inputs
F:add|I,I|I|ret:i0+i1

# Array input
F:sum|A|I|ret:agg:sum,i0

# Multi-line body
F:process|A|A|
  filtered=filter:i0,x>0|
  doubled=map:filtered,x*2|
  ret:doubled
```

### Variables

Variables use implicit declaration (no prefix needed):

```vl
name=value              # Inferred type
name:type=value         # Explicit type
```

**Examples:**

```vl
count=0                 # int inferred
name='Alice'            # str inferred
items:A=[1,2,3]        # explicit array type
total:N=0.0            # explicit float type
```

### Direct Function Calls

For function calls without needing the return value, or within expressions, use the `@` syntax:

```vl
@function(args)
```

**Benefits:**
- More concise than variable assignment
- Reduces token count for simple operations
- Generates clean Python/JavaScript output
- Can be used in expressions and recursion

**Examples:**

```vl
# Print statement
@print('Hello World')

# API call
@requests.get('api/users')

# File operations
@fs.writeFile('data.txt','content')

# Method chaining
@logger.info('Starting process').timestamp()

# In expressions
v:result=@loadData()*2

# Recursion
F:fact|I|I|
  if:i0<=1?ret:1:ret:i0*@fact(i0-1)
```

**Comparison:**

```vl
# Old syntax (verbose)
v:msg='Hello'|v:x=print(msg)  # 13 tokens

# New @ syntax (concise)
@print('Hello')                # 6 tokens
# 54% token reduction!

# Recursion with @
F:fact|I|I|if:i0<=1?ret:1:ret:i0*@fact(i0-1)  # 29 tokens
# vs
F:fact|I|I|if:i0<=1?ret:1:ret:i0*fact(i0-1)   # 29 tokens (same!)
# @ makes recursion clearer without token overhead
```

### Operations

VL supports two syntaxes for operations: prefix notation and infix notation.

#### Prefix Notation (Traditional)

```vl
op:operator(operand1,operand2,...)
```

**Examples:**

```vl
op:+(5,3)                # Addition: 8
op:*(x,2)                # Multiply x by 2
op:>(age,18)             # Greater than: age > 18
op:&&(a,b)               # Logical AND
op:concat('Hello',' ','World')  # String concat
```

#### Infix Notation (Modern - Recommended)

For improved readability and token efficiency, VL supports standard infix operators:

**Arithmetic:**

```vl
i0 + i1                  # Addition
i0 - i1                  # Subtraction
i0 * i1                  # Multiplication
i0 / i1                  # Division
i0 % i1                  # Modulo
i0 ** i1                 # Power
```

**Comparison:**

```vl
age > 18                 # Greater than
age >= 18                # Greater or equal
age < 65                 # Less than
age <= 65                # Less or equal
age == 18                # Equal
age != 18                # Not equal
```

**Logical:**

```vl
a && b                   # Logical AND
a || b                   # Logical OR
!a                       # Logical NOT
```

**Token Efficiency Comparison:**

```vl
# Prefix notation
F:calc|I,I,I|I|ret:op:+(op:*(i0,i1),op:/(i2,2))  # 23 tokens

# Infix notation (recommended)
F:calc|I,I,I|I|ret:(i0*i1)+(i2/2)                # 23 tokens
# Similar token count but more readable and familiar syntax
```

**Boolean Logic Example:**

```vl
# Prefix: -86% efficiency (very verbose)
F:validate|I,I,B|B|ret:op:&&(op:>(i0,0),op:&&(op:<(i1,100),i2))

# Infix: Optimized per target language
F:validate|I,I,B|B|ret:i0>0&&i1<100&&i2
```

**Cross-Platform Boolean Optimization:**

VL uses `&&`, `||`, and `!` for boolean logic in the source language, but each target language codegen optimizes the output differently:

**VL Source (universal):**
```vl
F:validate|I,I,B|B|ret:i0>0&&i1<100&&i2
```

**Python Target (uses `all()` for token efficiency):**
```python
def validate(i0: int, i1: int, i2: bool) -> bool:
    return all([i0 > 0, i1 < 100, i2])
```

**JavaScript/TypeScript Target (native operators):**
```javascript
function validate(i0, i1, i2) {
    return i0 > 0 && i1 < 100 && i2;
}
```

**C Target (native operators with explicit parentheses):**
```c
bool validate(int i0, int i1, bool i2) {
    return (i0 > 0) && (i1 < 100) && i2;
}
```

**Rust Target (native operators):**
```rust
fn validate(i0: i32, i1: i32, i2: bool) -> bool {
    (i0 > 0) && (i1 < 100) && i2
}
```

**Key Design Decision:** VL maintains a single, universal syntax (`&&`, `||`, `!`) that each target language compiler optimizes appropriately. This is a core principle of VL as a **universal intermediate representation (IR)** - write once, optimize everywhere.

**Best Practice:** Use infix notation for arithmetic, comparison, and logical operators. Use prefix notation for special operations like `concat`, `merge`, etc.

### Early Returns in Conditionals

VL supports early return patterns in conditional expressions:

```vl
if:condition?ret:value:ret:other
```

**Examples:**

```vl
# Guard clause
if:op:==(i1,0)?ret:0:ret:op:/(i0,i1)

# API error handling
if:op:==(response.status,200)?ret:response.json:ret:{}
```

### Conditionals

```vl
if:condition?true_expr:false_expr
```

**Early Returns:**

VL supports early return patterns for guard clauses and error handling:

```vl
if:condition?ret:value:ret:other
```

**Examples:**

```vl
# Simple ternary
if:op:>(age,18)?'adult':'minor'

# Guard clause with early return
if:op:==(divisor,0)?ret:0:ret:op:/(dividend,divisor)

# API error handling
if:op:==(response.status,200)?ret:response.json:ret:{}

# Nested
if:op:>(x,0)?'positive':if:op:<(x,0)?'negative':'zero'

# With function calls
if:isEmpty($list)?'No data':'Has data'
```

**Complex String Interpolation:**

VL supports full expressions inside `${...}` including conditionals and operations:

```vl
'Hello ${name}, you are ${if:op:>(age,18)?'adult':'minor'}'
'Result: ${op:+(x,y)} = ${if:op:>(result,100)?'high':'low'}'
```

### Loops

**For Loop:**

```vl
for:var,iterable|body
```

**While Loop:**

```vl
while:condition|body
```

**Examples:**

```vl
# For each
for:item,items|print:$item

# For with index
for:i,range(0,10)|v:squared=op:*($i,$i)

# While
while:op:<(count,10)|v:count=op:+(count,1)
```

### Return Statement

```vl
ret:value
```

**Examples:**

```vl
ret:42
ret:$result
ret:op:+(a,b)
ret:[1,2,3]
```

-----

## Domain-Specific Constructs

### API/HTTP Operations

#### Basic HTTP Requests

```vl
api:METHOD,endpoint[,options]
```

**Methods:** `GET`, `POST`, `PUT`, `DELETE`, `PATCH`

**Examples:**

```vl
# Simple GET
api:GET,/users

# GET with query params
api:GET,/users,{query:{status:'active'}}

# POST with body
api:POST,/users,{body:{name:'John',age:30}}

# With headers (auth)
api:GET,/data,{headers:{Authorization:'Bearer ${token}'}}
```

#### Chaining Operations

```vl
# Filter response
api:GET,/users|filter:age>=18

# Extract fields
api:GET,/users|map:name,email

# Parse format
api:GET,/data|parse:json

# Chain multiple
api:GET,/users|filter:active==true|map:id,name|parse:json
```

#### Async Operations

```vl
async|api:GET,/data
```

### UI Components (React)

#### Component Declaration

```vl
ui:ComponentName|props:prop1:type,...|state:var:type=init,...|body
```

**Example:**

```vl
ui:Counter|state:count:int=0|
on:onClick|setState:count,op:+(count,1)|
render:div|
  render:h1|'Count: ${count}'|
  render:button,{onClick:$onClick}|'Increment'
```

#### State Management

```vl
state:varName:type=initialValue
setState:varName,newValue
```

#### Props

```vl
props:propName:type,propName2:type,...
```

#### Event Handlers

```vl
on:eventName|handler_body
```

**Common events:**

- `onClick`, `onChange`, `onSubmit`
- `onFocus`, `onBlur`
- `onMouseEnter`, `onMouseLeave`
- `onKeyDown`, `onKeyUp`

#### Rendering

```vl
render:element[,{attributes}]|children
```

**Examples:**

```vl
render:div|'Hello'
render:button,{className:'btn-primary',onClick:$handleClick}|'Click'
render:input,{type:'text',value:$inputValue,onChange:$handleChange}
```

#### Hooks

```vl
hook:hookName(args)
```

**Supported:**

- `useEffect(handler,deps)` - Side effects
- `useCallback(handler,deps)` - Memoized callbacks
- `useMemo(computation,deps)` - Memoized values
- `useRef(initialValue)` - Refs

**Example:**

```vl
hook:useEffect(async|api:GET,/data|setState:data,$result,[])
```

### Data Processing

#### Transform Pipeline

VL supports data pipelines starting from various sources:

**From Named Source:**

```vl
data:source|operation|operation|...
```

**From Expression (New!):**

VL now supports pipeline operations starting from any expression, including variables, API calls, and function returns:

```vl
# From variable
v:users=getUsers()|
ret:$users|filter:age>18|map:name

# From API call
F:fetchActive|S|A|
  v:result=api:GET,i0|
  ret:$result|filter:status=='active'

# From function call
ret:@loadData()|filter:x>0|map:x*2

# In return statement
F:process|A|A|
  ret:$i0|filter:active==true|map:salary*1.1
```

**Benefits:**

- Eliminates intermediate variables
- More declarative code
- Better token efficiency
- Cleaner function composition

**Token Comparison:**

```vl
# Without expression pipelines (old)
F:fetchActive|S|A|
  v:data=api:GET,i0|
  v:filtered=data:data|filter:status=='active'|
  ret:$filtered
# 30 tokens

# With expression pipelines (new)
F:fetchActive|S|A|
  v:result=api:GET,i0|
  ret:$result|filter:status=='active'
# 23 tokens (23% reduction!)
```

#### Core Operations

**Map (Transform):**

```vl
data:users|map:name,email
data:numbers|map:item*2          # Infix notation
data:items|map:{id:item.id,doubled:item.value*2}
```

**Filter (Select):**

```vl
data:users|filter:age>=18        # Infix notation
data:items|filter:status=='active'
data:values|filter:x>0&&x<100    # Infix logical operators
```

**Reduce (Aggregate):**

```vl
data:numbers|reduce:sum,0,op:+(acc,item)
data:items|reduce:total,0,op:+(acc,item.price)
```

**Sort:**

```vl
data:users|sort:age
data:products|sort:price,desc
```

**GroupBy:**

```vl
data:users|groupBy:country
data:sales|groupBy:category
```

**Aggregate:**

```vl
data:numbers|agg:sum
data:items|agg:avg,price
data:values|agg:count
```

**Unique:**

```vl
data:values|unique
data:users|unique:email
```

**Join:**

```vl
data:users|join:orders,on:userId
data:products|join:categories,left:catId,right:id
```

**Slice/Limit:**

```vl
data:items|slice:0,10
data:users|limit:20
data:results|skip:10|limit:10
```

### File I/O

#### File Operations

```vl
file:operation,path[,options]
```

**Read:**

```vl
file:read,data.txt
file:read,config.json,utf8
file:readLines,log.txt
file:readBytes,image.png
```

**Write:**

```vl
file:write,output.txt,'Hello World'
file:append,log.txt,'${timestamp}: ${message}\n'
file:writeBytes,output.bin,$data
```

**Parse/Serialize:**

```vl
file:read,data.json|parse:json
serialize:json,$data|file:write,output.json,$result
file:read,data.csv|parse:csv,{headers:true}
```

**File System:**

```vl
file:exists,config.json
file:delete,temp.txt
file:copy,source.txt,dest.txt
file:move,old.txt,new.txt
```

#### Directory Operations

```vl
dir:list,/data
dir:list,/logs,{pattern:'*.log',recursive:true}
dir:create,output/reports
dir:delete,temp,recursive:true
```

#### Path Operations

```vl
path:join,/data,users,profile.json
path:dirname,/data/users/profile.json
path:basename,/data/users/profile.json
path:extname,profile.json
```

### Foreign Function Interface (FFI)

```vl
ffi:language,function_path,args...
```

**Examples:**

```vl
# Call Python
ffi:python,numpy.array,[1,2,3]
ffi:python,pandas.read_csv,'data.csv'

# Call JavaScript/Node
ffi:node,express.Router()
ffi:node,lodash.chunk,$array,3

# Call Rust
ffi:rust,my_crate::process_data,$input
```

-----

#### What is FFI?

**FFI (Foreign Function Interface)** is a mechanism that allows VL to call functions written in other programming languages (Python, JavaScript, Rust, C, etc.).

Think of FFI as a **translator** or **bridge** between languages:

- VL can “speak” to Python
- VL can “speak” to JavaScript
- VL can “speak” to Rust
- VL can “speak” to C

-----

#### Why FFI Matters

**The Problem:**

- Python has 100,000+ libraries (numpy, pandas, scikit-learn, requests, etc.)
- JavaScript has millions of npm packages (express, react, lodash, axios, etc.)
- Rust has performance-critical libraries
- C has system-level libraries

Rewriting all these libraries in VL would take decades!

**The Solution:**
FFI lets VL use these existing libraries immediately—no rewriting needed!

-----

#### How FFI Works

```
┌──────────────┐
│  VL Program  │
│              │
│ ffi:python,  │
│ numpy.mean() │
└──────┬───────┘
       │
   ┌───▼────┐
   │  FFI   │  ← Bridge/Translator
   │ Layer  │
   └───┬────┘
       │
┌──────▼─────────┐
│ Python Runtime │
│                │
│  numpy.mean()  │  ← Actual Python library executes
└────────────────┘
```

**Important:** FFI calls happen **locally on your machine**—no LLM tokens used!

-----

#### FFI Strategy: Start Fast, Build Native Later

**Phase 1 (Year 1): Heavy FFI Usage**

```vl
# Use existing libraries via FFI
ffi:python,pandas.read_csv,'data.csv'
ffi:python,numpy.mean,$data
ffi:node,express.Router()
```

**Benefit:** VL works immediately with mature ecosystems

**Phase 2 (Year 2-3): Mixed Approach**

```vl
# Some native VL, some FFI
file:read,'data.csv'|parse:csv           # Native VL
ffi:python,scikit_learn.predict,$model   # Still use Python for ML
```

**Benefit:** Best of both worlds

**Phase 3 (Year 4+): Mostly Native**

```vl
# Pure VL implementations
file:read,'data.csv'|parse:csv
data:$values|stats:mean
ml:model:predict,$model,$data
```

**Benefit:** Performance optimization, full control

-----

#### Real-World Analogy

Imagine you’re starting a restaurant:

**Without FFI (Build Everything):**

- ❌ Grow your own wheat → Make flour → Bake bread
- ❌ Raise cows → Process milk → Make cheese
- ❌ Takes 10 years before you can serve a sandwich

**With FFI (Use Suppliers):**

- ✅ Buy bread from bakery
- ✅ Buy cheese from dairy
- ✅ Serve sandwiches **today**
- ✅ Gradually make your own bread/cheese later (if desired)

**FFI lets VL “buy ingredients” from Python/JS/Rust instead of making everything from scratch!**

-----

#### FFI Examples by Use Case

**Data Science:**

```vl
# Use Python's data science ecosystem
ffi:python,pandas.read_csv,'sales.csv'
ffi:python,numpy.mean,$data
ffi:python,matplotlib.plot,$x,$y
```

**Web Development:**

```vl
# Use Node.js web frameworks
ffi:node,express()
ffi:node,next.create_app()
```

**Performance:**

```vl
# Use Rust for heavy computation
ffi:rust,image_processor::resize,$image,800,600
ffi:rust,crypto::hash_password,$password
```

**System Access:**

```vl
# Use C for low-level operations
ffi:c,libc::fopen,$filename,'r'
```

-----

#### FFI Cost Model

**IMPORTANT:** FFI has **zero LLM token costs**—it runs locally!

```
VL code with FFI:
F:analyze|S|O|
  v:data=ffi:python,pandas.read_csv,$i     ← Free (local)
  v:mean=ffi:python,numpy.mean,$data       ← Free (local)
  ret:$mean

LLM Token Cost: ~25 tokens (just the VL code generation)
FFI Execution Cost: $0 (runs on user's machine)
```

Compare to pure Python approach:

```python
LLM Token Cost: ~80 tokens (verbose Python code)
```

**VL with FFI: 68% token savings, same functionality!**

-----

## Examples

### Example 1: Simple Function

```vl
M:calculator,function,python
F:add|I,I|I|ret:op:+(i0,i1)
E:add
```

### Example 2: API Function

```vl
M:getAdultUsers,api_function,python
deps:requests
F:getAdultUsers|S|A|
async|api:GET,$i|filter:age>=18|map:name,email
E:getAdultUsers
```

### Example 3: React Component

```vl
M:Counter,ui_component,react
ui:Counter|state:count:int=0|
on:handleClick|setState:count,op:+(count,1)|
render:div,{className:'counter'}|
  render:h1|'Count: ${count}'|
  render:button,{onClick:$handleClick}|'Increment'
E:Counter
```

### Example 4: Data Pipeline

```vl
M:processSales,data_processor,python
F:processSales|S|O|
file:read,$i|parse:csv,{headers:true}|
data:$data|
  filter:amount>100|
  groupBy:category|
  agg:sum,amount|
  sort:total,desc|
ret:$result
E:processSales
```

### Example 5: Complex Workflow

```vl
M:userAnalytics,api_function,node
deps:[axios,lodash]

F:analyzeUsers|S|O|
  # Fetch user data
  v:users=async|api:GET,$i|parse:json|
  
  # Process data
  v:activeUsers=data:$users|filter:status=='active'|
  v:byCountry=data:$activeUsers|groupBy:country|
  
  # Calculate stats
  v:stats=data:$byCountry|map:{
    country:key,
    count:agg:count,
    avgAge:agg:avg,age,
    totalRevenue:agg:sum,revenue
  }|
  
  # Sort and format
  v:result=data:$stats|sort:totalRevenue,desc|limit:10|
  
  ret:$result

E:analyzeUsers
```

-----

## Grammar Reference

### EBNF Grammar (Informal)

```ebnf
program = metadata , dependencies? , statements , export ;

metadata = "meta" , ":" , identifier , "," , type , "," , target ;

dependencies = "deps" , ":" , ( identifier | "[" , identifier-list , "]" ) ;

export = "export" , ":" , identifier ;

statements = statement , ( "|" , statement )* ;

statement = function-def
          | variable-def
          | operation
          | conditional
          | loop
          | return-stmt
          | api-call
          | ui-component
          | data-pipeline
          | file-operation
          | ffi-call ;

function-def = "fn" , ":" , identifier , 
               "|" , "i" , ":" , type-list ,
               "|" , "o" , ":" , type ,
               "|" , statements ;

variable-def = "v" , ":" , identifier , ( ":" , type )? , "=" , expression ;

operation = "op" , ":" , operator , "(" , expression-list , ")" ;

conditional = "if" , ":" , expression , "?" , expression , ":" , expression ;

loop = ( "for" | "while" ) , ":" , parameters , "|" , statements ;

return-stmt = "ret" , ":" , expression ;

type = "int" | "float" | "str" | "bool" | "arr" | "obj" | "any" | ... ;

expression = literal
           | identifier
           | operation
           | conditional
           | function-call
           | "$" , identifier ;

literal = number | string | boolean | array | object ;

identifier = letter , ( letter | digit | "_" | "-" )* ;
```

-----

## Reserved for Future Versions

Features planned but not yet in v0.1:

- **Classes/Objects** - Object-oriented programming
- **Modules** - Multi-file programs
- **Generators** - Lazy evaluation
- **Pattern Matching** - Advanced conditionals
- **Async/Await** - More robust async handling
- **Error Handling** - Try/catch/finally
- **Decorators** - Function/class modification
- **Macros** - Compile-time code generation

-----

## Appendix A: Keyword Reference

Complete list of reserved keywords:

```
meta, deps, export, fn, i, o, ret, v, op, if, for, while,
api, async, filter, map, parse, reduce, sort, groupBy, agg,
ui, state, props, on, render, hook,
data, file, dir, path, ffi,
int, float, str, bool, arr, obj, map, set, any, void, promise, func
```

-----

## Appendix B: Operator Precedence

From highest to lowest:

1. Parentheses `()`
1. Member access `.`
1. Function call `()`
1. Unary `!`, `-`
1. Power `**`
1. Multiply/Divide `*`, `/`, `%`
1. Add/Subtract `+`, `-`
1. Comparison `<`, `>`, `<=`, `>=`
1. Equality `==`, `!=`
1. Logical AND `&&`
1. Logical OR `||`
1. Ternary `? :`
1. Assignment `=`

-----

## Appendix C: Naming Conventions

**Recommended (not enforced):**

- Functions: `camelCase` - `getUserData`, `calculateTotal`
- Variables: `snake_case` or `camelCase` - `user_count`, `itemList`
- Constants: `UPPER_CASE` - `MAX_SIZE`, `DEFAULT_PORT`
- Types: `lowercase` - `int`, `str`, `arr`
- Components: `PascalCase` - `UserCard`, `NavBar`

-----

## Contributing

This specification is a living document. To propose changes:

1. Open an issue on GitHub
1. Discuss the proposal with the community
1. Submit a pull request with changes
1. Update version number and changelog

-----

## Changelog

### v0.1.0-alpha (2026-01-29)

- Initial specification
- Core constructs defined
- Four domain-specific construct sets (API, UI, Data, File)
- Basic type system
- FFI support

-----

**Document Version:** 1.0.0  
**Specification Version:** 0.1.0-alpha  
**License:** MIT  
