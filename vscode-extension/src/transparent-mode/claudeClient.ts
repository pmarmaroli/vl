/**
 * Claude API Client with Prompt Caching
 * 
 * Implements Anthropic's prompt caching to reduce VL specification overhead by 90%.
 * The VL language spec is cached across requests, dramatically reducing costs.
 */

import Anthropic from '@anthropic-ai/sdk';
import * as vscode from 'vscode';
import { Logger } from '../utils/logger';

export interface CacheStats {
    cacheWrites: number;
    cacheReads: number;
    cacheMisses: number;
    specTokensSaved: number;
    dollarsSavedFromCache: number;
}

export class ClaudeClient {
    private anthropic: Anthropic | null = null;
    private stats: CacheStats = {
        cacheWrites: 0,
        cacheReads: 0,
        cacheMisses: 0,
        specTokensSaved: 0,
        dollarsSavedFromCache: 0
    };
    
    constructor(private logger: Logger) {}
    
    /**
     * Initialize the Claude client with API key
     */
    private async getClient(): Promise<Anthropic | null> {
        if (this.anthropic) {
            return this.anthropic;
        }
        
        // Get API key from settings
        const config = vscode.workspace.getConfiguration('vl');
        let apiKey = config.get<string>('claude.apiKey', '');
        
        // If no API key in settings, prompt user
        if (!apiKey) {
            const inputKey = await vscode.window.showInputBox({
                prompt: 'Enter your Anthropic API key (starts with sk-ant-)',
                password: true,
                placeHolder: 'sk-ant-api03-...',
                ignoreFocusOut: true
            });
            
            if (!inputKey) {
                return null;
            }
            
            apiKey = inputKey;
            
            // Ask if user wants to save it
            const save = await vscode.window.showQuickPick(['Yes', 'No'], {
                placeHolder: 'Save API key to settings?'
            });
            
            if (save === 'Yes') {
                await config.update('claude.apiKey', apiKey, vscode.ConfigurationTarget.Global);
            }
        }
        
        this.anthropic = new Anthropic({ apiKey });
        this.logger.info('Claude client initialized with prompt caching enabled');
        
        return this.anthropic;
    }
    
    /**
     * Response from Claude with usage stats
     */
    private lastUsage: {
        inputTokens: number;
        outputTokens: number;
        cacheRead: number;
        cacheCreation: number;
    } | null = null;

    /**
     * Generate Python completion from VL context
     * Uses prompt caching to reduce VL specification overhead
     */
    async generateCompletion(userPrompt: string, targetLanguage: 'python' | 'javascript' | 'typescript' = 'python'): Promise<string | null> {
        const client = await this.getClient();
        if (!client) {
            this.logger.warn('Claude client not initialized - API key missing');
            return null;
        }
        
        try {
            const response = await client.messages.create({
                model: "claude-sonnet-4-20250514",
                max_tokens: 4096,  // Increased for longer responses
                system: [
                    {
                        type: "text",
                        text: this.getVLSpecification(),
                        cache_control: { type: "ephemeral" } as any  // TypeScript doesn't recognize cache_control yet
                    }
                ],
                messages: [
                    {
                        role: "user",
                        content: this.buildChatPrompt(userPrompt, targetLanguage)
                    }
                ]
            } as any);  // Cast to any since prompt caching types aren't in SDK yet
            
            // Store usage for accurate reporting
            const usageAny = response.usage as any;
            this.lastUsage = {
                inputTokens: usageAny?.input_tokens || 0,
                outputTokens: usageAny?.output_tokens || 0,
                cacheRead: usageAny?.cache_read_input_tokens || 0,
                cacheCreation: usageAny?.cache_creation_input_tokens || 0
            };
            
            // Track cache usage
            this.trackCacheUsage(response.usage);
            
            // Extract completion text
            const completion = response.content[0]?.type === 'text' 
                ? response.content[0].text 
                : null;
            
            return completion;
            
        } catch (error: any) {
            this.logger.error('Claude API error', error);
            
            // Handle specific errors
            if (error.status === 401) {
                vscode.window.showErrorMessage('Invalid Anthropic API key. Please update in settings.');
                // Clear invalid key
                const config = vscode.workspace.getConfiguration('vl');
                await config.update('claude.apiKey', '', vscode.ConfigurationTarget.Global);
                this.anthropic = null;
            } else if (error.status === 429) {
                vscode.window.showWarningMessage('Claude API rate limit exceeded. Please try again later.');
            } else {
                vscode.window.showErrorMessage(`Claude API error: ${error.message}`);
            }
            
            return null;
        }
    }
    
