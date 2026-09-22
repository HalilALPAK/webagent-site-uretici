"""Web Agent platformunu başlatır:  python run.py  →  http://127.0.0.1:8000"""
import uvicorn

from webagent.config import PORT

if __name__ == "__main__":
    uvicorn.run("webagent.web.app:app", host="127.0.0.1", port=PORT)
