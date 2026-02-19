/**
 * Analytics Dashboard - Webview showing detailed cost savings
 */

import * as vscode from 'vscode';
import { AnalyticsTracker } from '../analytics/analyticsTracker';

export class AnalyticsDashboard {
    private panel: vscode.WebviewPanel | undefined;
    
    constructor(
        private context: vscode.ExtensionContext,
        private analytics: AnalyticsTracker
    ) {}
    
    show() {
        if (this.panel) {
            this.panel.reveal(vscode.ViewColumn.One);
            this.updateContent();
            return;
        }
        
        this.panel = vscode.window.createWebviewPanel(
            'vlDashboard',
            '💰 VL Cost Savings Dashboard',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );
        
        this.updateContent();
        
        this.panel.onDidDispose(() => {
            this.panel = undefined;
        }, null, this.context.subscriptions);
        
        // Handle messages from webview
        this.panel.webview.onDidReceiveMessage(
            async message => {
                switch (message.command) {
                    case 'resetStats':
                        const confirm = await vscode.window.showWarningMessage(
                            'Reset all analytics data? This cannot be undone.',
                            'Reset',
                            'Cancel'
                        );
                        if (confirm === 'Reset') {
                            this.analytics.reset();
                            this.updateContent();
                            vscode.window.showInformationMessage('Analytics data reset');
                        }
                        break;
                    case 'exportCSV':
                        this.exportToCSV();
                        break;
                    case 'refresh':
                        this.updateContent();
                        break;
                    case 'openSettings':
                        vscode.commands.executeCommand('workbench.action.openSettings', 'vl');
                        break;
                }
            },
            undefined,
            this.context.subscriptions
        );
    }
    
    private updateContent(): void {
        if (!this.panel) return;
        const summary = this.analytics.getSummary();
        this.panel.webview.html = this.getHtmlContent(summary);
    }
    
    private async exportToCSV(): Promise<void> {
        const csv = this.analytics.exportToCSV();
        const uri = await vscode.window.showSaveDialog({
            defaultUri: vscode.Uri.file('vl-analytics.csv'),
            filters: {
                'CSV Files': ['csv'],
                'All Files': ['*']
            }
        });
        
        if (uri) {
            await vscode.workspace.fs.writeFile(uri, Buffer.from(csv, 'utf8'));
            vscode.window.showInformationMessage(`Analytics exported to ${uri.fsPath}`);
        }
    }
    
    private getHtmlContent(summary: any): string {
        const hasData = summary.allTime.requestCount > 0;
        
        return `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VL Analytics</title>
    <style>
        body { 
            font-family: var(--vscode-font-family); 
            padding: 20px; 
            color: var(--vscode-foreground);
        }
        h1 { color: var(--vscode-textLink-foreground); margin-bottom: 20px; }
        .actions { margin-bottom: 20px; }
        button {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 8px 16px;
            margin-right: 8px;
            cursor: pointer;
            border-radius: 4px;
        }
        button:hover { background: var(--vscode-button-hoverBackground); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minwidth(250px, 1fr)); gap: 16px; margin: 20px 0; }
        .card {
            background: var(--vscode-sideBar-background);
            border: 1px solid var(--vscode-panel-border);
            padding: 20px;
            border-radius: 6px;
        }
        .card h3 { margin: 0 0 8px 0; font-size: 14px; }
        .metric { font-size: 32px; font-weight: bold; color: var(--vscode-textLink-foreground); }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td { 
            padding: 12px; 
            text-align: left;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        th { font-weight: bold; }
        .no-data { text-align: center; padding: 60px 20px; color: var(--vscode-descriptionForeground); }
    </style>
</head>
<body>
    <h1>💰 VL Cost Savings Dashboard</h1>
    <div class="actions">
        <button onclick="refresh()">🔄 Refresh</button>
        <button onclick="exportCSV()">📊 Export CSV</button>
        <button onclick="reset()">⚠️ Reset Data</button>
    </div>
    
    ${!hasData ? `
        <div class="no-data">
            <h2>📈 No Data Yet</h2>
            <p>Start using @vl in chat to track your token savings!</p>
        </div>
    ` : `
        <div class="grid">
            <div class="card">
                <h3>Today</h3>
                <div class="metric">${this.formatNumber(summary.today.totalSavings)}</div>
                <p>${summary.today.avgSavingsPercent}% avg savings</p>
            </div>
            <div class="card">
                <h3>This Week</h3>
                <div class="metric">${this.formatNumber(summary.thisWeek.totalSavings)}</div>
                <p>${summary.thisWeek.avgSavingsPercent}% avg savings</p>
            </div>
            <div class="card">
                <h3>This Month</h3>
                <div class="metric">${this.formatNumber(summary.thisMonth.totalSavings)}</div>
                <p>${summary.thisMonth.avgSavingsPercent}% avg savings</p>
            </div>
            <div class="card">
                <h3>Projected Annual</h3>
                <div class="metric">${this.formatNumber(summary.projectedAnnualSavings.tokens)}</div>
                <p>~$${summary.projectedAnnualSavings.costAtClaudeAPI}/year</p>
            </div>
        </div>
        
        <h2>🏆 Top Files</h2>
        <table>
            <thead><tr><th>File</th><th>Tokens Saved</th><th>Requests</th></tr></thead>
            <tbody>
                ${summary.topFiles.map((f: any) => `
                    <tr>
                        <td>${this.getFileName(f.file)}</td>
                        <td><strong>${this.formatNumber(f.savings)}</strong></td>
                        <td>${f.count}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        
        <h2>🕐 Recent Activity</h2>
        <table>
            <thead><tr><th>Time</th><th>File</th><th>Saved</th><th>%</th></tr></thead>
            <tbody>
                ${summary.recentRecords.map((r: any) => `
                    <tr>
                        <td>${new Date(r.timestamp).toLocaleString()}</td>
                        <td>${this.getFileName(r.fileName)}</td>
                        <td><strong>${this.formatNumber(r.savedTokens)}</strong></td>
                        <td>${r.savingsPercent.toFixed(1)}%</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `}
    
    <script>
        const vscode = acquireVsCodeApi();
        function refresh() { vscode.postMessage({ command: 'refresh' }); }
        function exportCSV() { vscode.postMessage({ command: 'exportCSV' }); }
        function reset() { vscode.postMessage({ command: 'resetStats' }); }
    </script>
</body>
</html>`;
    }
    
    private formatNumber(num: number): string {
        if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
        if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K';
        return num.toString();
    }
    
    private getFileName(fullPath: string): string {
        return fullPath.split(/[/\\]/).pop() || fullPath;
    }
}
