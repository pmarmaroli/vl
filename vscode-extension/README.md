# VL AI Cost Optimizer

**Cut your AI coding costs by 45% — automatically.**

VL is a VS Code extension that optimizes AI coding assistant requests, reducing token usage and costs without requiring you to learn a new language.

## Features

### 🔮 Transparent Mode (Active Now!)
- **Automatic AI chat optimization** - Just use `@vl` in VS Code chat
- Optimizes Python code to VL format before sending to Claude/AI
- **Zero learning curve** - Keep writing Python normally
- **Real-time cost savings tracking** - Dashboard with daily/weekly/monthly stats
- **45% average token reduction** - Verified with actual Claude tokenizer
- **Smart fallback** - Validates Python syntax, gracefully handles conversion errors
- **Apply code buttons** - One-click application of AI responses

### 🎯 Manual Optimization (Also Available)
- Convert Python files to token-efficient VL format
- Compile VL back to Python/JavaScript/TypeScript
- See token savings in real-time
- Command palette integration

## Quick Start

1. **Install the extension**
2. **Add your Anthropic API key** to VS Code settings (`vl.anthropicApiKey`)
3. **Open VS Code chat** (`Ctrl+Shift+I` or `Cmd+Shift+I`)
4. **Use `@vl` to activate optimization:**
   ```
   @vl #file:my_script.py Can you help optimize this?
   ```
5. **Watch the savings** - Click "VL: Show Cost Savings Dashboard" to see analytics

### How It Works

When you use `@vl` in chat, the extension:
1. Extracts referenced Python files
2. Validates syntax (prevents corrupted file conversions)
3. Converts to VL format (45% token reduction)
4. Sends optimized request to Claude with prompt caching
5. Tracks savings in persistent analytics
6. Shows "Apply Code" buttons for easy implementation

## Commands

- `@vl` - Chat participant for optimized AI requests (use in VS Code chat)
- `VL: Show Cost Savings Dashboard` - View detailed analytics with projections
- `VL: Export Analytics to CSV` - Export full savings history
- `VL: Convert Current File to VL` - Manual Python → VL conversion
- `VL: Compile VL to Target Language` - Manual VL → Python/JS/TS compilation
- `VL: Toggle Transparent Mode` - Enable/disable auto-optimization
- `VL: Reset Statistics` - Clear token savings data

## Prompt Syntax (Update Guide)

- System prompt + cached VL spec live in `src/transparent-mode/claudeClient.ts` (`getVLSpecification`, `buildChatPrompt`, `buildPrompt`).
- Keep prompts concise and align with current VL syntax (raw/base64 passthrough, full-module preservation). Avoid reiterating the spec already cached.
- After any prompt edits, rebuild and repackage:
   ```bash
   npm install         # once
   npm run compile     # refresh out/
   npm run package     # produce .vsix
   ```
   Then install the new VSIX in VS Code for testing.

## Release Notes

### 0.2.0-alpha (January 2026)

**Major Release: Transparent Mode Complete! 🎉**

- ✅ **Chat Participant Integration** - Use `@vl` in VS Code chat for automatic optimization
- ✅ **Calibrated Token Estimation** - Measured actual Claude tokenizer (2.58 chars/token)
- ✅ **Python Syntax Validation** - Pre-flight checks prevent corrupted file conversions
- ✅ **Analytics Dashboard** - Daily/weekly/monthly breakdown with projections
- ✅ **CSV Export** - Full savings history export for analysis
- ✅ **Apply Code Buttons** - One-click code application from AI responses
- ✅ **Prompt Caching** - VL spec cached for 90% token savings on repeat requests
- ✅ **Graceful Fallbacks** - Smart error handling with clear user messaging
- ✅ **Persistent Storage** - Analytics saved across VS Code sessions

**Performance:**
- 45% average token reduction on Python code
- Validated with real Claude API measurements
- Supports Python initially (JavaScript/TypeScript coming soon)

### 0.1.0

- Initial release with basic syntax highlighting
