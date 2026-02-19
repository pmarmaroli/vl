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
     * Validate Python syntax before conversion
     */
    private async validatePythonSyntax(code: string): Promise<{ valid: boolean; error?: string }> {
        return new Promise((resolve) => {
            const env = { ...process.env, PYTHONPATH: path.join(this.vlRoot, 'src') };
            const proc = child_process.spawn(this.pythonPath, ['-c', code], { env });
            
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
