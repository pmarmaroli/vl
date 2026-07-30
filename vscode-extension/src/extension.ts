/**
 * VL (Very Little) AI Cost Optimizer - VS Code Extension
 *
 * Main extension entry point. Activates transparent mode to automatically
 * optimize AI coding assistant requests (semantic minification and VL v2
 * macro compression - measured 20-30% typical token savings).
 */

import * as vscode from 'vscode';
import { TokenSavingsStatusBar } from './ui/statusBar';
import { AnalyticsDashboard } from './ui/dashboard';
import { TransparentModeManager } from './transparent-mode/manager';
import { VLConverter } from './converter/vlConverter';
import { Logger } from './utils/logger';
import { estimateTokens } from './utils/tokenEstimator';
import { AnalyticsTracker } from './analytics/analyticsTracker';

let statusBar: TokenSavingsStatusBar;
let transparentMode: TransparentModeManager;
let logger: Logger;
let analytics: AnalyticsTracker;

export function activate(context: vscode.ExtensionContext) {
    logger = new Logger();
    logger.info('VL AI Cost Optimizer activating...');
    
    // Initialize components
    analytics = new AnalyticsTracker(context);
    statusBar = new TokenSavingsStatusBar(context);
    const converter = new VLConverter(context, logger);
    const dashboard = new AnalyticsDashboard(context, analytics);
    
    // IMPORTANT: Always create and activate transparent mode manager
    // The chat participant MUST be registered during activation for VS Code to recognize it
    // The manager will handle whether features are enabled/disabled internally
    transparentMode = new TransparentModeManager(context, converter, statusBar, logger, analytics);
    transparentMode.activate();
    logger.info('Transparent mode manager initialized');
    
    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('vl.setApiKey', async () => {
            const key = await transparentMode.getClaudeClient().promptForApiKey();
            if (key) {
                vscode.window.showInformationMessage('Anthropic API key saved to secure storage.');
            }
        }),

        vscode.commands.registerCommand('vl.showDashboard', () => {
            dashboard.show();
        }),
        
        vscode.commands.registerCommand('vl.toggleTransparentMode', async () => {
            await toggleTransparentMode(context, converter, statusBar);
        }),
        
        vscode.commands.registerCommand('vl.resetStats', () => {
            statusBar.reset();
            vscode.window.showInformationMessage('VL statistics reset');
        }),
        
        vscode.commands.registerCommand('vl.applyCodeFromChat', async (code: string, language: string, context: string) => {
            await applyCodeFromChat(code, language, context);
        }),
        
        vscode.commands.registerCommand('vl.minifyCurrentFile', async () => {
            await minifyCurrentFile(converter);
        }),

        vscode.commands.registerCommand('vl.showOutput', () => {
            logger.show();
        }),
        
        vscode.commands.registerCommand('vl.showStats', () => {
            if (transparentMode) {
                const stats = transparentMode.getStats();
                const chatStats = stats.chat;
                const cacheStats = stats.cache;
                
                const message = [
                    `📊 VL Statistics:`,
                    ``,
                    `Chat/Agent Optimization:`,
                    `• Requests optimized: ${chatStats.requestCount}`,
                    `• Tokens original: ${chatStats.totalOriginalTokens}`,
                    `• Tokens VL: ${chatStats.totalVLTokens}`,
                    `• Tokens saved: ${chatStats.totalSaved}`,
                    `• Savings: ${chatStats.savingsPercent}%`,
                    ``,
                    `Claude Cache:`,
                    `• Cache hits: ${cacheStats.cacheReads}`,
                    `• Spec tokens cached: ${cacheStats.specTokensSaved}`,
                    `• Cache savings: $${cacheStats.dollarsSavedFromCache.toFixed(4)}`
                ].join('\n');
                
                vscode.window.showInformationMessage(message, 'View Dashboard', 'Reset Stats').then(selection => {
                    if (selection === 'View Dashboard') {
                        vscode.commands.executeCommand('vl.showDashboard');
                    } else if (selection === 'Reset Stats') {
                        vscode.commands.executeCommand('vl.resetStats');
                    }
                });
            } else {
                vscode.window.showInformationMessage('Transparent mode not active');
            }
        })
    );
    
    // Show welcome message on first install
    const hasShownWelcome = context.globalState.get('vl.hasShownWelcome', false);
    if (!hasShownWelcome) {
        showWelcomeMessage(context);
    }
    
    logger.info('VL AI Cost Optimizer activated successfully');
}

export function deactivate() {
    logger?.info('VL AI Cost Optimizer deactivating');
    
    if (transparentMode) {
        transparentMode.deactivate();
    }
}

