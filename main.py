# =============================================================================
# IMPORTS
# =============================================================================

import os
import json
import asyncio
import logging

from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.responses import (
    JSONResponse,
    HTMLResponse
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import (
    BaseModel,
    Field,
    field_validator
)

from slowapi import (
    Limiter,
    _rate_limit_exceeded_handler
)

from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# =============================================================================
# OPTIONAL GEMINI IMPORT
# =============================================================================

GEMINI_AVAILABLE = True

try:

    from google import genai

except Exception:

    GEMINI_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

DATASET_FILE = BASE_DIR / "job_dataset.json"

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

FRONTEND_URL = "http://localhost:3000"

TOP_K_RESULTS = 5

MAX_RESUME_LENGTH = 10000


# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# =============================================================================
# GEMINI CLIENT
# =============================================================================

client = None

if GEMINI_AVAILABLE and GEMINI_API_KEY:

    try:

        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        logger.info(
            "Gemini client initialized"
        )

    except Exception as e:

        logger.error(
            f"Gemini initialization failed: {e}"
        )


# =============================================================================
# RATE LIMITER
# =============================================================================

limiter = Limiter(
    key_func=get_remote_address
)


# =============================================================================
# GLOBAL MEMORY
# =============================================================================

jobs_data = []


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class RecommendRequest(BaseModel):

    resume_text: str = Field(
        ...,
        min_length=10
    )

    @field_validator("resume_text")
    @classmethod
    def validate_resume(
        cls,
        value: str
    ) -> str:

        value = value.strip()

        if not value:

            raise ValueError(
                "resume_text cannot be empty"
            )

        if len(value) > MAX_RESUME_LENGTH:

            raise ValueError(
                f"resume_text exceeds "
                f"{MAX_RESUME_LENGTH} characters"
            )

        return value


class RefineRequest(BaseModel):

    resume_text: str
    user_feedback: str


class CandidateInfo(BaseModel):

    name: str
    skills: list[str]
    experience_years: int
    preferred_roles: list[str]
    education: str


class RankedJob(BaseModel):

    id: int
    title: str
    company: str
    similarity_score: float
    explanation: str


class RecommendResponse(BaseModel):

    candidate: CandidateInfo
    ranked_jobs: list[RankedJob]
    clarifying_question: str


# =============================================================================
# LOAD JOBS
# =============================================================================

def load_jobs():

    global jobs_data

    logger.info(
        "Loading jobs dataset"
    )

    if not DATASET_FILE.exists():

        raise FileNotFoundError(
            "job_dataset.json not found"
        )

    with open(
        DATASET_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        jobs_data = json.load(file)

    logger.info(
        f"Loaded {len(jobs_data)} jobs"
    )


# =============================================================================
# GEMINI HELPER
# =============================================================================

def generate_json_response(
    prompt: str
) -> dict:

    if not client:

        return {
            "error": "Gemini unavailable"
        }

    try:

        response = client.models.generate_content(

            model="gemini-2.0-flash",

            contents=prompt
        )

        text = response.text.strip()

        print("\n=== GEMINI RESPONSE ===")
        print(text)
        print("=======================\n")

        text = (
            text.replace(
                "```json",
                ""
            )
            .replace(
                "```",
                ""
            )
            .strip()
        )

        return json.loads(text)

    except Exception as e:

        logger.exception(
            "Gemini API failure"
        )

        return {
            "error": str(e)
        }


# =============================================================================
# FALLBACK CANDIDATE EXTRACTION
# =============================================================================

def fallback_candidate_extraction(
    resume_text: str
) -> dict:

    text = resume_text.lower()

    skills_master = [

        "python",
        "fastapi",
        "tensorflow",
        "pytorch",
        "docker",
        "aws",
        "sql",
        "machine learning",
        "deep learning",
        "nlp",
        "langchain",
        "react",
        "mongodb",
        "redis"
    ]

    extracted_skills = []

    for skill in skills_master:

        if skill in text:

            extracted_skills.append(
                skill.title()
            )

    preferred_roles = []

    role_keywords = {

        "AI Engineer":
            ["ai engineer"],

        "ML Engineer":
            ["ml engineer"],

        "Backend Engineer":
            ["backend engineer"],

        "Data Scientist":
            ["data scientist"]
    }

    for role, keywords in role_keywords.items():

        for keyword in keywords:

            if keyword in text:

                preferred_roles.append(
                    role
                )

    return {

        "name": "Candidate",

        "skills": extracted_skills,

        "experience_years": 1,

        "preferred_roles":
            preferred_roles,

        "education":
            "Bachelor's Degree"
    }


# =============================================================================
# CANDIDATE EXTRACTION
# =============================================================================

def extract_candidate_information(
    resume_text: str
) -> dict:

    logger.info(
        "Extracting candidate information"
    )

    prompt = f"""
    Extract candidate information
    from this resume.

    Resume:
    {resume_text}

    Return ONLY valid JSON.

    {{
      "name": "string",
      "skills": ["string"],
      "experience_years": 0,
      "preferred_roles": ["string"],
      "education": "string"
    }}
    """

    response = generate_json_response(
        prompt
    )

    if "error" in response:

        logger.warning(
            "Using fallback candidate extraction"
        )

        return fallback_candidate_extraction(
            resume_text
        )

    return {

        "name":
            response.get(
                "name",
                "Candidate"
            ),

        "skills":
            response.get(
                "skills",
                []
            ),

        "experience_years":
            response.get(
                "experience_years",
                1
            ),

        "preferred_roles":
            response.get(
                "preferred_roles",
                []
            ),

        "education":
            response.get(
                "education",
                "Bachelor's Degree"
            )
    }


# =============================================================================
# JOB RANKING
# =============================================================================

def rank_jobs(
    resume_text: str
) -> list[dict]:

    logger.info(
        "Ranking jobs"
    )

    matched_jobs = []

    resume_lower = resume_text.lower()

    for job in jobs_data:

        score = 0

        title = str(
            job.get("title", "")
        ).lower()

        description = str(
            job.get("description", "")
        ).lower()

        skills = " ".join(
            job.get("skills", [])
        ).lower()

        for keyword in resume_lower.split():

            if keyword in title:
                score += 3

            if keyword in description:
                score += 2

            if keyword in skills:
                score += 5

        matched_jobs.append({

            "id": job.get("id"),

            "title": job.get(
                "title",
                "Unknown"
            ),

            "company": job.get(
                "company",
                "Unknown"
            ),

            "similarity_score":
                round(score / 10, 2),

            "explanation":
                "Matched based on resume relevance"
        })

    matched_jobs.sort(
        key=lambda x:
            x["similarity_score"],
        reverse=True
    )

    return matched_jobs[:TOP_K_RESULTS]


# =============================================================================
# FALLBACK REASONING
# =============================================================================

def fallback_reasoning(
    candidate: dict,
    jobs: list[dict]
) -> dict:

    reasoned_jobs = []

    for job in jobs:

        reasoned_jobs.append({

            "id": job["id"],

            "explanation":
                f"This role aligns with the candidate's technical background and interest in {job['title']}."
        })

    return {

        "reasoned_jobs":
            reasoned_jobs,

        "clarifying_question":
            "Would you prefer AI-focused engineering roles or backend-heavy development roles?"
    }


# =============================================================================
# AI REASONING
# =============================================================================

def generate_reasoning(
    candidate: dict,
    jobs: list[dict]
) -> dict:

    logger.info(
        "Generating reasoning"
    )

    prompt = f"""
    You are an AI hiring assistant.

    Candidate:
    {json.dumps(candidate, indent=2)}

    Jobs:
    {json.dumps(jobs, indent=2)}

    Generate:
    1. Job explanations
    2. One clarifying question

    Return ONLY JSON.

    {{
      "reasoned_jobs": [
        {{
          "id": 1,
          "explanation": "string"
        }}
      ],
      "clarifying_question": "string"
    }}
    """

    response = generate_json_response(
        prompt
    )

    if "error" in response:

        logger.warning(
            "Using fallback reasoning"
        )

        return fallback_reasoning(
            candidate,
            jobs
        )

    return response


# =============================================================================
# MAIN RECOMMENDATION PIPELINE
# =============================================================================

def generate_recommendations(
    resume_text: str
) -> dict:

    top_jobs = rank_jobs(
        resume_text
    )

    candidate = extract_candidate_information(
        resume_text
    )

    reasoning = generate_reasoning(
        candidate,
        top_jobs
    )

    explanation_map = {

        item["id"]: item["explanation"]

        for item in reasoning.get(
            "reasoned_jobs",
            []
        )
    }

    ranked_jobs = []

    for job in top_jobs:

        ranked_jobs.append({

            "id": job["id"],

            "title": job["title"],

            "company": job["company"],

            "similarity_score":
                job["similarity_score"],

            "explanation":
                explanation_map.get(
                    job["id"],
                    job["explanation"]
                )
        })

    return {

        "candidate": candidate,

        "ranked_jobs": ranked_jobs,

        "clarifying_question":
            reasoning.get(
                "clarifying_question",
                "Would you prefer AI-focused engineering roles or backend-heavy development roles?"
            )
    }


# =============================================================================
# FALLBACK RERANKING
# =============================================================================

def fallback_refine_recommendations(
    resume_text: str,
    user_feedback: str
) -> dict:

    jobs = rank_jobs(
        resume_text
    )

    feedback = user_feedback.lower()

    for job in jobs:

        title = job["title"].lower()

        if "ai" in feedback:

            if "ai" in title or "ml" in title:

                job["similarity_score"] += 15

        if "backend" in feedback:

            if "backend" in title:

                job["similarity_score"] += 15

    jobs.sort(
        key=lambda x:
            x["similarity_score"],
        reverse=True
    )

    return {
        "ranked_jobs": jobs
    }


# =============================================================================
# RERANKING ENGINE
# =============================================================================

def refine_recommendations(
    resume_text: str,
    user_feedback: str
) -> dict:

    initial_jobs = rank_jobs(
        resume_text
    )

    prompt = f"""
    Resume:
    {resume_text}

    User Feedback:
    {user_feedback}

    Current Jobs:
    {json.dumps(initial_jobs, indent=2)}

    Re-rank jobs based on feedback.

    Return ONLY JSON.

    {{
      "ranked_jobs": [
        {{
          "id": 1,
          "similarity_score": 0.95,
          "explanation": "string"
        }}
      ]
    }}
    """

    response = generate_json_response(
        prompt
    )

    if "error" in response:

        logger.warning(
            "Using fallback reranking"
        )

        return fallback_refine_recommendations(
            resume_text,
            user_feedback
        )

    reranked_jobs = []

    for item in response["ranked_jobs"]:

        matched_job = next(

            (
                job for job in jobs_data
                if job["id"] == item["id"]
            ),

            None
        )

        if matched_job:

            reranked_jobs.append({

                "id": matched_job["id"],

                "title": matched_job["title"],

                "company": matched_job["company"],

                "similarity_score":
                    item.get(
                        "similarity_score",
                        0.8
                    ),

                "explanation":
                    item.get(
                        "explanation",
                        "Reranked"
                    )
            })

    return {
        "ranked_jobs": reranked_jobs
    }


# =============================================================================
# ASYNC HELPERS
# =============================================================================

async def async_generate_recommendations(
    resume_text: str
):

    return await asyncio.to_thread(
        generate_recommendations,
        resume_text
    )


async def async_refine_recommendations(
    resume_text: str,
    user_feedback: str
):

    return await asyncio.to_thread(
        refine_recommendations,
        resume_text,
        user_feedback
    )


# =============================================================================
# FASTAPI LIFESPAN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    load_jobs()

    yield


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(

    title="Smart Job Match API",

    version="5.0.0",

    lifespan=lifespan
)


# =============================================================================
# TEMPLATES
# =============================================================================

templates = Jinja2Templates(
    directory="templates"
)


# =============================================================================
# STATIC FILES
# =============================================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# =============================================================================
# RATE LIMITING
# =============================================================================

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)


# =============================================================================
# CORS
# =============================================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=[FRONTEND_URL],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# =============================================================================
# ROOT
# =============================================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def home(
    request: Request
):

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request
        }
    )


# =============================================================================
# HEALTH
# =============================================================================

@app.get("/health")
async def health_check():

    return {

        "status": "ok",

        "jobs_loaded":
            len(jobs_data),

        "gemini_enabled":
            client is not None
    }


# =============================================================================
# RECOMMEND
# =============================================================================

@app.post(
    "/recommend",
    response_model=RecommendResponse
)
@limiter.limit("10/minute")
async def recommend_jobs(
    request: Request,
    payload: RecommendRequest
):

    result = await async_generate_recommendations(
        payload.resume_text
    )

    return result


# =============================================================================
# REFINE
# =============================================================================

@app.post("/refine")
@limiter.limit("10/minute")
async def refine_jobs(
    request: Request,
    payload: RefineRequest
):

    result = await async_refine_recommendations(
        payload.resume_text,
        payload.user_feedback
    )

    return result


# =============================================================================
# DEBUG
# =============================================================================

@app.get("/debug")
async def debug():

    return {

        "dataset_loaded":
            len(jobs_data),

        "sample_job":
            jobs_data[0]
            if jobs_data
            else None
    }


# =============================================================================
# VERCEL HANDLER
# =============================================================================

handler = app


# =============================================================================
# LOCAL SERVER
# =============================================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )