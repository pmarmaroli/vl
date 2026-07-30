/**
 * VL Converter - Bridge to the Python-based VL (Very Little) toolkit
 * (semantic minifier + v2 macro compression)
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import * as child_process from 'child_process';
import { Logger } from '../utils/logger';
import { estimateTokens } from '../utils/tokenEstimator';

export type OptimizationMode = 'minify' | 'v2' | 'auto';

export interface OptimizationResult {
    content: string;
    /**
     * 'python-min' = minified plain Python, 'v2' = minified Python with VL v2
     * macros, 'original' = unchanged
     */
    format: 'python-min' | 'v2' | 'original';
    originalTokens: number;
    optimizedTokens: number;
    /** VL v2 macro spec to include in the prompt (set only for format 'v2') */
    spec?: string;
}

interface V2Result {
    content: string;
    macros: Record<string, number>;
    spec: string;
}

export class VLConverter {
    private pythonPath: string;
    private vlRoot: string;

    constructor(
        private context: vscode.ExtensionContext,
        private logger: Logger
    ) {
        const config = vscode.workspace.getConfiguration('vl');
        this.pythonPath = config.get<string>('compiler.pythonPath', 'python');

        // 1. Check for a bundled VL toolkit in the extension directory
        const bundledToolkitPath = path.join(context.extensionPath, 'vl-compiler', 'src', 'vl', 'py_minify.py');
        let foundVlRoot: string | undefined;

        if (require('fs').existsSync(bundledToolkitPath)) {
            foundVlRoot = path.join(context.extensionPath, 'vl-compiler');
            this.logger.info('Using bundled VL toolkit', { path: foundVlRoot });
        }

        // 2. Check workspace folders for the vl repo
        if (!foundVlRoot) {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (workspaceFolders) {
                for (const folder of workspaceFolders) {
                    const candidatePath = folder.uri.fsPath;
                    const toolkitPath = path.join(candidatePath, 'src', 'vl', 'py_minify.py');

                    if (require('fs').existsSync(toolkitPath)) {
                        foundVlRoot = candidatePath;
                        this.logger.debug('Found VL toolkit in workspace', { path: candidatePath });
                        break;
                    }
                }
            }
        }

        // 3. Fallback: sibling directory (for development)
        if (!foundVlRoot) {
            foundVlRoot = path.resolve(context.extensionPath, '..', '..', 'vl');
            this.logger.warn('Using fallback VL path - toolkit may not be available', { path: foundVlRoot });
        }

        this.vlRoot = foundVlRoot;

        this.logger.debug('VLConverter initialized', {
            pythonPath: this.pythonPath,
            vlRoot: this.vlRoot
        });
    }

    /**
     * Optimize code for LLM token efficiency according to the configured mode.
     *
     * - 'minify' (default): semantic Python minification — plain Python out,
     *   no spec needed in the prompt, measured ~20-30% real savings.
     * - 'v2': macro compression + minification. Highest savings (~57% on
     *   pattern-rich code); the small macro spec is included in the prompt
     *   only when macros were actually detected.
     * - 'auto': run both and keep whichever estimates cheapest.
     *
     * Never returns something more expensive than the original (spec
     * overhead included in the comparison).
     */
    async optimize(
        code: string,
        language: 'python' | 'javascript' | 'typescript',
        mode?: OptimizationMode
    ): Promise<OptimizationResult> {
        const config = vscode.workspace.getConfiguration('vl');
        const effectiveMode = mode ?? config.get<OptimizationMode>('optimizationMode', 'minify');
        const originalTokens = estimateTokens(code, language);

        const candidates: Array<{
            content: string;
            format: 'python-min' | 'v2';
            tokens: number;
            spec?: string;
        }> = [];

        if (effectiveMode === 'minify' || effectiveMode === 'auto') {
            const minified = await this.toMinified(code, language);
            if (minified !== code) {
                candidates.push({
                    content: minified,
                    format: 'python-min',
                    tokens: estimateTokens(minified, language)
                });
            }
        }
        if (effectiveMode === 'v2' || effectiveMode === 'auto') {
            const v2 = await this.toV2(code, language);
            if (v2 !== null) {
                const hasMacros = Object.keys(v2.macros).length > 0;
                // Count the spec against the candidate so the "never worse
                // than original" guarantee holds even on the first request.
                const specTokens = hasMacros ? estimateTokens(v2.spec, language) : 0;
                candidates.push({
                    content: v2.content,
                    format: hasMacros ? 'v2' : 'python-min',
                    tokens: estimateTokens(v2.content, language) + specTokens,
                    spec: hasMacros ? v2.spec : undefined
                });
            }
        }
        const best = candidates
            .filter(c => c.tokens < originalTokens)
            .sort((a, b) => a.tokens - b.tokens)[0];

        if (!best) {
            return { content: code, format: 'original', originalTokens, optimizedTokens: originalTokens };
        }
        return {
            content: best.content,
            format: best.format,
            originalTokens,
            optimizedTokens: best.tokens,
            spec: best.spec
        };
    }

    /**
     * VL v2 pipeline: compress known patterns into macros, then minify.
     * Returns null on any failure (caller falls back to other strategies).
     */
    private async toV2(
        code: string,
        language: 'python' | 'javascript' | 'typescript'
    ): Promise<V2Result | null> {
        if (language !== 'python') {
            return null;
        }
        try {
            const raw = await this.runPython(['-m', 'vl.v2', '-c', '--minify', '--json', '-'], code);
            const parsed = JSON.parse(raw) as V2Result;
            if (typeof parsed.content !== 'string' || !parsed.content.trim()) {
                return null;
            }
            return parsed;
        } catch (error) {
            this.logger.debug('v2 pipeline unavailable for this input', {
                error: (error as Error)?.message?.substring(0, 100)
            });
            return null;
        }
    }

