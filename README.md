# Automated-Social-Media-Content-Generator
The system is a modular, autonomous system designed to generate brand-aligned social media content using AI-driven components. It orchestrates multiple services from narrative generation and voice synthesis to video editing.

## Project Structure
- `backend/` – FastAPI app, pipeline services, simulated agent workflow.
- `frontend/` – React dashboard with brand-aligned styling (to be scaffolded next).
- `docs/` – Brand notes, architecture overview, runbook.

## Prerequisites
- Python 3.11+
- Node.js 18+
- Create a `.env` file in `backend/` based on `.env.example` with Gemini and TTS keys if available (optional for mocked run).

## Backend Setup
1. `cd backend`
2. `python -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `uvicorn app.main:app --reload`

## Frontend Setup
1. `cd frontend`
2. `npm install`
3. `npm run dev`
