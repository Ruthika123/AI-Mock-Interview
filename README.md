# AI Mock Interview

A Flask application for technology-specific AI mock interviews. It works in fallback mode without an API key and uses an OpenAI-compatible chat completions endpoint when configured.

## Run on Windows

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open http://127.0.0.1:5000. Add `AI_API_KEY` to `.env` to enable live question generation and answer evaluation. The `.env` file is ignored by Git.