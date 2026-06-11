/**
 * VL Chat Participant - Intercepts agent/chat requests and optimizes with VL
 * This is the REAL transparent mode - optimizing complete code blocks in chat context
 */

import * as vscode from 'vscode';
import { VLConverter } from '../converter/vlConverter';
import { Logger } from '../utils/logger';
import { TokenSavingsStatusBar } from '../ui/statusBar';
import { ClaudeClient } from './claudeClient';
import { estimateTokens } from '../utils/tokenEstimator';
import { AnalyticsTracker } from '../analytics/analyticsTracker';

interface ChatContext {
    originalContent: string;
    vlContent: string;
    originalTokens: number;
    vlTokens: number;
    language: string;
    /**
     * 'python-min' = minified plain Python, 'v2' = minified Python with VL v2
     * macros, 'vl' = VL syntax, 'original' = unchanged
     */
    format: 'python-min' | 'v2' | 'vl' | 'original';
    /** VL v2 macro spec (set only for format 'v2') */
    spec?: string;
}

export class VLChatParticipant {
    private requestCount = 0;
    private totalOriginalTokens = 0;
    private totalVLTokens = 0;
    
    constructor(
        private converter: VLConverter,
        private statusBar: TokenSavingsStatusBar,
        private logger: Logger,
        private analytics: AnalyticsTracker,
        private claudeClient?: ClaudeClient
    ) {}
    
    /**
     * Register the chat participant
     */
    static register(
        context: vscode.ExtensionContext,
        converter: VLConverter,
        statusBar: TokenSavingsStatusBar,
        logger: Logger,
        analytics: AnalyticsTracker,
        claudeClient?: ClaudeClient
    ): VLChatParticipant {
        const participant = new VLChatParticipant(converter, statusBar, logger, analytics, claudeClient);
        
        // Register chat participant with vscode.chat API
        const chatParticipant = vscode.chat.createChatParticipant(
            'vl.optimizer',
            participant.handleChatRequest.bind(participant)
        );
        
        chatParticipant.iconPath = vscode.Uri.file(
            context.asAbsolutePath('resources/vl-icon.png')
        );
        
        context.subscriptions.push(chatParticipant);
        
        logger.info('VL Chat Participant registered');
        return participant;
    }
    
