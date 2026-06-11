/**
 * VL Converter - Bridge to Python-based VL compiler
 * Handles bidirectional conversion: Python/JS/TS ↔ VL
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import * as child_process from 'child_process';
import { Logger } from '../utils/logger';
import { estimateTokens } from '../utils/tokenEstimator';

export type OptimizationMode = 'minify' | 'v2' | 'vl' | 'auto';

export interface OptimizationResult {
    content: string;
    /**
     * 'python-min' = minified plain Python, 'v2' = minified Python with VL v2
     * macros, 'vl' = VL syntax, 'original' = unchanged
     */
    format: 'python-min' | 'v2' | 'vl' | 'original';
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
    private converterScript: string;
    private vlRoot: string;
    
    constructor(
        private context: vscode.ExtensionContext,
        private logger: Logger
    ) {
        const config = vscode.workspace.getConfiguration('vl');
        this.pythonPath = config.get<string>('compiler.pythonPath', 'python');
        
        // 1. Check for bundled VL compiler in extension directory
        const bundledCompilerPath = path.join(context.extensionPath, 'vl-compiler', 'src', 'vl', 'py2vl.py');
        let foundVlRoot: string | undefined;
        
        if (require('fs').existsSync(bundledCompilerPath)) {
            foundVlRoot = path.join(context.extensionPath, 'vl-compiler');
            this.logger.info('Using bundled VL compiler', { path: foundVlRoot });
        }
        
        // 2. Check workspace folders for vibe-language repo
        if (!foundVlRoot) {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (workspaceFolders) {
                for (const folder of workspaceFolders) {
                    const candidatePath = folder.uri.fsPath;
                    const converterPath = path.join(candidatePath, 'src', 'vl', 'py2vl.py');
                    
                    if (require('fs').existsSync(converterPath)) {
                        foundVlRoot = candidatePath;
                        this.logger.debug('Found VL compiler in workspace', { path: candidatePath });
                        break;
                    }
                }
            }
        }
        
        // 3. Fallback: sibling directory (for development)
        if (!foundVlRoot) {
            foundVlRoot = path.resolve(context.extensionPath, '..', '..', 'vibe-language');
            this.logger.warn('Using fallback VL path - compiler may not be available', { path: foundVlRoot });
        }
        
        this.vlRoot = foundVlRoot;
        this.converterScript = path.join(this.vlRoot, 'src', 'vl', 'py2vl.py');
        
        this.logger.debug('VLConverter initialized', {
            pythonPath: this.pythonPath,
            vlRoot: this.vlRoot,
            converterScript: this.converterScript
        });
    }
    
    /**
     * Convert source code to VL
     */
    async toVL(code: string, language: 'python' | 'javascript' | 'typescript'): Promise<string> {
        this.logger.debug(`Converting ${language} to VL (${code.length} chars)`);
        
        if (language === 'python') {
            // Skip syntax validation for large files (causes ENAMETOOLONG on Windows)
            // The py2vl converter will catch syntax errors anyway
            if (code.length < 5000) {
                const syntaxCheck = await this.validatePythonSyntax(code);
                if (!syntaxCheck.valid) {
                    throw new Error(`Python syntax error: ${syntaxCheck.error}`);
                }
            }
            
            return this.pythonToVL(code);
        } else {
            // JavaScript/TypeScript conversion not yet implemented
            throw new Error(`${language} → VL conversion not yet implemented. Python conversion available now.`);
        }
    }
    
    /**
     * Optimize code for LLM token efficiency according to the configured mode.
     *
     * - 'minify' (default): semantic Python minification — plain Python out,
     *   no spec needed in the prompt, measured ~20-30% real savings.
     * - 'v2': macro compression + minification. Highest savings (~57% on
     *   pattern-rich code); the small macro spec is included in the prompt
     *   only when macros were actually detected.
     * - 'vl': legacy VL conversion.
     * - 'auto': run all and keep whichever estimates cheapest (VL tokens are
     *   estimated with the VL-specific ratio; see tokenEstimator).
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
            format: 'python-min' | 'v2' | 'vl';
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
        if (effectiveMode === 'vl' || effectiveMode === 'auto') {
            try {
                const vlCode = await this.toVL(code, language);
                candidates.push({
                    content: vlCode,
                    format: 'vl',
                    tokens: estimateTokens(vlCode, 'vl')
                });
            } catch (error) {
                this.logger.debug('VL conversion unavailable for this input', {
                    error: (error as Error)?.message?.substring(0, 100)
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
     * Validate Python syntax before conversion.
     * Uses ast.parse on stdin — never executes the user's code.
     */
    private async validatePythonSyntax(code: string): Promise<{ valid: boolean; error?: string }> {
        return new Promise((resolve) => {
            const env = { ...process.env, PYTHONPATH: path.join(this.vlRoot, 'src') };
            const proc = child_process.spawn(
                this.pythonPath,
                ['-c', 'import ast, sys; ast.parse(sys.stdin.read())'],
                { env }
            );
            proc.stdin?.on('error', () => { /* process exited early; close handler reports */ });
            proc.stdin?.write(code);
            proc.stdin?.end();
            
            let stderr = '';
            proc.stderr.on('data', (data) => {
                stderr += data.toString();
            });
            
            proc.on('close', (code) => {
                if (code === 0) {
                    resolve({ valid: true });
                } else {
                    // Extract just the error message, not full traceback
                    const errorMatch = stderr.match(/SyntaxError: (.+)/);
                    const error = errorMatch ? errorMatch[1] : 'Invalid Python syntax';
                    resolve({ valid: false, error });
                }
            });
            
            proc.on('error', (err) => {
                resolve({ valid: false, error: err.message });
            });
            
            // Timeout after 2 seconds
            setTimeout(() => {
                proc.kill();
                resolve({ valid: false, error: 'Syntax check timeout' });
            }, 2000);
        });
    }
    
    /**
     * Convert VL code to target language
     */
    async fromVL(vlCode: string, targetLanguage: 'python' | 'javascript' | 'typescript'): Promise<string> {
        this.logger.debug(`Converting VL to ${targetLanguage} (${vlCode.length} chars)`);
        
        const args = [
            '-m', 'vl.cli',
            '--target', targetLanguage === 'typescript' ? 'typescript' : 
                       targetLanguage === 'javascript' ? 'javascript' : 'python',
            '-'  // Read from stdin
        ];
        
        try {
            const result = await this.runPython(args, vlCode);
            this.logger.debug(`Conversion complete: ${result.length} chars`);
            return result;
        } catch (error) {
            this.logger.error('VL compilation failed', error);
            throw error;
        }
    }
    
    /**
     * Convert Python code to VL using py2vl module
     */
    private async pythonToVL(pythonCode: string): Promise<string> {
        const args = [
            '-m', 'vl.py2vl',
            '-'  // Read from stdin
        ];
        
        try {
            const result = await this.runPython(args, pythonCode);
            this.logger.debug(`Python → VL conversion complete: ${result.length} chars`);
            return result;
        } catch (error: any) {
            // Syntax errors are expected when converting incomplete code (mid-typing)
            const isSyntaxError = error.message && (
                error.message.includes('Invalid Python syntax') ||
                error.message.includes('SyntaxError') ||
                error.message.includes('unexpected indent') ||
                error.message.includes('expected')
            );
            
            if (isSyntaxError) {
                // Log syntax errors at DEBUG level (expected during typing)
                this.logger.debug('Python → VL conversion skipped (incomplete syntax)', { 
                    error: error.message?.substring(0, 100) 
                });
            } else {
                // Log other errors at ERROR level (unexpected)
                this.logger.error('Python → VL conversion failed', error);
            }
            throw error;
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
     * Test if Python and VL modules are available
     */
    async test(): Promise<{ success: boolean; error?: string }> {
        try {
            this.logger.debug('Testing VL converter');
            
            const testCode = 'def test(): return 42';
            const vlCode = await this.pythonToVL(testCode);
            
            if (vlCode.includes('F:test')) {
                this.logger.info('VL converter test passed');
                return { success: true };
            } else {
                return { success: false, error: 'Unexpected VL output' };
            }
        } catch (error: any) {
            this.logger.error('VL converter test failed', error);
            return { success: false, error: error.message };
        }
    }
}
