@echo off
setlocal
title SUPRA Agentic Taskmaster
cd /d "E:\PROYECTS\SUPRA"
python -m uvicorn supra_agentic.service:app --host 127.0.0.1 --port 8080
endlocal
