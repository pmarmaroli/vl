/**
 * Analytics Tracker - Persistent storage for token savings data
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export interface SavingsRecord {
    timestamp: number;
    date: string; // ISO date string
    fileName: string;
    language: string;
    originalTokens: number;
    vlTokens: number;
    savedTokens: number;
    savingsPercent: number;
    mode: 'monitoring' | 'active';
    cacheHit?: boolean;
    cacheTokens?: number;
}

export interface DailySummary {
    date: string;
    totalSavings: number;
    totalOriginal: number;
    totalVL: number;
    requestCount: number;
    avgSavingsPercent: number;
    fileCount: number;
}

export interface AnalyticsSummary {
    today: DailySummary;
    thisWeek: DailySummary;
    thisMonth: DailySummary;
    allTime: DailySummary;
    recentRecords: SavingsRecord[];
    topFiles: Array<{ file: string; savings: number; count: number }>;
    projectedAnnualSavings: {
        tokens: number;
        costAtCopilotPricing: number; // $10/month baseline
        costAtClaudeAPI: number; // ~$3 per 1M tokens
    };
}

export class AnalyticsTracker {
    private records: SavingsRecord[] = [];
    private storageFile: string;
    
    constructor(private context: vscode.ExtensionContext) {
        this.storageFile = path.join(
            context.globalStorageUri.fsPath,
            'vl-analytics.json'
        );
        this.loadRecords();
    }
    
    /**
     * Record a new savings event
     */
    recordSavings(record: Omit<SavingsRecord, 'timestamp' | 'date'>): void {
        const fullRecord: SavingsRecord = {
            ...record,
            timestamp: Date.now(),
            date: new Date().toISOString().split('T')[0], // YYYY-MM-DD
        };
        
        this.records.push(fullRecord);
        this.saveRecords();
    }
    
    /**
     * Get analytics summary
     */
    getSummary(): AnalyticsSummary {
        const now = new Date();
        const today = this.getDateString(now);
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        
        return {
            today: this.getSummaryForPeriod(r => r.date === today),
            thisWeek: this.getSummaryForPeriod(r => new Date(r.timestamp) >= weekAgo),
            thisMonth: this.getSummaryForPeriod(r => new Date(r.timestamp) >= monthAgo),
            allTime: this.getSummaryForPeriod(() => true),
            recentRecords: this.records.slice(-20).reverse(),
            topFiles: this.getTopFiles(),
            projectedAnnualSavings: this.calculateAnnualProjection(),
        };
    }
    
    /**
     * Get daily breakdown for charting
     */
    getDailyBreakdown(days: number = 30): DailySummary[] {
        const breakdown: Map<string, SavingsRecord[]> = new Map();
        const now = new Date();
        
        // Group records by date
        for (const record of this.records) {
            const recordDate = new Date(record.timestamp);
            const daysAgo = Math.floor((now.getTime() - recordDate.getTime()) / (24 * 60 * 60 * 1000));
            
            if (daysAgo < days) {
                const dateKey = record.date;
                if (!breakdown.has(dateKey)) {
                    breakdown.set(dateKey, []);
                }
                breakdown.get(dateKey)!.push(record);
            }
        }
        
        // Convert to summaries
        const summaries: DailySummary[] = [];
        for (let i = days - 1; i >= 0; i--) {
            const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
            const dateKey = this.getDateString(date);
            const records = breakdown.get(dateKey) || [];
            
            summaries.push(this.calculateSummary(dateKey, records));
        }
        
        return summaries;
    }
    
    /**
     * Export data to CSV
     */
    exportToCSV(): string {
        const headers = [
            'Date',
            'Time',
            'File',
            'Language',
            'Original Tokens',
            'VL Tokens',
            'Saved Tokens',
            'Savings %',
            'Mode',
            'Cache Hit',
            'Cache Tokens',
        ].join(',');
        
        const rows = this.records.map(r => {
            const date = new Date(r.timestamp);
            return [
                r.date,
                date.toTimeString().split(' ')[0],
                `"${r.fileName}"`,
                r.language,
                r.originalTokens,
                r.vlTokens,
                r.savedTokens,
                r.savingsPercent.toFixed(1),
                r.mode,
                r.cacheHit ? 'Yes' : 'No',
                r.cacheTokens || 0,
            ].join(',');
        });
        
        return [headers, ...rows].join('\n');
    }
    
    /**
     * Reset all analytics data
     */
    reset(): void {
        this.records = [];
        this.saveRecords();
    }
    
    // Private helper methods
    
    private getSummaryForPeriod(predicate: (r: SavingsRecord) => boolean): DailySummary {
        const filtered = this.records.filter(predicate);
        const dateRange = this.getDateRangeLabel(filtered);
        return this.calculateSummary(dateRange, filtered);
    }
    
    private calculateSummary(label: string, records: SavingsRecord[]): DailySummary {
        if (records.length === 0) {
            return {
                date: label,
                totalSavings: 0,
                totalOriginal: 0,
                totalVL: 0,
                requestCount: 0,
                avgSavingsPercent: 0,
                fileCount: 0,
            };
        }
        
        const totalSavings = records.reduce((sum, r) => sum + r.savedTokens, 0);
        const totalOriginal = records.reduce((sum, r) => sum + r.originalTokens, 0);
        const totalVL = records.reduce((sum, r) => sum + r.vlTokens, 0);
        const avgSavingsPercent = totalOriginal > 0 
            ? (totalSavings / totalOriginal) * 100 
            : 0;
        const uniqueFiles = new Set(records.map(r => r.fileName)).size;
        
        return {
            date: label,
            totalSavings,
            totalOriginal,
            totalVL,
            requestCount: records.length,
            avgSavingsPercent: Math.round(avgSavingsPercent * 10) / 10,
            fileCount: uniqueFiles,
        };
    }
    
    private getTopFiles(): Array<{ file: string; savings: number; count: number }> {
        const fileMap = new Map<string, { savings: number; count: number }>();
        
        for (const record of this.records) {
            const existing = fileMap.get(record.fileName) || { savings: 0, count: 0 };
            fileMap.set(record.fileName, {
                savings: existing.savings + record.savedTokens,
                count: existing.count + 1,
            });
        }
        
        return Array.from(fileMap.entries())
            .map(([file, data]) => ({ file, ...data }))
            .sort((a, b) => b.savings - a.savings)
            .slice(0, 10);
    }
    
    private calculateAnnualProjection() {
        const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        const recentRecords = this.records.filter(r => new Date(r.timestamp) >= thirtyDaysAgo);
        
        if (recentRecords.length === 0) {
            return {
                tokens: 0,
                costAtCopilotPricing: 0,
                costAtClaudeAPI: 0,
            };
        }
        
        // Calculate daily average
        const totalSavings = recentRecords.reduce((sum, r) => sum + r.savedTokens, 0);
        const avgDailySavings = totalSavings / 30;
        
        // Project to annual
        const annualTokens = Math.round(avgDailySavings * 365);
        
        // Cost calculations
        // Copilot: $10/month = $120/year, assume 50% savings = $60
        // Claude API: $3 per 1M input tokens
        const costAtCopilotPricing = 60; // Simplified
        const costAtClaudeAPI = (annualTokens / 1_000_000) * 3;
        
        return {
            tokens: annualTokens,
            costAtCopilotPricing: Math.round(costAtCopilotPricing),
            costAtClaudeAPI: Math.round(costAtClaudeAPI * 100) / 100,
        };
    }
    
    private getDateString(date: Date): string {
        return date.toISOString().split('T')[0];
    }
    
    private getDateRangeLabel(records: SavingsRecord[]): string {
        if (records.length === 0) return 'No data';
        const dates = records.map(r => r.date).sort();
        return dates.length === 1 ? dates[0] : `${dates[0]} to ${dates[dates.length - 1]}`;
    }
    
    private loadRecords(): void {
        try {
            // Ensure directory exists
            const dir = path.dirname(this.storageFile);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            
            if (fs.existsSync(this.storageFile)) {
                const data = fs.readFileSync(this.storageFile, 'utf8');
                this.records = JSON.parse(data);
            }
        } catch (error) {
            console.error('Failed to load analytics:', error);
            this.records = [];
        }
    }
    
    private saveRecords(): void {
        try {
            const dir = path.dirname(this.storageFile);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            
            fs.writeFileSync(this.storageFile, JSON.stringify(this.records, null, 2));
        } catch (error) {
            console.error('Failed to save analytics:', error);
        }
    }
}