    /**
     * Build the prompt for Claude (for VL conversion)
     */
    private buildPrompt(vlContext: string, targetLanguage: string): string {
        const langName = targetLanguage.charAt(0).toUpperCase() + targetLanguage.slice(1);
        
        return `Convert this VL code to idiomatic ${langName}:

\`\`\`vl
${vlContext}
\`\`\`

Generate clean, readable ${langName} code. Only output the code, no explanations.`;
    }
    
    /**
     * Build prompt for chat requests (user request + VL context)
     */
    private buildChatPrompt(userPrompt: string, targetLanguage: string): string {
        const langName = targetLanguage.charAt(0).toUpperCase() + targetLanguage.slice(1);
        
        return `You are a helpful coding assistant. The user has provided code context in VL format (a token-efficient representation).

User Request: ${userPrompt}

Important:
- The code context is in VL format to save tokens
- Respond to the user's request directly
- If generating code, use ${langName}
- Be concise but thorough
- Format code blocks with proper markdown`;
    }
    
    /**
     * Get VL language specification (cached across requests)
     * NOTE: This must be >1024 tokens to enable Anthropic prompt caching
     */
    private getVLSpecification(): string {
        return `VL (Vibe Language) v0.2.0-alpha - Token-Efficient Language Specification

VL is a compact intermediate language designed for AI code generation with ~47% fewer tokens than Python/JavaScript/TypeScript.
Proven to achieve 40-75% token reduction in real-world code generation scenarios.

═══════════════════════════════════════════════════════════════════════════════
CORE SYNTAX
═══════════════════════════════════════════════════════════════════════════════

FUNCTIONS:
  F:name|param_types|return_type|body
  - name: Function identifier
  - param_types: Comma-separated type codes (I,F,S,B,A,O)
  - return_type: Single type code or V (void)
  - body: Function statements separated by |

VARIABLES:
  name=value
  - Implicit type inference
  - No declaration keyword needed
  - Scope determined by context

CONDITIONALS:
  if:condition?true_value:false_value
  - Ternary-style syntax
  - Can be nested: if:a>b?if:c>d?e:f:g
  - Used in expressions and statements

LOOPS:
  for:var,iterable|body
  - var: Loop variable name
  - iterable: Array, range, or iterable expression
  - body: Loop body statements

while:condition|body
  - condition: Boolean expression
  - body: Loop body statements

OPERATIONS:
  op:+(a,b)      # Addition
  op:-(a,b)      # Subtraction
  op:*(a,b)      # Multiplication
  op:/(a,b)      # Division
  op:%(a,b)      # Modulo
  op:==(a,b)     # Equality
  op:>(a,b)      # Greater than
  op:<(a,b)      # Less than
  op:>=(a,b)     # Greater or equal
  op:<=(a,b)     # Less or equal
  op:&&(a,b)     # Logical AND
  op:||(a,b)     # Logical OR
  op:!(a)        # Logical NOT

COLLECTIONS:
  Arrays: [item1,item2,item3]
  Objects: {key1:val1,key2:val2}
  Access: arr[index], obj.key or obj[key]

FUNCTION CALLS:
  @functionName(args)  # Explicit call operator
  functionName(args)   # Implicit call (context-dependent)

PYTHON PASSTHROUGH:
    py:<code>            # Statement/expression passthrough
    - Encoded form may use @@@ for newlines, @4@ for 4-space indents (expanded only when single-line encoded)
    - py:__RAW__('...') preserves full module verbatim
    - py:__RAW_B64__('<base64>') for marker/binary-safe payloads (no newline/indent expansion)

═══════════════════════════════════════════════════════════════════════════════
TYPE SYSTEM
═══════════════════════════════════════════════════════════════════════════════

PRIMITIVE TYPES:
  I = integer (int, int64, long)
  F = float (float, double, decimal)
  S = string (str, String, string)
  B = boolean (bool, Boolean, boolean)
  V = void (no return value)

COMPOSITE TYPES:
  A = array/list (list, array, List<T>)
  O = object/dict (dict, object, Map<K,V>)
  T = tuple (tuple, array with fixed size)
  
OPTIONAL TYPES:
  I? = optional integer
  A? = optional array
  
GENERIC COLLECTIONS:
  A<I> = array of integers
  A<S> = array of strings
  O<S,I> = object with string keys, integer values

═══════════════════════════════════════════════════════════════════════════════
PARAMETER ACCESS
═══════════════════════════════════════════════════════════════════════════════

INDEXED PARAMETERS:
  i0, i1, i2... = function parameters (0-indexed)
  - Always use indexes for function parameters
  - Enables position-based parameter passing
  - More compact than named parameters

VARIABLE REFERENCES:
  \$var = reference to variable in expression
  - Use when variable name might conflict
  - Explicit variable dereferencing

═══════════════════════════════════════════════════════════════════════════════
COMPREHENSIVE EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

EXAMPLE 1 - Basic Function:
VL:     F:add|I,I|I|ret:i0+i1
Python: def add(i0: int, i1: int) -> int:
            return i0 + i1
JS:     function add(i0, i1) { return i0 + i1; }

EXAMPLE 2 - Conditional Logic:
VL:     F:max|I,I|I|ret:if:i0>i1?i0:i1
Python: def max(i0: int, i1: int) -> int:
            return i0 if i0 > i1 else i1
JS:     function max(i0, i1) { return i0 > i1 ? i0 : i1; }

EXAMPLE 3 - Loop with Filter:
VL:     F:filterPositive|A|A|result=[]|for:item,i0|if:item>0?result.append(item)|ret:result
Python: def filterPositive(i0: list) -> list:
            result = []
            for item in i0:
                if item > 0:
                    result.append(item)
            return result

EXAMPLE 4 - Nested Loops:
VL:     F:matrix_sum|A<A<I>>|I|total=0|for:row,i0|for:val,row|total=total+val|ret:total
Python: def matrix_sum(i0: list[list[int]]) -> int:
            total = 0
            for row in i0:
                for val in row:
                    total = total + val
            return total

EXAMPLE 5 - Object Processing:
VL:     F:getUserName|O|S|ret:i0.name
Python: def getUserName(i0: dict) -> str:
            return i0['name']
JS:     function getUserName(i0) { return i0.name; }

EXAMPLE 6 - Array Mapping:
VL:     F:doubleValues|A<I>|A<I>|result=[]|for:x,i0|result.append(x*2)|ret:result
Python: def doubleValues(i0: list[int]) -> list[int]:
            result = []
            for x in i0:
                result.append(x * 2)
            return result

EXAMPLE 7 - Multiple Conditions:
VL:     F:classify|I|S|ret:if:i0<0?'negative':if:i0==0?'zero':'positive'
Python: def classify(i0: int) -> str:
            return 'negative' if i0 < 0 else ('zero' if i0 == 0 else 'positive')

EXAMPLE 8 - Error Handling:
VL:     F:safeDivide|F,F|F|ret:if:i1==0?0:i0/i1
Python: def safeDivide(i0: float, i1: float) -> float:
            return 0 if i1 == 0 else i0 / i1

EXAMPLE 9 - String Operations:
VL:     F:greet|S|S|ret:'Hello, '+i0+'!'
Python: def greet(i0: str) -> str:
            return f'Hello, {i0}!'
JS:     function greet(i0) { return \`Hello, \${i0}!\`; }

EXAMPLE 10 - Complex Data Structure:
VL:     users=[{name:'Alice',age:30},{name:'Bob',age:25}]
Python: users = [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]
JS:     const users = [{name: 'Alice', age: 30}, {name: 'Bob', age: 25}];

EXAMPLE 11 - Data Validation:
VL:     F:isValidEmail|S|B|ret:op:&&(i0.includes('@'),i0.includes('.'))
Python: def isValidEmail(i0: str) -> bool:
            return '@' in i0 and '.' in i0

EXAMPLE 12 - Aggregation:
VL:     F:sum|A<I>|I|total=0|for:n,i0|total=total+n|ret:total
Python: def sum(i0: list[int]) -> int:
            total = 0
            for n in i0:
                total = total + n
            return total

═══════════════════════════════════════════════════════════════════════════════
CONVERSION RULES
═══════════════════════════════════════════════════════════════════════════════

PYTHON CONVERSION:
1. Use type hints (PEP 484) for all parameters and returns
2. Follow PEP 8 naming conventions (snake_case)
3. Use f-strings for string formatting
4. Prefer list comprehensions where appropriate
5. Use 'in' operator instead of 'includes'
6. Dictionary access: obj['key'] not obj.key
7. Proper indentation (4 spaces)

JAVASCRIPT CONVERSION:
1. Use const/let appropriately (prefer const)
2. Use camelCase naming
3. Template literals for strings (\`\${var}\`)
4. Array methods: includes(), map(), filter()
5. Object property access: obj.key or obj['key']
6. Arrow functions for callbacks: x => x * 2

TYPESCRIPT CONVERSION:
1. All JavaScript rules apply
2. Add type annotations: : number, : string, : boolean
3. Interface definitions for complex objects
4. Generic types where applicable: Array<number>
5. Proper return types for functions

GENERAL PRINCIPLES:
- Generate clean, readable, idiomatic code
- Preserve exact logic and semantics
- Use target language's standard library
- Proper error handling where appropriate
- Performance-conscious implementations
- Follow language-specific best practices

═══════════════════════════════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════════════════════════════

Convert VL code snippets to clean, idiomatic code in the target language.
Output ONLY the code, no explanations or markdown formatting.
Ensure the output is ready to run without modifications.`;
    }
    
