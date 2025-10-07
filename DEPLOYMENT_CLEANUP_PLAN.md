# API Deployment Cleanup Plan
**Goal**: Minimal production API for Next.js frontend integration

## What You Actually Need for Next.js Integration

### Essential Files (20 files)
```
├── agents/              # AI logic (5 files)
├── api/main.py          # FastAPI endpoints (1 file)
├── orchestrator/        # Workflow (2 files)
├── ops/                 # Core utilities (8 files)
│   ├── llm_client.py
│   ├── logging.py
│   ├── ulid_gen.py
│   ├── hashing.py
│   ├── retry.py
│   ├── job_board_scraper.py  # For URL scraping
│   ├── parsing_errors.py
│   └── __init__.py
├── schemas/models.py    # Data models (1 file)
├── requirements.txt     # Dependencies
├── Dockerfile          # For deployment
├── .env.example        # Config template
└── README.md           # Setup instructions
```

### DELETE from GitHub (Save 50% bloat)
```
❌ tests/ (all test files) - Keep in .gitignore, not in repo
❌ scripts/ (CLI tools) - Not needed for API
❌ examples/ - Demo code
❌ _archive/ - Old documentation
❌ docs/ (except API integration guide) - Too much documentation
❌ out/ - Output directory
❌ data/ - Data directory
❌ Most markdown files (keep README, CHANGELOG)
❌ setup.sh, setup.ps1 - Not needed for cloud deployment
❌ docker-compose.yml - For local dev only
```

### Keep but Don't Deploy (in .gitignore)
```
⚠️ tests/ - Important but not deployed
⚠️ htmlcov/ - Coverage reports
⚠️ .pytest_cache/
⚠️ __pycache__/
```

## Recommended Deployment Platforms

### Option 1: Railway.app (Easiest)
- Auto-detects Dockerfile
- Free tier available
- One-click deploy from GitHub
- Setup: `railway init` → push

### Option 2: Render.com
- Free tier available  
- Auto-deploy from GitHub
- Detects Python/FastAPI
- Setup: Connect repo → deploy

### Option 3: Fly.io
- Good free tier
- Global edge deployment
- Setup: `fly launch` → deploy

### Option 4: Google Cloud Run
- Serverless containers
- Pay per use
- Setup: `gcloud run deploy`

