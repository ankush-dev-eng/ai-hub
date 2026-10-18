@echo off
title Hackathon AI Studio
cd /d "%~dp0"
echo ========================================================
echo   Hackathon AI Studio - Unified AI Prototyping Hub
echo ========================================================
echo Starting Streamlit app on http://localhost:8502...
uv run streamlit run app.py --server.port 8502
if %ERRORLEVEL% NEQ 0 (
    echo Streamlit stopped or encountered an error.
    pause
)