    /**
     * Minify Python code for token efficiency (semantics preserved, AST-verified).
     * Output is plain Python — no VL spec needed in the prompt, no correctness risk.
     * Falls back to the original code on any failure.
     */
    async toMinified(code: string, language: 'python' | 'javascript' | 'typescript'): Promise<string> {
        if (language !== 'python') {
            // Minification only implemented for Python so far
            return code;
        }
        this.logger.debug(`Minifying python (${code.length} chars)`);
        try {
            const result = await this.runPython(['-m', 'vl.py_minify', '-'], code);
            // py_minify guarantees valid output or echoes the input; guard anyway
            return result.trim().length > 0 ? result : code;
        } catch (error) {
            this.logger.warn('Python minification failed, using original code', error);
            return code;
        }
    }

    /**
     * Run Python script with stdin/stdout
     * For large inputs, uses temporary file to avoid Windows command line length limits
     */
    private runPython(args: string[], stdin?: string): Promise<string> {
        return new Promise((resolve, reject) => {
            this.logger.info('runPython called', { argsCount: args.length, stdinSize: stdin?.length });
            
            // For large inputs (>1KB), use temp file to avoid ENAMETOOLONG on Windows
            let tempFile: string | undefined;
            let cleanupTempFile = () => {};
            
            if (stdin && stdin.length > 1000) {
                try {
                    // Create temp file
                    tempFile = path.join(os.tmpdir(), `vl-input-${Date.now()}.py`);
                    fs.writeFileSync(tempFile, stdin, 'utf8');
                    this.logger.info('Using temp file for large input', { 
                        size: stdin.length, 
                        tempFile 
                    });
                    
                    // Replace '-' with temp file path in args
                    args = args.map(arg => arg === '-' ? tempFile! : arg);
                    stdin = undefined; // Don't use stdin
                    
                    // Schedule cleanup
                    cleanupTempFile = () => {
                        try {
                            if (tempFile && fs.existsSync(tempFile)) {
                                fs.unlinkSync(tempFile);
                            }
                        } catch (e) {
                            // Ignore cleanup errors
                        }
                    };
                } catch (error: any) {
                    this.logger.error('Failed to create temp file', error);
                    reject(new Error(`Failed to create temp file: ${error.message}`));
                    return;
                }
            }
            
            // Set minimal environment to avoid Windows ENAMETOOLONG errors
            // Only pass essential variables instead of spreading entire process.env
            const env: { [key: string]: string } = {
                PYTHONPATH: path.join(this.vlRoot, 'src'),
                PATH: process.env.PATH || '',
                SYSTEMROOT: process.env.SYSTEMROOT || '',
                USERPROFILE: process.env.USERPROFILE || '',
                HOME: process.env.HOME || '',
                TEMP: process.env.TEMP || '',
                TMP: process.env.TMP || ''
            };
            
            this.logger.debug('Running Python', { 
                command: this.pythonPath, 
                args: tempFile ? args : args.map(a => a === '-' ? '<stdin>' : a),
                stdinSize: stdin?.length,
                env: { PYTHONPATH: env.PYTHONPATH }
            });
            
            let proc: child_process.ChildProcess;
            try {
                proc = child_process.spawn(this.pythonPath, args, {
                    cwd: this.vlRoot,
                    env,
                    windowsHide: true  // Don't show console window
                });
            } catch (spawnError: any) {
                cleanupTempFile();
                this.logger.error('spawn() failed synchronously', spawnError);
                reject(new Error(`Failed to spawn Python process: ${spawnError.message}`));
                return;
            }
            
            let stdout = '';
            let stderr = '';
            
            proc.stdout?.on('data', (data: Buffer) => {
                stdout += data.toString();
            });
            
            proc.stderr?.on('data', (data: Buffer) => {
                stderr += data.toString();
            });
            
            proc.on('error', (error: Error) => {
                cleanupTempFile();
                this.logger.error('Python process error', error);
                reject(new Error(`Failed to start Python: ${error.message}`));
            });
            
            proc.on('close', (code: number | null) => {
                cleanupTempFile();
                
                if (code === 0) {
                    resolve(stdout);
                } else {
                    // Don't log syntax errors as ERROR - they're expected during typing
                    const isSyntaxError = stderr && (
                        stderr.includes('Invalid Python syntax') ||
                        stderr.includes('SyntaxError') ||
                        stderr.includes('unexpected indent') ||
                        stderr.includes('expected')
                    );
                    
                    if (!isSyntaxError) {
                        this.logger.error('Python process failed', { code, stderr });
                    }
                    
                    reject(new Error(`Python exited with code ${code}: ${stderr}`));
                }
            });
            
            // Send stdin if provided
            if (stdin && proc.stdin) {
                proc.stdin.write(stdin);
                proc.stdin.end();
            }
        });
    }
    
    /**
     * Test if Python and the VL toolkit modules are available
     */
    async test(): Promise<{ success: boolean; error?: string }> {
        try {
            this.logger.debug('Testing VL toolkit');

            const testCode = '# comment\ndef test():\n    return 42\n';
            const minified = await this.runPython(['-m', 'vl.py_minify', '-'], testCode);

            if (minified.includes('def test') && !minified.includes('# comment')) {
                this.logger.info('VL toolkit test passed');
                return { success: true };
            } else {
                return { success: false, error: 'Unexpected minifier output' };
            }
        } catch (error: any) {
            this.logger.error('VL toolkit test failed', error);
            return { success: false, error: error.message };
        }
    }
}
