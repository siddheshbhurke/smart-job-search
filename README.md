# Smart Job Match

AI-powered resume-to-job recommendation system built using FastAPI, JavaScript, and Gemini-powered reasoning with intelligent fallback logic.

## Live Demo

🌐 Live Application:  
https://smart-job-search-alpha.vercel.app/

---

## Features

- Resume-based job recommendations
- Dynamic clarifying question generation
- Interactive reranking workflow
- AI-powered reasoning with Gemini
- Automatic fallback logic if AI quota fails
- FastAPI backend
- Responsive frontend
- Vercel deployment ready

---

## Tech Stack

- Python
- FastAPI
- JavaScript
- HTML/CSS
- Gemini API
- Vercel

---

## Project Structure

```text
smart-job-match/
│
├── static/
│   ├── app.js
│   └── style.css
│
├── templates/
│   └── index.html
│
├── job_dataset.json
├── main.py
├── requirements.txt
├── vercel.json
└── README.md
```

---

## Setup

```bash
git clone <repo-url>
cd smart-job-match
pip install -r requirements.txt
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

---

## API Endpoints

### POST `/recommend`

Generates:
- candidate profile
- ranked jobs
- clarifying question

### Request

```json
{
  "resume_text": "resume content"
}
```

---

### POST `/refine`

Reranks jobs based on user clarification.

### Request

```json
{
  "resume_text": "resume content",
  "user_feedback": "I prefer AI-focused roles"
}
```

---

## Agentic Workflow

```text
Resume Input
     ↓
Candidate Extraction
     ↓
Initial Job Ranking
     ↓
AI Reasoning + Clarifying Question
     ↓
User Feedback
     ↓
Job Reranking
```

---

## Fallback Architecture

If Gemini API:
- fails,
- exceeds quota,
- or becomes unavailable,

the system automatically switches to:
- deterministic candidate extraction,
- local reasoning,
- fallback reranking logic.

This ensures uninterrupted functionality during deployment and demo scenarios.

---

## Deployment

Deployed using Vercel.

### Environment Variable

```env
GEMINI_API_KEY=your_api_key
```

---

## Design Decisions

- FastAPI chosen for lightweight API architecture
- Multi-stage pipeline used instead of one monolithic prompt
- Fallback logic added for resilience against quota failures
- Dynamic clarification improves reranking quality
- Frontend kept lightweight for fast deployment

---

## Limitations

- Local ranking is keyword-based during fallback mode
- Gemini free-tier quota may throttle requests
- No persistent database currently used

---

## Future Improvements

- Vector embeddings for semantic retrieval
- Persistent user sessions
- Better ranking models
- Real-time job APIs
- Authentication system

---

## Author

Siddhesh
