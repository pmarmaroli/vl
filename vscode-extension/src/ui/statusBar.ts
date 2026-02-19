/**
 * Token Savings Status Bar
 * Displays real-time token and cost savings in VS Code status bar
 */

import * as vscode from 'vscode';

interface SavingsStats {
    totalOriginalTokens: number;
    totalOptimizedTokens: number;
    requestCount: number;
}

export class TokenSavingsStatusBar {
    private statusBarItem: vscode.StatusBarItem;
    private stats: SavingsStats;
    private storageKey = 'vl.savingsStats';
    
    constructor(private context: vscode.ExtensionContext) {
        // Create status bar item
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'vl.showDashboard';
        
        // Load saved stats
        this.stats = context.globalState.get<SavingsStats>(this.storageKey, {
            totalOriginalTokens: 0,
            totalOptimizedTokens: 0,
            requestCount: 0
        });
        
        // Check if status bar should be shown
        const config = vscode.workspace.getConfiguration('vl');
        const showStatusBar = config.get<boolean>('analytics.showStatusBar', true);
        
        if (showStatusBar) {
            this.statusBarItem.show();
        }
        
        this.update();
        
        // Watch for config changes
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('vl.analytics.showStatusBar')) {
                const config = vscode.workspace.getConfiguration('vl');
                const show = config.get<boolean>('analytics.showStatusBar', true);
                if (show) {
                    this.statusBarItem.show();
                } else {
                    this.statusBarItem.hide();
                }
            }
        });
        
        context.subscriptions.push(this.statusBarItem);
    }
    
    /**
     * Record token savings from a conversion
     */
    recordSavings(originalTokens: number, optimizedTokens: number) {
        this.stats.totalOriginalTokens += originalTokens;
        this.stats.totalOptimizedTokens += optimizedTokens;
        this.stats.requestCount++;
        
        this.save();
        this.update();
        
        // Show notification for significant savings
        const config = vscode.workspace.getConfiguration('vl');
        const showNotifications = config.get<boolean>('analytics.showNotifications', false);
        
        if (showNotifications && originalTokens > 1000) {
            const savings = ((originalTokens - optimizedTokens) / originalTokens * 100).toFixed(1);
            vscode.window.showInformationMessage(
                `💰 VL saved ${savings}% tokens (${originalTokens} → ${optimizedTokens})`
            );
        }
    }
    
    /**
     * Reset all statistics
     */
    reset() {
        this.stats = {
            totalOriginalTokens: 0,
            totalOptimizedTokens: 0,
            requestCount: 0
        };
        this.save();
        this.update();
    }
    
    /**
     * Get current statistics
     */
    getStats(): SavingsStats {
        return { ...this.stats };
    }
    
    /**
     * Update status bar display
     */
    private update() {
        if (this.stats.requestCount === 0) {
            this.statusBarItem.text = '$(zap) VL: Ready';
            this.statusBarItem.tooltip = 'VL Cost Optimizer\nClick to view dashboard';
            return;
        }
        
        const saved = this.stats.totalOriginalTokens - this.stats.totalOptimizedTokens;
        const percent = ((saved / this.stats.totalOriginalTokens) * 100).toFixed(1);
        
        // Estimate cost savings (rough estimate: $0.03 per 1K tokens)
        const dollarsSaved = (saved / 1000 * 0.03).toFixed(2);
        
        this.statusBarItem.text = `$(zap) VL: ${percent}% ($${dollarsSaved})`;
        this.statusBarItem.tooltip = this.buildTooltip(saved, percent, dollarsSaved);
    }
    
    private buildTooltip(saved: number, percent: string, dollars: string): string {
        const lines = [
            '💰 VL Cost Savings',
            '',
            `Tokens: ${this.formatNumber(this.stats.totalOriginalTokens)} → ${this.formatNumber(this.stats.totalOptimizedTokens)}`,
            `Saved: ${this.formatNumber(saved)} tokens (${percent}%)`,
            `Cost savings: $${dollars}`,
            `Requests optimized: ${this.stats.requestCount}`,
            '',
            'Click to view dashboard'
        ];
        return lines.join('\n');
    }
    
    private formatNumber(num: number): string {
        return num.toLocaleString();
    }
    
    private save() {
        this.context.globalState.update(this.storageKey, this.stats);
    }
}
