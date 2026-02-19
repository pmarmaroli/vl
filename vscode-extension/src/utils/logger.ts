/**
 * Logger utility for VL extension
 */

import * as vscode from 'vscode';

export class Logger {
    private outputChannel: vscode.OutputChannel;
    private debugEnabled: boolean = false;
    
    constructor() {
        this.outputChannel = vscode.window.createOutputChannel('VL Cost Optimizer');
        this.updateDebugSetting();
        
        // Watch for config changes
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('vl.debug.enabled')) {
                this.updateDebugSetting();
            }
        });
    }
    
    private updateDebugSetting() {
        const config = vscode.workspace.getConfiguration('vl');
        this.debugEnabled = config.get<boolean>('debug.enabled', false);
    }
    
    info(message: string, ...args: any[]) {
        const formatted = this.format('INFO', message, args);
        this.outputChannel.appendLine(formatted);
        if (this.debugEnabled) {
            console.log(formatted);
        }
    }
    
    error(message: string, error?: any) {
        const formatted = this.format('ERROR', message, error ? [error] : []);
        this.outputChannel.appendLine(formatted);
        console.error(formatted, error);
    }
    
    warn(message: string, ...args: any[]) {
        const formatted = this.format('WARN', message, args);
        this.outputChannel.appendLine(formatted);
        if (this.debugEnabled) {
            console.warn(formatted);
        }
    }
    
    debug(message: string, ...args: any[]) {
        if (!this.debugEnabled) {
            return;
        }
        const formatted = this.format('DEBUG', message, args);
        this.outputChannel.appendLine(formatted);
        console.log(formatted);
    }
    
    show() {
        this.outputChannel.show();
    }
    
    private format(level: string, message: string, args: any[]): string {
        const timestamp = new Date().toISOString();
        const argsStr = args.length > 0 ? ' ' + JSON.stringify(args) : '';
        return `[${timestamp}] [${level}] ${message}${argsStr}`;
    }
}