async function toggleTransparentMode(
    context: vscode.ExtensionContext,
    converter: VLConverter,
    statusBar: TokenSavingsStatusBar
) {
    const config = vscode.workspace.getConfiguration('vl');
    const currentState = config.get<boolean>('transparentMode.enabled', true);
    
    await config.update('transparentMode.enabled', !currentState, vscode.ConfigurationTarget.Global);
    
    if (!currentState) {
        // Enabling
        if (!transparentMode) {
            transparentMode = new TransparentModeManager(context, converter, statusBar, logger, analytics);
        }
        transparentMode.activate();
        vscode.window.showInformationMessage('✅ VL Transparent Mode: ON - Saving tokens automatically');
    } else {
        // Disabling
        if (transparentMode) {
            transparentMode.deactivate();
        }
        vscode.window.showInformationMessage('⏸️ VL Transparent Mode: OFF');
    }
}

async function minifyCurrentFile(converter: VLConverter) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor');
        return;
    }

    const document = editor.document;
    const language = document.languageId;

    if (language !== 'python') {
        vscode.window.showWarningMessage(`VL minification not yet supported for ${language}`);
        return;
    }

    const code = document.getText();

    try {
        const result = await converter.optimize(code, 'python');

        // Create new untitled document with the optimized code
        const doc = await vscode.workspace.openTextDocument({
            language: 'python',
            content: result.content
        });

        await vscode.window.showTextDocument(doc);

        const savings = result.originalTokens > 0
            ? ((result.originalTokens - result.optimizedTokens) / result.originalTokens * 100).toFixed(1)
            : '0.0';

        vscode.window.showInformationMessage(
            `✅ Optimized (${result.format}): ${result.originalTokens} → ${result.optimizedTokens} tokens (${savings}% savings)`
        );
    } catch (error) {
        vscode.window.showErrorMessage(`Optimization failed: ${error}`);
        logger.error('Optimization error', error);
    }
}

async function applyCodeFromChat(code: string, language: string, contextPrompt: string) {
    const editor = vscode.window.activeTextEditor;
    
    if (!editor) {
        vscode.window.showErrorMessage('No active editor to apply code to');
        return;
    }
    
    // Check if the language matches
    if (editor.document.languageId !== language && language !== 'text') {
        const proceed = await vscode.window.showWarningMessage(
            `Apply ${language} code to ${editor.document.languageId} file?`,
            'Apply Anyway',
            'Cancel'
        );
        if (proceed !== 'Apply Anyway') {
            return;
        }
    }
    
    // Ask user how to apply
    const action = await vscode.window.showQuickPick([
        { label: '📝 Replace entire file', value: 'replace' },
        { label: '➕ Insert at cursor', value: 'insert' },
        { label: '📋 Copy to clipboard', value: 'copy' }
    ], {
        placeHolder: 'How would you like to apply this code?'
    });
    
    if (!action) return;
    
    switch (action.value) {
        case 'replace':
            const fullRange = new vscode.Range(
                editor.document.positionAt(0),
                editor.document.positionAt(editor.document.getText().length)
            );
            await editor.edit(editBuilder => {
                editBuilder.replace(fullRange, code);
            });
            vscode.window.showInformationMessage('✅ Code applied to file');
            break;
            
        case 'insert':
            await editor.edit(editBuilder => {
                editBuilder.insert(editor.selection.active, code);
            });
            vscode.window.showInformationMessage('✅ Code inserted at cursor');
            break;
            
        case 'copy':
            await vscode.env.clipboard.writeText(code);
            vscode.window.showInformationMessage('✅ Code copied to clipboard');
            break;
    }
}

function showWelcomeMessage(context: vscode.ExtensionContext) {
    const message = '🎉 VL AI Cost Optimizer installed! Start saving 45% on AI coding costs automatically.';
    const actions = ['Show Dashboard', 'Learn More', 'Settings'];
    
    vscode.window.showInformationMessage(message, ...actions).then(selection => {
        if (selection === 'Show Dashboard') {
            vscode.commands.executeCommand('vl.showDashboard');
        } else if (selection === 'Learn More') {
            vscode.env.openExternal(vscode.Uri.parse('https://github.com/pmarmaroli/vl'));
        } else if (selection === 'Settings') {
            vscode.commands.executeCommand('workbench.action.openSettings', 'vl');
        }
    });
    
    context.globalState.update('vl.hasShownWelcome', true);
}

function estimateTokenCount(text: string): number {
    // Use calibrated model (2.58 chars/token for Claude)
    return estimateTokens(text);
}
