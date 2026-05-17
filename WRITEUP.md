# WRITEUP

## 1. Design Choices

The system was designed as a lightweight AI-powered resume recommendation platform focused on fast iteration, explainability, and practical deployment within a constrained timeline. The recommendation engine combines deterministic ranking logic with optional LLM-based reasoning and reranking.

Initially, the plan was to use semantic embeddings using sentence-transformer models such as `all-MiniLM-L6-v2` or OpenAI embedding APIs. These models were considered because they provide significantly better semantic understanding compared to keyword matching and are commonly used in production recommendation pipelines. However, these approaches were rejected for this submission due to deployment complexity, inference overhead, and time limitations.

Instead, the final implementation uses a keyword-weighted ranking engine combined with Gemini-based reasoning. The ranking logic scores jobs by matching resume keywords against job titles, descriptions, and skills. This approach is computationally lightweight, fast to execute, and deterministic. The Gemini model is then used as an optional reasoning layer to:
- extract structured candidate information,
- generate job explanations,
- generate clarifying questions,
- rerank jobs based on user feedback.

A fallback architecture was intentionally added because free-tier Gemini quota limits can become unstable during live demos or deployment. If Gemini fails or exceeds quota, the system automatically switches to deterministic local logic. This trade-off sacrifices semantic depth but dramatically improves reliability.

The major trade-off made was accuracy versus robustness. A fully semantic vector-search architecture would likely improve ranking quality significantly, but the simpler deterministic approach reduced infrastructure requirements and ensured stable deployment under time constraints.

---

## 2. Agentic Architecture

The system follows a multi-stage agentic workflow rather than using one monolithic prompt. The architecture is intentionally modular.

### Workflow

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

The pipeline was split into multiple tool-like stages for several reasons.

The first stage performs candidate extraction and initial ranking. This stage transforms unstructured resume text into structured candidate attributes such as skills, education, preferred roles, and experience. Separating this stage makes the downstream reasoning process more controllable and easier to debug.

The second stage performs reasoning and clarifying question generation. Instead of generating final recommendations immediately, the agent asks a targeted follow-up question. This creates a more interactive recommendation flow and improves personalization.

The third stage reranks jobs using the user’s clarification. This mimics an iterative recommendation agent rather than a static search engine.

This design was preferred over a single large prompt because:
- prompts become easier to debug,
- failures become isolated,
- fallback logic becomes easier,
- token usage is reduced,
- individual stages can be replaced independently later.

Several failure modes still exist:
- incorrect skill extraction from noisy resumes,
- Gemini hallucinating malformed JSON,
- quota exhaustion,
- reranking bias caused by simplistic scoring,
- frontend/backend state desynchronization.

Additionally, because fallback logic is deterministic, recommendations can become less semantically accurate when Gemini is unavailable.

---

## 3. Honest Weaknesses

The system has several known weaknesses.

The largest weakness is resume quality sensitivity. Poorly formatted resumes, resumes with excessive graphics, missing skill sections, or ambiguous terminology can reduce ranking quality significantly. Since the fallback ranking engine is keyword-based, semantic understanding remains limited when Gemini is unavailable.

Another limitation is scalability. The current implementation stores data in memory and performs synchronous ranking logic without distributed caching or task queues. Under 10,000 concurrent requests, several bottlenecks would appear:
- Gemini API rate limiting,
- server memory pressure,
- blocking reranking operations,
- repeated dataset scans,
- frontend request congestion.

The system currently lacks:
- vector databases,
- Redis caching,
- async task queues,
- autoscaling infrastructure,
- persistent session management.

Several engineering shortcuts were taken due to time constraints. These include:
- using a static JSON dataset,
- simplified keyword ranking,
- no authentication,
- no database,
- limited frontend state management,
- no automated testing,
- no observability or tracing.

The fallback reasoning system is intentionally simplistic and exists primarily to ensure demo reliability during quota failures.

---

## 4. Next Steps

If two additional days were available, the single highest-impact improvement would be replacing keyword ranking with semantic vector retrieval using embeddings and a vector database.

Specifically, I would:
- generate embeddings for all job descriptions,
- store them in FAISS or Pinecone,
- generate resume embeddings dynamically,
- perform cosine similarity search before reranking.

This would improve recommendation quality dramatically because semantic retrieval handles:
- synonymous skills,
- contextual understanding,
- varied resume phrasing,
- domain-specific terminology.

For example, a keyword system may fail to associate “transformer pipelines” with NLP engineering, while embedding-based retrieval would likely succeed.

This improvement would have higher impact than frontend changes or UI polish because ranking quality directly determines the usefulness of the platform. It would also make the clarifying-question reranking stage significantly more intelligent by starting from stronger initial candidates.

Additionally, vector retrieval would create a cleaner path toward production scalability and future hybrid retrieval architectures combining embeddings, metadata filtering, and LLM reasoning.
