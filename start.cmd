@echo off
cd /d "%~dp0"
echo Installing dependencies...
pip install -r requirements.txt
echo Starting Beauty UGC SaaS...
echo Open http://127.0.0.1:8000 in your browser
echo Demo login: demo@example.com / password123
python main.py
pause
