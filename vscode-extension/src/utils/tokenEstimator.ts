/**
 * Token Estimation for Claude API
 * 
 * Calibrated on 2026-01-31 using claude-sonnet-4-20250514
 * 
 * Methodology: Sent sample code (small/medium/large) in Python, JavaScript,
 * and TypeScript to Claude API and measured actual input_tokens.
 * 
 * Key finding: Claude's tokenizer is ~2.58 chars/token on average,
 * NOT 4 chars/token as commonly assumed. This means code uses more
 * tokens than naive estimates suggest.
 */

// Calibrated chars-per-token ratios by language
// Lower = more tokens per character = more expensive
const CHARS_PER_TOKEN: Record<string, number> = {
    python: 2.60,
    javascript: 2.61,
    typescript: 2.50,
    default: 2.58,
};

/**
 * Estimate token count for code using calibrated model
 * 
 * @param code - The source code to estimate tokens for
 * @param language - Programming language (python, javascript, typescript)
 * @returns Estimated token count
 */
export function estimateTokens(code: string, language?: string): number {
    const lang = language?.toLowerCase() || 'default';
    const ratio = CHARS_PER_TOKEN[lang] || CHARS_PER_TOKEN.default;
    return Math.ceil(code.length / ratio);
}

/**
 * Get the chars-per-token ratio for a language
 */
export function getCharsPerToken(language?: string): number {
    const lang = language?.toLowerCase() || 'default';
    return CHARS_PER_TOKEN[lang] || CHARS_PER_TOKEN.default;
}

/**
 * Calculate token savings between original and optimized code
 */
export function calculateSavings(
    originalCode: string, 
    optimizedCode: string, 
    language?: string
): { originalTokens: number; optimizedTokens: number; savedTokens: number; savingsPercent: number } {
    const originalTokens = estimateTokens(originalCode, language);
    const optimizedTokens = estimateTokens(optimizedCode, language);
    const savedTokens = originalTokens - optimizedTokens;
    const savingsPercent = originalTokens > 0 ? (savedTokens / originalTokens) * 100 : 0;
    
    return {
        originalTokens,
        optimizedTokens,
        savedTokens,
        savingsPercent: Math.round(savingsPercent * 10) / 10, // 1 decimal place
    };
}