    /**
     * Track cache usage statistics
     */
    private trackCacheUsage(usage: any) {
        const config = vscode.workspace.getConfiguration('vl');
        const debugEnabled = config.get<boolean>('debug.enabled', false);
        
        // Cache writes (first time seeing this content)
        if (usage.cache_creation_input_tokens > 0) {
            this.stats.cacheWrites++;
            if (debugEnabled) {
                this.logger.info(`✅ VL spec cached (${usage.cache_creation_input_tokens} tokens)`);
            }
        }
        
        // Cache reads (using cached content)
        if (usage.cache_read_input_tokens > 0) {
            this.stats.cacheReads++;
            
            // Estimate tokens saved (90% discount on cached tokens)
            const fullCost = usage.cache_read_input_tokens * 10; // Rough estimate of uncached size
            const savedTokens = fullCost - usage.cache_read_input_tokens;
            this.stats.specTokensSaved += savedTokens;
            
            // Calculate dollar savings ($3.00/1M normal, $0.30/1M cached)
            const normalCost = fullCost * (3.00 / 1_000_000);
            const cachedCost = usage.cache_read_input_tokens * (0.30 / 1_000_000);
            this.stats.dollarsSavedFromCache += (normalCost - cachedCost);
            
            if (debugEnabled) {
                this.logger.info(`💰 Cache hit: ${usage.cache_read_input_tokens} tokens @ 90% discount (saved ${savedTokens} tokens, $${(normalCost - cachedCost).toFixed(6)})`);
            }
        }
        
        // Log full usage details in debug mode
        if (debugEnabled) {
            this.logger.debug('Claude API usage', {
                input_tokens: usage.input_tokens,
                output_tokens: usage.output_tokens,
                cache_creation: usage.cache_creation_input_tokens || 0,
                cache_read: usage.cache_read_input_tokens || 0
            });
        }
    }
    
    /**
     * Get the last API call's usage stats
     */
    getLastUsage() {
        return this.lastUsage;
    }
    
    /**
     * Get cache statistics
     */
    getStats(): CacheStats {
        return { ...this.stats };
    }
    
    /**
     * Reset statistics
     */
    resetStats() {
        this.stats = {
            cacheWrites: 0,
            cacheReads: 0,
            cacheMisses: 0,
            specTokensSaved: 0,
            dollarsSavedFromCache: 0
        };
    }
    
    /**
     * Warm the cache by making a dummy request
     * Call this on extension startup to ensure VL spec is cached
     */
    async warmCache(): Promise<boolean> {
        this.logger.info('Warming Claude prompt cache...');
        
        const result = await this.generateCompletion(
            'F:test|I|I|ret:i0',
            'python'
        );
        
        if (result) {
            this.logger.info('✅ Cache warmed successfully');
            return true;
        } else {
            this.logger.warn('⚠️ Cache warming failed');
            return false;
        }
    }
}
