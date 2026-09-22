@echo off
cd /d %~dp0
pip install -q -r requirements.txt
python -m uvicorn app:app --port 8100 --reload
