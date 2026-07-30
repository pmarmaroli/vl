# VL (Very Little) — AI Cost Optimizer

**Cut your AI coding costs — automatically.** (measured 20–30% token savings via semantic minification, up to ~57% with VL v2 macros)

VL (Very Little) is a VS Code extension that optimizes AI coding assistant requests — semantic minification and v2 macro compression reduce token usage and costs. Everything stays plain Python: there is no new language to learn.

## Features

### 🔮 Transparent Mode (Active Now!)
- **Automatic AI chat optimization** - Just use `@vl` in VS Code chat
- Minifies / macro-compresses Python context before sending to Claude/AI
- **Zero learning curve** - Keep writing Python normally
- **Real-time cost savings tracking** - Dashboard with daily/weekly/monthly stats
- **Measured 20–30% token reduction** on typical Python (semantic minification, verified with a real LLM tokenizer)
- **Smart fallback** - Validates Python syntax, gracefully handles conversion errors
- **Apply code buttons** - One-click application of AI responses

### 🎯 Manual Optimization (Also Available)
- `VL: Optimize Current File (Minify / v2)` — see what the model would receive
- See token savings in real-time
- Command palette integration

## Quick Start

1. **Install the extension**
2. **Add your Anthropic API key** with the command `VL: Set Anthropic API Key` (stored in VS Code secure storage)
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
3. Optimizes the code (semantic minification by default; VL v2 macros for higher savings)
4. Sends optimized request to Claude with prompt caching
5. Tracks savings in persistent analytics
6. Shows "Apply Code" buttons for easy implementation

## Commands

- `@vl` - Chat participant for optimized AI requests (use in VS Code chat)
- `VL: Show Cost Savings Dashboard` - View detailed analytics with projections
- `VL: Export Analytics to CSV` - Export full savings history
- `VL: Optimize Current File (Minify / v2)` - Preview the token-optimized version of the current file
- `VL: Set Anthropic API Key` - Store your API key in VS Code secure storage
- `VL: Toggle Transparent Mode` - Enable/disable auto-optimization
- `VL: Reset Statistics` - Clear token savings data

## Prompt Syntax (Update Guide)

- System prompts live in `src/transparent-mode/claudeClient.ts` (`buildSystemPrompt`, `buildChatPrompt`). The small VL v2 macro spec is inlined only when macros are present in the context.
- Keep prompts concise.
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
- Measured 20–30% token reduction on typical Python code (more with VL v2 macros)
- Validated with real Claude API measurements
- Supports Python initially (JavaScript/TypeScript coming soon)

### 0.1.0

- Initial release with basic syntax highlighting
