@echo off
REM ─── StockAI Platform Quick Start (No Docker required) ───────────────────────

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     🚀 StockAI Platform Setup Script      ║
echo  ╚══════════════════════════════════════════╝
echo.

REM ── Backend Setup ────────────────────────────────────────────────────────────
echo [1/5] Setting up Python virtual environment...
cd /d "%~dp0backend"
if not exist venv (
    python -m venv venv
    echo     ✅ Virtual environment created
) else (
    echo     ✅ Virtual environment already exists
)

echo.
echo [2/5] Installing Python dependencies (this may take a few minutes)...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
echo     ✅ Python dependencies installed

REM ── Frontend Setup ────────────────────────────────────────────────────────────
echo.
echo [3/5] Installing Node.js dependencies...
cd /d "%~dp0frontend"
npm install --silent
echo     ✅ Node.js dependencies installed

REM ── Environment ──────────────────────────────────────────────────────────────
echo.
echo [4/5] Setting up environment...
cd /d "%~dp0"
if not exist .env (
    copy .env.example .env
    echo     ✅ Created .env from template
) else (
    echo     ✅ .env already exists
)

echo.
echo [5/5] Setup complete!
echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  ⚡ To start the platform:                                    ║
echo  ║                                                               ║
echo  ║  Terminal 1 (Backend):                                        ║
echo  ║    cd backend                                                 ║
echo  ║    venv\Scripts\activate                                      ║
echo  ║    uvicorn main:app --reload --port 8000                     ║
echo  ║                                                               ║
echo  ║  Terminal 2 (Frontend):                                       ║
echo  ║    cd frontend                                                ║
echo  ║    npm run dev                                                ║
echo  ║                                                               ║
echo  ║  🌐 Frontend:  http://localhost:3000                          ║
echo  ║  📖 API Docs:  http://localhost:8000/docs                     ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
pause
