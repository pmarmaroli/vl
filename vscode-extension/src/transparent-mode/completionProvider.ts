/**
 * VL Inline Completion Provider
 * 
 * Proof of concept for intercepting code completion requests.
 * This provider runs alongside GitHub Copilot and can:
 * 1. Monitor what context is being sent to AI
 * 2. Estimate token usage
 * 3. Calculate potential VL savings
 * 4. Optionally provide VL-optimized completions
 */

import * as vscode from 'vscode';
import { VLConverter } from '../converter/vlConverter';
import { TokenSavingsStatusBar } from '../ui/statusBar';
import { Logger } from '../utils/logger';
import { ClaudeClient } from './claudeClient';
import { estimateTokens } from '../utils/tokenEstimator';

export class VLCompletionProvider implements vscode.InlineCompletionItemProvider {
    private requestCount: number = 0;
    
    constructor(
        private converter: VLConverter,
        private statusBar: TokenSavingsStatusBar,
        private logger: Logger,
        private claudeClient?: ClaudeClient
    ) {}
    
    async provideInlineCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        context: vscode.InlineCompletionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[] | vscode.InlineCompletionList | null> {
        
        this.requestCount++;
        
        // Get configuration
        const config = vscode.workspace.getConfiguration('vl');
        const debugEnabled = config.get<boolean>('debug.enabled', false);
        
        try {
            // Get surrounding code context (what would be sent to Copilot)
            const context = this.getSurroundingContext(document, position);
            
            if (debugEnabled) {
                this.logger.debug('Completion request detected', {
                    requestNumber: this.requestCount,
                    position: `${position.line}:${position.character}`,
                    contextLength: context.length,
                    language: document.languageId
                });
            }
            
            // Only process Python/JavaScript files
            if (!['python', 'javascript', 'typescript'].includes(document.languageId)) {
                return null;
            }
            
            // Estimate original token count using calibrated model
            const originalTokens = estimateTokens(context, document.languageId);
            
            // Optimize (minify | v2 | auto per settings) to see potential savings
            try {
                const optimized = await this.converter.optimize(
                    context,
                    document.languageId as 'python' | 'javascript' | 'typescript'
                );
                const vlCode = optimized.content;

                const vlTokens = optimized.optimizedTokens;
                const saved = originalTokens - vlTokens;
                const savingsPercent = originalTokens > 0 
                    ? ((saved / originalTokens) * 100).toFixed(1)
                    : '0.0';
                
                // Update status bar with potential savings
                this.statusBar.recordSavings(originalTokens, vlTokens);
                
                if (debugEnabled) {
                    this.logger.info('Token analysis complete', {
                        originalTokens,
                        vlTokens,
                        saved,
                        savingsPercent: savingsPercent + '%'
                    });
                    
                }
                
                // If Claude completions are enabled, generate VL-based completion
                const claudeEnabled = config.get<boolean>('claude.enableCompletions', false);
                if (claudeEnabled && this.claudeClient && vlCode.trim()) {
                    const apiFormat: 'v2' | 'plain' = optimized.format === 'v2' ? 'v2' : 'plain';
                    const completion = await this.claudeClient.generateCompletion(
                        vlCode,
                        document.languageId as 'python' | 'javascript' | 'typescript',
                        { format: apiFormat, spec: optimized.spec }
                    );
                    
                    if (completion) {
                        // Return VL-optimized completion
                        return [{
                            insertText: completion,
                            range: new vscode.Range(position, position)
                        }];
                    }
                }
                
            } catch (conversionError: any) {
                // Only log non-syntax errors (syntax errors are expected mid-typing)
                const isSyntaxError = conversionError?.message && (
                    conversionError.message.includes('Invalid Python syntax') ||
                    conversionError.message.includes('SyntaxError') ||
                    conversionError.message.includes('unexpected indent') ||
                    conversionError.message.includes('expected')
                );
                
                if (debugEnabled && !isSyntaxError) {
                    this.logger.error('VL conversion failed', conversionError);
                }
                // Syntax errors are silently ignored - user is still typing
            }
            
        } catch (error) {
            this.logger.error('Completion provider error', error);
        }
        
        // Return null to let Copilot handle the completion
        // In future versions, we could return VL-optimized completions here
        return null;
    }
    
    /**
     * Get surrounding code context (what Copilot would see)
     * Returns up to 2000 characters before cursor position
     */
    private getSurroundingContext(document: vscode.TextDocument, position: vscode.Position): string {
        // Get text from start of file to cursor position
        const range = new vscode.Range(
            new vscode.Position(0, 0),
            position
        );
        
        const textBeforeCursor = document.getText(range);
        
        // Limit to last 2000 characters (rough approximation of typical context window)
        const maxContextLength = 2000;
        if (textBeforeCursor.length > maxContextLength) {
            return textBeforeCursor.substring(textBeforeCursor.length - maxContextLength);
        }
        
        return textBeforeCursor;
    }
    
    /**
     * Get statistics about interception
     */
    getStats() {
        return {
            requestCount: this.requestCount
        };
    }
    
    /**
     * Reset statistics
     */
    resetStats() {
        this.requestCount = 0;
    }
}

/**
 * Register the completion provider for supported languages
 */
export function registerCompletionProvider(
    context: vscode.ExtensionContext,
    converter: VLConverter,
    statusBar: TokenSavingsStatusBar,
    logger: Logger,
    claudeClient?: ClaudeClient
): VLCompletionProvider {
    
    const provider = new VLCompletionProvider(converter, statusBar, logger, claudeClient);
    
    // Register for Python, JavaScript, and TypeScript
    const disposable = vscode.languages.registerInlineCompletionItemProvider(
        [
            { language: 'python', scheme: 'file' },
            { language: 'javascript', scheme: 'file' },
            { language: 'typescript', scheme: 'file' }
        ],
        provider
    );
    
    context.subscriptions.push(disposable);
    
    logger.info('VL Completion Provider registered for Python, JavaScript, TypeScript');
    
    return provider;
}
