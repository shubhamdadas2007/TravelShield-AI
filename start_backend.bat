@echo off
title TravelShield AI - FastAPI Backend Server
echo =========================================================
echo    TravelShield AI - Multimodal Disruption Recovery Engine
echo                 FastAPI Backend v2.3.0
echo =========================================================
echo.
echo Checking Python environment...
python --version
echo.
echo Starting FastAPI Backend Server on http://127.0.0.1:8000 ...
echo API Documentation available at: http://127.0.0.1:8000/docs
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