    /**
     * Handle chat request - intercept and optimize with VL
     */
    private async handleChatRequest(
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<void> {
        this.requestCount++;
        
        const config = vscode.workspace.getConfiguration('vl');
        const debugEnabled = config.get<boolean>('debug.enabled', false);
        const apiKey = config.get<string>('claude.apiKey', '');
        const isMonitoringMode = !apiKey || apiKey.trim() === '';
        
        try {
            // Extract file references from the request
            const fileContexts = await this.extractFileContexts(request, context);
            
            if (fileContexts.length === 0) {
                // No file context - pass through to default agent
                stream.markdown('*VL: No code files in context - passing to default agent*\n\n');
                return;
            }
            
            // Convert all file contexts to VL
            const vlContexts: ChatContext[] = [];
            const conversionErrors: Array<{ file: string; error: any }> = [];
            let totalSaved = 0;
            
            for (const fileCtx of fileContexts) {
                try {
                    // Optimize per the configured mode (minify | vl | auto).
                    // Never returns something more expensive than the original.
                    const result = await this.converter.optimize(
                        fileCtx.content,
                        fileCtx.language as 'python' | 'javascript' | 'typescript'
                    );

                    const saved = result.originalTokens - result.optimizedTokens;

                    if (result.format === 'original') {
                        this.logger.info(`Optimization did not reduce size for ${fileCtx.file}, using original`);
                    }

                    vlContexts.push({
                        originalContent: fileCtx.content,
                        vlContent: result.content,
                        originalTokens: result.originalTokens,
                        vlTokens: result.optimizedTokens,
                        language: fileCtx.language,
                        format: result.format,
                        spec: result.spec
                    });

                    totalSaved += saved;

                    // Update status bar
                    this.statusBar.recordSavings(result.originalTokens, result.optimizedTokens);
                    this.totalOriginalTokens += result.originalTokens;
                    this.totalVLTokens += result.optimizedTokens;

                    // Record in analytics
                    this.analytics.recordSavings({
                        fileName: fileCtx.file,
                        language: fileCtx.language,
                        originalTokens: result.originalTokens,
                        vlTokens: result.optimizedTokens,
                        savedTokens: saved,
                        savingsPercent: result.originalTokens > 0 ? (saved / result.originalTokens) * 100 : 0,
                        mode: isMonitoringMode ? 'monitoring' : 'active',
                    });

                } catch (error) {
                    // Optimization failed entirely - use original code
                    conversionErrors.push({ file: fileCtx.file, error });

                    this.logger.warn(`Optimization failed for ${fileCtx.file}, using original code`, error);

                    const originalTokens = estimateTokens(fileCtx.content, fileCtx.language);

                    vlContexts.push({
                        originalContent: fileCtx.content,
                        vlContent: fileCtx.content, // Use original as fallback
                        originalTokens,
                        vlTokens: originalTokens, // No savings
                        language: fileCtx.language,
                        format: 'original'
                    });
                }
            }
            
            // Notify about conversion errors
            if (conversionErrors.length > 0) {
                stream.markdown(`**⚠️ VL Conversion Issues:**\n`);
                for (const err of conversionErrors) {
                    const fileName = err.file.split(/[/\\]/).pop();
                    stream.markdown(`- ${fileName}: Using original code (conversion failed)\n`);
                }
                stream.markdown(`\n_Don't worry - proceeding with original ${conversionErrors[0].error?.toString().includes('syntax') ? 'syntax-checked' : ''} code._\n\n`);
            }
            
            // Show savings summary
            if (vlContexts.length > 0) {
                const savingsPercent = totalSaved > 0 
                    ? ((totalSaved / this.totalOriginalTokens) * 100).toFixed(1)
                    : '0.0';
                
                // Show mode-specific header
                if (isMonitoringMode) {
                    stream.markdown(`**📊 VL Monitoring Mode** _(Free Tier)_\n`);
                } else {
                    stream.markdown(`**🚀 VL Active Optimization** _(Premium)_\n`);
                }
                
                const minified = vlContexts.filter(c => c.format === 'python-min').length;
                const asV2 = vlContexts.filter(c => c.format === 'v2').length;
                const asVL = vlContexts.filter(c => c.format === 'vl').length;
                const untouched = vlContexts.filter(c => c.format === 'original').length;
                const parts: string[] = [];
                if (minified > 0) { parts.push(`${minified} minified`); }
                if (asV2 > 0) { parts.push(`${asV2} macro-compressed (v2)`); }
                if (asVL > 0) { parts.push(`${asVL} converted to VL`); }
                if (untouched > 0) { parts.push(`${untouched} kept as-is`); }
                stream.markdown(`- ${vlContexts.length} file(s) optimized (${parts.join(', ')})\n`);
                stream.markdown(`- **${totalSaved} tokens saved** (${savingsPercent}% reduction)\n`);
                stream.markdown(`- Original: ${this.totalOriginalTokens} tokens → Optimized: ${this.totalVLTokens} tokens\n`);
                
                if (isMonitoringMode) {
                    // Monitoring mode: show potential savings
                    const monthlySavings = (totalSaved * 0.003 * 100).toFixed(2); // Assume 100 requests/month
                    stream.markdown(`\n💡 **Potential Monthly Savings:** $${monthlySavings} _(based on 100 similar requests)_\n`);
                    stream.markdown(`\n_Upgrade to Premium to activate real-time optimization with Claude API_\n`);
                    stream.markdown(`→ Add your Anthropic API key in settings: \`vl.claude.apiKey\`\n\n`);
                } else {
                    stream.markdown(`\n✅ **Real-time optimization active**\n\n`);
                }
                
                this.logger.info('Chat request optimized with VL', {
                    mode: isMonitoringMode ? 'monitoring' : 'active',
                    files: vlContexts.length,
                    savedTokens: totalSaved,
                    savingsPercent: savingsPercent + '%'
                });
            }
            
            // Build optimized prompt with VL context
            const optimizedPrompt = this.buildOptimizedPrompt(request.prompt, vlContexts);
            
            if (isMonitoringMode) {
                // MONITORING MODE: Just show what we'd do, don't call API
                stream.markdown('---\n\n');
                stream.markdown('**📋 VL Conversion Preview** _(Monitoring Mode)_\n\n');
                
                if (debugEnabled && vlContexts.length > 0) {
                    const preview = vlContexts[0].vlContent.substring(0, 300);
                    const fence = vlContexts[0].format === 'vl' ? 'vl' : vlContexts[0].language;
                    stream.markdown('```' + fence + '\n' + preview + '...\n```\n\n');
                }
                
                stream.markdown('**What would happen in Premium mode:**\n');
                stream.markdown('1. ✅ VL context sent to Claude API (with 90% cached discount)\n');
                stream.markdown('2. ✅ Receive AI-powered response\n');
                stream.markdown('3. ✅ Automatic code generation in target language\n\n');
                
                stream.markdown('**Current mode:** Monitoring only - passing request to default Copilot\n\n');
                stream.markdown('_Want real optimization?_ [Get Premium](https://vl-lang.dev/pricing) or add API key in settings.\n');
                
            } else {
                // ACTIVE MODE: Actually call Claude API
                stream.markdown('---\n\n');
                
                if (!this.claudeClient) {
                    stream.markdown('**⚠️ Claude client not initialized**\n\n');
                    stream.markdown('Please restart VS Code to enable Claude integration.\n');
                    return;
                }
                
                stream.markdown('**⚡ Processing with Claude API...**\n\n');
                
                try {
                    // Build the full prompt with user request + optimized context.
                    // Plain Python (minified or original) needs no VL framing.
                    const targetLanguage = vlContexts[0]?.language || 'python';
                    const contextBlocks = vlContexts.map(c => {
                        if (c.format === 'vl') {
                            return `Context (in VL format for efficiency):\n\`\`\`vl\n${c.vlContent}\n\`\`\``;
                        }
                        return `Context:\n\`\`\`${c.language}\n${c.vlContent}\n\`\`\``;
                    });
                    // Pick the API context format: VL needs its full spec,
                    // v2 needs the small macro spec, plain needs none.
                    const hasVL = vlContexts.some(c => c.format === 'vl');
                    const v2Spec = vlContexts.find(c => c.format === 'v2')?.spec;
                    const apiFormat: 'vl' | 'v2' | 'plain' = hasVL ? 'vl' : (v2Spec ? 'v2' : 'plain');
                    if (hasVL && v2Spec) {
                        // Mixed formats (auto mode): VL spec goes in the system
                        // prompt, so inline the small v2 spec here.
                        contextBlocks.unshift(`Some context uses VL v2 macros:\n${v2Spec}`);
                    }
                    const fullPrompt = `${request.prompt}\n\n${contextBlocks.join('\n\n')}`;
                    
                    // Calculate what we would have sent without VL
                    const originalChars = vlContexts.reduce((sum, c) => sum + c.originalContent.length, 0);
                    const vlChars = vlContexts.reduce((sum, c) => sum + c.vlContent.length, 0);
                    
                    this.logger.debug('Sending to Claude', { 
                        promptLength: fullPrompt.length,
                        targetLanguage 
                    });
                    
                    // Call Claude with the optimized context
                    const response = await this.claudeClient.generateCompletion(
                        fullPrompt,
                        targetLanguage as 'python' | 'javascript' | 'typescript',
                        { format: apiFormat, spec: v2Spec }
                    );
                    
                    // Get actual usage from Claude
                    const usage = this.claudeClient.getLastUsage();
                    
                    if (response) {
                        stream.markdown('**Claude Response:**\n\n');
                        stream.markdown(response);
                        
                        // Extract code blocks and add apply buttons
                        const codeBlocks = this.extractCodeBlocks(response);
                        if (codeBlocks.length > 0 && vlContexts.length > 0) {
                            stream.markdown('\n\n---\n');
                            stream.markdown('**💡 Quick Actions:**\n');
                            
                            for (let i = 0; i < codeBlocks.length; i++) {
                                const block = codeBlocks[i];
                                const targetFile = vlContexts[0].originalContent; // File we're working with
                                
                                stream.button({
                                    command: 'vl.applyCodeFromChat',
                                    title: `📝 Apply ${block.language} code (Block ${i + 1})`,
                                    arguments: [
                                        block.code,
                                        vlContexts[0].language,
                                        request.prompt
                                    ]
                                });
                            }
                        }
                        
                        stream.markdown('\n\n---\n');
                        
                        // Show accurate cost breakdown
                        if (usage) {
                            const vlSpecTokens = usage.cacheRead || usage.cacheCreation;
                            const actualInputTokens = usage.inputTokens;
                            const cacheDiscount = usage.cacheRead > 0 ? '90%' : '0%';
                            
                            // What it would have cost without VL (raw Python + no caching)
                            const hypotheticalTokens = Math.ceil(originalChars / 4) + vlSpecTokens; // Would need to explain VL anyway
                            const withoutVL = Math.ceil(originalChars / 4); // Just raw Python, no VL spec needed
                            
                            stream.markdown(`\n**📊 Actual Claude Usage:**\n`);
                            stream.markdown(`- Input tokens: **${actualInputTokens}** (VL-compressed)\n`);
                            stream.markdown(`- Output tokens: ${usage.outputTokens}\n`);
                            stream.markdown(`- Cache: ${usage.cacheRead > 0 ? `✅ HIT (${usage.cacheRead} tokens @ ${cacheDiscount} off)` : `❌ MISS (building cache)`}\n`);
                            stream.markdown(`\n**💰 Cost Comparison:**\n`);
                            stream.markdown(`- Without VL: ~${withoutVL} tokens\n`);
                            stream.markdown(`- With VL: ${actualInputTokens} tokens ${usage.cacheRead > 0 ? `(${usage.cacheRead} cached)` : ''}\n`);
                            
                            // Calculate actual savings
                            if (usage.cacheRead > 0) {
                                // After cache: VL context + cached spec at 90% off
                                const effectiveTokens = actualInputTokens - usage.cacheRead + (usage.cacheRead * 0.1);
                                const savings = ((withoutVL - effectiveTokens) / withoutVL * 100).toFixed(1);
                                stream.markdown(`- **Effective cost: ~${Math.round(effectiveTokens)} tokens (${savings}% savings)**\n`);
                            }
                        } else {
                            stream.markdown(`_✅ Processed with VL optimization (${totalSaved} estimated tokens saved)_\n`);
                        }
                    } else {
                        stream.markdown('**⚠️ No response from Claude**\n\n');
                        stream.markdown('The API returned an empty response. Please try again.\n');
                    }
                    
                } catch (apiError: any) {
                    this.logger.error('Claude API call failed', apiError);
                    stream.markdown(`**❌ Claude API Error**\n\n`);
                    stream.markdown(`${apiError.message || 'Unknown error'}\n\n`);
                    stream.markdown('_Falling back - please use Copilot for this request_\n');
                }
            }
            
        } catch (error) {
            this.logger.error('Chat participant error', error);
            stream.markdown('*VL optimization error - falling back to default agent*\n\n');
        }
    }
    
    /**
     * Extract file contexts from chat request
     */
    private async extractFileContexts(
        request: vscode.ChatRequest,
        context: vscode.ChatContext
    ): Promise<Array<{ content: string; language: string; file: string }>> {
        const fileContexts: Array<{ content: string; language: string; file: string }> = [];
        
        const config = vscode.workspace.getConfiguration('vl');
        const debugEnabled = config.get<boolean>('debug.enabled', false);
        
        // Check for file references in the request
        if (debugEnabled) {
            this.logger.debug('Chat request references', { count: request.references.length });
        }
        
        for (const ref of request.references) {
            if (debugEnabled) {
                this.logger.debug('Processing reference', { 
                    id: ref.id, 
                    valueType: typeof ref.value,
                    isUri: ref.value instanceof vscode.Uri 
                });
            }
            
            // Handle explicit file references (e.g., #file:test.py in chat)
            if (ref.id.startsWith('file://') || ref.value instanceof vscode.Uri) {
                const uri = ref.value instanceof vscode.Uri ? ref.value : vscode.Uri.parse(ref.id);
                
                try {
                    const document = await vscode.workspace.openTextDocument(uri);
                    const content = document.getText();
                    
                    if (debugEnabled) {
                        this.logger.debug('Extracted file content', {
                            file: uri.fsPath,
                            language: document.languageId,
                            contentLength: content.length,
                            lineCount: document.lineCount
                        });
                    }
                    
                    // Only process supported languages
                    if (['python', 'javascript', 'typescript'].includes(document.languageId)) {
                        fileContexts.push({
                            content,
                            language: document.languageId,
                            file: uri.fsPath
                        });
                    }
                } catch (error) {
                    if (debugEnabled) {
                        this.logger.warn('Failed to open file from reference', { uri: uri.toString(), error });
                    }
                }
                continue;
            }
            
            // Handle legacy file references
            if (ref.id === 'vscode.file' && ref.value instanceof vscode.Uri) {
                const uri = ref.value;
                const document = await vscode.workspace.openTextDocument(uri);
                const content = document.getText();
                
                if (debugEnabled) {
                    this.logger.debug('Extracted file content (legacy)', {
                        file: uri.fsPath,
                        language: document.languageId,
                        contentLength: content.length,
                        lineCount: document.lineCount
                    });
                }
                
                // Only process supported languages
                if (['python', 'javascript', 'typescript'].includes(document.languageId)) {
                    fileContexts.push({
                        content,
                        language: document.languageId,
                        file: uri.fsPath
                    });
                }
                continue;
            }
            
            // Handle implicit selection references
            if (ref.id === 'vscode.implicit.selection') {
                const editor = vscode.window.activeTextEditor;
                if (editor && ['python', 'javascript', 'typescript'].includes(editor.document.languageId)) {
                    // For VL optimization, we want the FULL file context, not just selection
                    // The LLM needs to understand the full codebase to provide good suggestions
                    const content = editor.document.getText(); // Full document, not selection
                    
                    if (debugEnabled) {
                        this.logger.debug('Extracted full file from implicit selection', {
                            file: editor.document.uri.fsPath,
                            language: editor.document.languageId,
                            contentLength: content.length,
                            lineCount: editor.document.lineCount,
                            selectionLength: editor.document.getText(editor.selection).length
                        });
                    }
                    
                    fileContexts.push({
                        content,
                        language: editor.document.languageId,
                        file: editor.document.uri.fsPath
                    });
                }
            }
        }
        
        // If no explicit references, check active editor
        if (fileContexts.length === 0) {
            if (debugEnabled) {
                this.logger.debug('No file references found, checking active editor');
            }
            
            const editor = vscode.window.activeTextEditor;
            if (editor && ['python', 'javascript', 'typescript'].includes(editor.document.languageId)) {
                // Get selected text or full document
                const selection = editor.selection;
                const content = selection.isEmpty 
                    ? editor.document.getText()
                    : editor.document.getText(selection);
                
                if (debugEnabled) {
                    this.logger.debug('Extracted from active editor', {
                        file: editor.document.uri.fsPath,
                        language: editor.document.languageId,
                        contentLength: content.length,
                        lineCount: editor.document.lineCount,
                        hasSelection: !selection.isEmpty
                    });
                }
                
                fileContexts.push({
                    content,
                    language: editor.document.languageId,
                    file: editor.document.uri.fsPath
                });
            }
        }
        
        if (debugEnabled) {
            this.logger.debug('File context extraction complete', { fileCount: fileContexts.length });
        }
        
        return fileContexts;
    }
    
    /**
     * Extract code blocks from markdown response
     */
    private extractCodeBlocks(markdown: string): Array<{ language: string; code: string }> {
        const blocks: Array<{ language: string; code: string }> = [];
        const regex = /```(\w+)?\n([\s\S]*?)```/g;
        let match;
        
        while ((match = regex.exec(markdown)) !== null) {
            blocks.push({
                language: match[1] || 'text',
                code: match[2].trim()
            });
        }
        
        return blocks;
    }
    
    /**
     * Build optimized prompt with VL context
     */
    private buildOptimizedPrompt(userPrompt: string, vlContexts: ChatContext[]): string {
        let prompt = `User Request: ${userPrompt}\n\n`;

        prompt += `Context (optimized for token efficiency):\n\n`;

        for (let i = 0; i < vlContexts.length; i++) {
            const ctx = vlContexts[i];
            const fence = ctx.format === 'vl' ? 'vl' : ctx.language;
            prompt += `File ${i + 1} (${ctx.language}):\n`;
            prompt += `\`\`\`${fence}\n${ctx.vlContent}\n\`\`\`\n\n`;
        }

        prompt += `Please analyze the code above and respond to the user's request.\n`;
        prompt += `Generate your response in ${vlContexts[0]?.language || 'the target language'}.\n`;

        return prompt;
    }
    
    /**
     * Get statistics
     */
    getStats() {
        return {
            requestCount: this.requestCount,
            totalOriginalTokens: this.totalOriginalTokens,
            totalVLTokens: this.totalVLTokens,
            totalSaved: this.totalOriginalTokens - this.totalVLTokens,
            savingsPercent: this.totalOriginalTokens > 0
                ? ((this.totalOriginalTokens - this.totalVLTokens) / this.totalOriginalTokens * 100).toFixed(1)
                : '0.0'
        };
    }
    
    /**
     * Reset statistics
     */
    resetStats() {
        this.requestCount = 0;
        this.totalOriginalTokens = 0;
        this.totalVLTokens = 0;
    }
}
