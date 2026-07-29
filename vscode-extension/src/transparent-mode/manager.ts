/**
 * Transparent Mode Manager
 * 
 * Handles automatic interception and optimization of AI coding assistant requests.
 * Currently a placeholder for future Copilot/Cursor integration.
 */

import * as vscode from 'vscode';
import { VLConverter } from '../converter/vlConverter';
import { TokenSavingsStatusBar } from '../ui/statusBar';
import { Logger } from '../utils/logger';
import { VLChatParticipant } from './chatParticipant';
import { ClaudeClient } from './claudeClient';
import { estimateTokens } from '../utils/tokenEstimator';
import { AnalyticsTracker } from '../analytics/analyticsTracker';

export class TransparentModeManager {
    private isActive: boolean = false;
    private chatParticipant: VLChatParticipant | null = null;
    private claudeClient: ClaudeClient;
    
    constructor(
        private context: vscode.ExtensionContext,
        private converter: VLConverter,
        private statusBar: TokenSavingsStatusBar,
        private logger: Logger,
        private analytics: AnalyticsTracker
    ) {
        this.claudeClient = new ClaudeClient(logger, context.secrets);
    }
    
    async activate() {
        // IMPORTANT: Always register chat participant regardless of settings
        // VS Code requires chat participants to be registered during activation
        this.chatParticipant = VLChatParticipant.register(
            this.context,
            this.converter,
            this.statusBar,
            this.logger,
            this.analytics,
            this.claudeClient  // Pass Claude client for Active mode
        );
        
        this.logger.info('VL Chat Participant registered (required for VS Code)');
        
        // Check if transparent mode features are enabled
        const config = vscode.workspace.getConfiguration('vl');
        const isEnabled = config.get<boolean>('transparentMode.enabled', true);
        
        if (!isEnabled) {
            this.isActive = false;
            this.logger.info('Transparent mode disabled in settings (chat participant still available)');
            return; // Exit early - features disabled but chat participant is registered
        }
        
        this.isActive = true;
        this.logger.info('Transparent mode: Active - Monitoring chat/agent requests');
        
        // Warm cache on startup if enabled
        const warmCache = config.get<boolean>('claude.warmCacheOnStartup', true);
        const claudeEnabled = config.get<boolean>('claude.enableCompletions', false);
        
        if (claudeEnabled && warmCache) {
            // Warm cache in background (don't await)
            this.claudeClient.warmCache().then(success => {
                if (success) {
                    this.logger.info('✅ Claude cache pre-warmed for fast completions');
                }
            });
        }
        
        // Show appropriate message based on configuration
        const debugEnabled = config.get<boolean>('debug.enabled', false);
        
        if (debugEnabled) {
            vscode.window.showInformationMessage(
                '🔄 VL Transparent Mode: Monitoring (Debug mode enabled)',
                'View Output'
            ).then(selection => {
                if (selection === 'View Output') {
                    vscode.commands.executeCommand('vl.showOutput');
                }
            });
        } else if (claudeEnabled) {
            vscode.window.showInformationMessage(
                '✅ VL Transparent Mode: Active with Claude completions'
            );
        } else {
            vscode.window.showInformationMessage(
                '✅ VL Transparent Mode: Active - Tracking token savings'
            );
        }
    }
    
    deactivate() {
        this.isActive = false;
        
        if (this.chatParticipant) {
            const stats = this.chatParticipant.getStats();
            this.logger.info('Chat participant statistics', stats);
        }
        
        // Log cache statistics
        const cacheStats = this.claudeClient.getStats();
        if (cacheStats.cacheReads > 0) {
            this.logger.info('Claude cache statistics', {
                cacheHits: cacheStats.cacheReads,
                tokensSaved: cacheStats.specTokensSaved,
                dollarsSaved: `$${cacheStats.dollarsSavedFromCache.toFixed(4)}`
            });
        }
        
        this.logger.info('Transparent mode manager deactivated');
    }
    
    /**
     * Get current statistics
     */
    getStats() {
        const chatStats = this.chatParticipant 
            ? this.chatParticipant.getStats() 
            : {
                requestCount: 0,
                totalOriginalTokens: 0,
                totalVLTokens: 0,
                totalSaved: 0,
                savingsPercent: '0.0'
            };
            
        const cacheStats = this.claudeClient.getStats();
        
        return {
            chat: chatStats,
            cache: cacheStats,
            combined: {
                requestCount: chatStats.requestCount,
                tokensOriginal: chatStats.totalOriginalTokens,
                tokensVL: chatStats.totalVLTokens,
                tokensSaved: parseInt(chatStats.totalSaved as any),
                savingsPercent: chatStats.savingsPercent,
                cacheHits: cacheStats.cacheReads,
                cacheMisses: cacheStats.cacheMisses
            }
        };
    }
    
    /**
     * Get Claude client (for commands)
     */
    getClaudeClient(): ClaudeClient {
        return this.claudeClient;
    }
    
    /**
     * Simulate token optimization (for testing/demo)
     * In production, this would intercept real Copilot requests
     */
    async simulateOptimization(code: string, language: string): Promise<string> {
        if (!this.isActive) {
            return code;
        }
        
        try {
            // Optimize (minify | vl | auto per settings)
            const optimized = await this.converter.optimize(
                code,
                language as 'python' | 'javascript' | 'typescript'
            );

            // Track savings
            this.statusBar.recordSavings(optimized.originalTokens, optimized.optimizedTokens);

            this.logger.debug('Simulated optimization', {
                language,
                format: optimized.format,
                originalTokens: optimized.originalTokens,
                optimizedTokens: optimized.optimizedTokens,
                savings: ((optimized.originalTokens - optimized.optimizedTokens) / optimized.originalTokens * 100).toFixed(1) + '%'
            });

            return optimized.content;
        } catch (error) {
            this.logger.error('Optimization failed', error);
            return code; // Return original on error
        }
    }
    
    private estimateTokens(text: string): number {
        // Use calibrated model (2.58 chars/token for Claude)
        return estimateTokens(text);
    }
}

/**
 * Future implementation notes:
 * 
 * To implement actual Copilot interception, we need to:
 * 
 * 1. Register as inline completion provider:
 *    vscode.languages.registerInlineCompletionItemProvider(['python', 'javascript'], {
 *        provideInlineCompletionItems: async (document, position, context) => {
 *            // Get surrounding context
 *            // Convert to VL
 *            // Let Copilot process VL context
 *            // Convert result back
 *        }
 *    })
 * 
 * 2. Or use Language Server Protocol:
 *    - Create LSP proxy that sits between VS Code and Python/JS language servers
 *    - Intercept completion requests
 *    - Convert context to VL before forwarding
 *    - Convert responses back
 * 
 * 3. Or wait for VS Code AI Extension API:
 *    - Microsoft is working on official APIs for AI extensions
 *    - This would provide proper hooks for Copilot integration
 * 
 * Current limitation: VS Code doesn't expose direct Copilot API hooks yet.
 * We'll need to use workarounds or wait for official API support.
 */
