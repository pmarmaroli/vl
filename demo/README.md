# VL Language Demo

Interactive web demo for the VL (Vibe Language) token-efficient Python compiler.

## Features

- Python → VL → Python roundtrip conversion
- Real-time token savings calculation
- Clean, responsive UI
- Serverless backend (Vercel Functions)

## Local Development

```bash
# Install Vercel CLI
npm install -g vercel

# Run locally
vercel dev
```

Visit: http://localhost:3000

## Deployment

```bash
# Deploy to Vercel
vercel --prod
```

## How It Works

1. **Frontend**: Static HTML/CSS/JS interface
2. **Backend**: Python serverless function (`api/convert.py`)
3. **Compiler**: Bundled VL compiler from main repository

## Architecture

```
vl-demo/
├── index.html           # Main demo page
├── styles.css          # Styling
├── app.js              # Frontend logic
├── api/
│   └── convert.py      # Vercel serverless function
├── vl-compiler/        # Bundled VL compiler (copied from main repo)
└── vercel.json         # Vercel configuration
```

## Token Estimation

Uses 2.58 chars/token ratio calibrated from real tokenizers.
