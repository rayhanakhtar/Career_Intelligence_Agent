# Setup script for Career Intelligence Agent (Windows)
# Run this from the repository root: .\scripts\setup.ps1

Write-Host "=== Career Intelligence Agent Setup ===" -ForegroundColor Cyan

# 1. Create virtual environment if not exists
if (-not (Test-Path ".venv")) {
    Write-Host "[1/5] Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "[1/5] Virtual environment already exists" -ForegroundColor Green
}

# 2. Activate and install dependencies
Write-Host "[2/5] Installing Python dependencies..." -ForegroundColor Yellow
& ".venv\Scripts\pip" install --upgrade pip
& ".venv\Scripts\pip" install -r requirements.txt

# 3. Install Playwright browsers (if playwright is available)
Write-Host "[3/5] Installing Playwright browsers..." -ForegroundColor Yellow
& ".venv\Scripts\python" -m playwright install chromium 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Playwright Chromium installed successfully" -ForegroundColor Green
} else {
    Write-Host "  Playwright not found or installation skipped (optional)" -ForegroundColor DarkYellow
}

# 4. Verify database setup
Write-Host "[4/5] Verifying database..." -ForegroundColor Yellow
& ".venv\Scripts\python" -c "
import sqlite3, os
db_path = os.getenv('DATABASE_PATH', 'jobs.db')
conn = sqlite3.connect(db_path)
conn.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, company TEXT NOT NULL, location TEXT DEFAULT \"\", description TEXT DEFAULT \"\", apply_url TEXT DEFAULT \"\", department TEXT DEFAULT \"\", employment_type TEXT DEFAULT \"\", posted_at TEXT DEFAULT \"\", source TEXT DEFAULT \"\", source_id TEXT DEFAULT \"\", created_at TEXT DEFAULT (datetime(\"now\")), UNIQUE(company, title))')
conn.commit()
conn.close()
print(f'  Database ready at {db_path}')
"

# 5. Verify company registry
Write-Host "[5/5] Verifying company registry..." -ForegroundColor Yellow
& ".venv\Scripts\python" -c "
import json
with open('data/companies.json', 'r') as f:
    companies = json.load(f)
print(f'  Loaded {len(companies)} companies from registry')
enabled = [c for c in companies if c.get('enabled')]
print(f'  Enabled crawlers: {len(enabled)}')
for c in enabled:
    print(f'    - {c[\"company\"]} ({c[\"platform\"]})')
"

Write-Host "`n=== Setup complete ===" -ForegroundColor Cyan
Write-Host "Run the application:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\activate"
Write-Host "  python -m api.main"
Write-Host "`nRun tests:" -ForegroundColor Green
Write-Host "  python -m pytest tests/ -v"
