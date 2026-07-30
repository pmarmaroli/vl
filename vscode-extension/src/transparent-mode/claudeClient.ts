/**
 * Claude API Client
 *
 * Sends token-optimized context (minified Python, optionally with VL v2
 * macros) to the Claude API. The small v2 macro spec is added to the
 * system prompt only when macros are present in the context.
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
    /** Key under which the Anthropic API key is stored in SecretStorage */
    private static readonly API_KEY_SECRET = 'vl.claude.apiKey';

    private anthropic: Anthropic | null = null;
    private stats: CacheStats = {
        cacheWrites: 0,
        cacheReads: 0,
        cacheMisses: 0,
        specTokensSaved: 0,
        dollarsSavedFromCache: 0
    };

    constructor(private logger: Logger, private secrets: vscode.SecretStorage) {}

    /**
     * Get the API key from SecretStorage, migrating any key previously
     * stored in plain-text settings (vl.claude.apiKey) into secure storage.
     */
    async getApiKey(): Promise<string | undefined> {
        let apiKey = await this.secrets.get(ClaudeClient.API_KEY_SECRET);
        if (apiKey) {
            return apiKey;
        }

        // One-time migration from the old plain-text setting
        const config = vscode.workspace.getConfiguration('vl');
        const legacyKey = config.get<string>('claude.apiKey', '');
        if (legacyKey && legacyKey.trim()) {
            await this.secrets.store(ClaudeClient.API_KEY_SECRET, legacyKey.trim());
            await config.update('claude.apiKey', undefined, vscode.ConfigurationTarget.Global);
            this.logger.info('Migrated Anthropic API key from settings to secure storage');
            return legacyKey.trim();
        }
        return undefined;
    }

    /**
     * Whether an API key is available (without prompting the user)
     */
    async hasApiKey(): Promise<boolean> {
        return !!(await this.getApiKey());
    }

    /**
     * Prompt the user for an API key and store it in SecretStorage.
     * Returns the key, or undefined if the user cancelled.
     */
    async promptForApiKey(): Promise<string | undefined> {
        const inputKey = await vscode.window.showInputBox({
            prompt: 'Enter your Anthropic API key (starts with sk-ant-). It is stored in VS Code secure storage, never in settings.',
            password: true,
            placeHolder: 'sk-ant-api03-...',
            ignoreFocusOut: true
        });

        if (!inputKey || !inputKey.trim()) {
            return undefined;
        }

        await this.secrets.store(ClaudeClient.API_KEY_SECRET, inputKey.trim());
        this.anthropic = null; // Recreate the client with the new key
        this.logger.info('Anthropic API key saved to secure storage');
        return inputKey.trim();
    }

    /**
     * Remove the stored API key
     */
    async clearApiKey(): Promise<void> {
        await this.secrets.delete(ClaudeClient.API_KEY_SECRET);
        this.anthropic = null;
    }

    /**
     * Initialize the Claude client with API key
     */
    private async getClient(): Promise<Anthropic | null> {
        if (this.anthropic) {
            return this.anthropic;
        }

        let apiKey = await this.getApiKey();
        if (!apiKey) {
            apiKey = await this.promptForApiKey();
            if (!apiKey) {
                return null;
            }
        }

        this.anthropic = new Anthropic({ apiKey });
        this.logger.info('Claude client initialized with prompt caching enabled');

        return this.anthropic;
    }

    /**
     * Model used for completions (configurable via vl.claude.model)
     */
    private getModel(): string {
        const config = vscode.workspace.getConfiguration('vl');
        return config.get<string>('claude.model', 'claude-sonnet-5') || 'claude-sonnet-5';
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
     * Generate completion from optimized context.
     *
     * The system prompt depends on the context format:
     * - 'v2': the small VL v2 macro spec passed by the caller
     * - 'plain': minimal system prompt, no spec at all (the context is
     *   plain Python; sending a spec would waste tokens)
     */
    async generateCompletion(
        userPrompt: string,
        targetLanguage: 'python' | 'javascript' | 'typescript' = 'python',
        context: { format: 'v2' | 'plain'; spec?: string } = { format: 'plain' }
    ): Promise<string | null> {
        const client = await this.getClient();
        if (!client) {
            this.logger.warn('Claude client not initialized - API key missing');
            return null;
        }

        try {
            const response = await client.messages.create({
                model: this.getModel(),
                max_tokens: 4096,  // Increased for longer responses
                system: this.buildSystemPrompt(context),
                messages: [
                    {
                        role: "user",
                        content: this.buildChatPrompt(userPrompt, targetLanguage, context.format)
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
                vscode.window.showErrorMessage('Invalid Anthropic API key. Run "VL: Set Anthropic API Key" to update it.');
                // Clear invalid key from secure storage
                await this.clearApiKey();
            } else if (error.status === 429) {
                vscode.window.showWarningMessage('Claude API rate limit exceeded. Please try again later.');
            } else {
                vscode.window.showErrorMessage(`Claude API error: ${error.message}`);
            }
            
            return null;
        }
    }
    
    /**
     * Build the system prompt for the given context format
     */
    private buildSystemPrompt(context: { format: 'v2' | 'plain'; spec?: string }): any {
        if (context.format === 'v2' && context.spec) {
            // Small spec (~150 tokens) — below Anthropic's caching minimum,
            // included directly
            return [
                {
                    type: "text",
                    text: `You are a helpful coding assistant.\n\nThe user's code context is plain Python that may contain VL v2 macros — compact one-line calls that a compiler expands to standard Python. Treat them as known helpers:\n\n${context.spec}\nWhen you generate code for the user, write plain standard Python (do not use these macros in your answer unless the user asks for them).`
                }
            ];
        }
        return [
            {
                type: "text",
                text: "You are a helpful coding assistant. The user's code context is plain Python (comments and docstrings were stripped to save tokens; the logic is unchanged)."
            }
        ];
    }

    /**
     * Build prompt for chat requests (user request + optimized context)
     */
    private buildChatPrompt(userPrompt: string, targetLanguage: string, format: 'v2' | 'plain' = 'plain'): string {
        const langName = targetLanguage.charAt(0).toUpperCase() + targetLanguage.slice(1);
        const contextNote = '- The code context is Python, compacted to save tokens (logic unchanged)';

        return `User Request: ${userPrompt}

Important:
${contextNote}
- Respond to the user's request directly
- If generating code, use ${langName}
- Be concise but thorough
- Format code blocks with proper markdown`;
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
    
}
