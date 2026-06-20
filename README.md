# Company Document RAG Assistant

Employees upload company documents (PDF / TXT / MD) into a shared vector store and **chat**
with them to get grounded, **cited** answers with multi-turn conversation history. Built as a
fast MVP per `prd.md`.

## Architecture

```
React/Vite frontend  ──REST──▶  FastAPI backend  ──▶  Neon Postgres + pgvector
                                       │
                                       ├──▶ Gemini  (embeddings: gemini-embedding-2, 768-dim)
                                       └──▶ Groq    (generation: llama-3.3-70b-versatile)
```

- **Frontend** (`/frontend`) and **backend** (`/backend`) are separate apps.
- Backend is **stateless** — the frontend sends recent conversation turns with each chat call.
- Vectors are stored in **Neon Postgres** via the `pgvector` extension, so the index is
  persistent and survives redeploys (no local disk / volume needed).
- Data flows one way: `upload → parse → chunk → embed → store → retrieve → answer`.

## Local setup

**Backend** (Python 3.11+) — runs on **port 8010**:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fill in GEMINI_API_KEY, GROQ_API_KEY, DATABASE_URL
uvicorn app.main:app --reload --port 8010
```

**Frontend** (Node 18+):

```bash
cd frontend
npm install
cp .env.example .env             # VITE_API_BASE=http://localhost:8010/api
npm run dev                      # http://localhost:5173
```

## Environment variables

### Backend (`backend/.env`)
| Var | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio key for embeddings (required) |
| `GROQ_API_KEY` | Groq key for generation (required) |
| `API_KEY` | Shared secret; clients must send it as `X-API-Key`. Empty = auth off (dev); **set in prod** |
| `ADMIN_KEY` | Admin secret for **deleting** documents (`X-Admin-Key`); never put in the frontend. Empty = delete open (dev) |
| `DATABASE_URL` | Neon Postgres connection string with `?sslmode=require` (required) |
| `EMBED_MODEL` / `EMBED_DIMS` | `gemini-embedding-2` / `768` |
| `GEN_MODEL` | `llama-3.3-70b-versatile` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` / `TOP_K` | `1000` / `150` / `5` |
| `MAX_UPLOAD_MB` / `MAX_CHUNKS_PER_DOC` / `MAX_FILES_PER_REQUEST` / `MAX_HISTORY_TURNS` | `25` / `1000` / `20` / `6` |
| `CORS_ORIGINS` | Comma-separated allowed origins (default `http://localhost:5173`; **set to your deployed frontend URL in prod**) |

### Frontend (`frontend/.env`)
| Var | Description |
|---|---|
| `VITE_API_BASE` | Backend API base, e.g. `http://localhost:8010/api` |
| `VITE_API_KEY` | Must match the backend `API_KEY` (empty if backend auth is off) |

## API (base `/api`)
`/documents` and `/chat` require the `X-API-Key` header when `API_KEY` is set. `/health` is open.
`DELETE` additionally requires the `X-Admin-Key` header when `ADMIN_KEY` is set (admin-only).
- `GET /health` → `{ status }` (lightweight liveness probe)
- `POST /documents` (multipart `files`) → `{ indexed, errors }` (any user)
- `GET /documents` → `{ documents }`
- `DELETE /documents/{filename}` → `{ deleted, removed_chunks }` (**admin only**)
- `POST /chat` → `{ answer, sources, grounded }`

## External dependencies
| Service | Role | Free tier | If it goes down |
|---|---|---|---|
| **Gemini** (`google-genai`) | Embeddings | Free tier with rate limits | Upload + chat fail with a clear error; cached index still listed |
| **Groq** | Answer generation | Free tier with rate limits | Chat returns a 429/500 with a friendly message; documents stay indexed |
| **Neon** (Postgres + pgvector) | Persistent vector store | Free tier, no credit card | Upload/chat fail with a clear error; data is safe in Neon |

## Deployment

### Database → Neon 
1. Create a project at [neon.tech](https://neon.tech) and a database.
2. Copy the connection string (keep `?sslmode=require`). The app auto-creates the
   `vector` extension, table, and indexes on first run — no manual migration.

### Backend → Hugging Face Spaces (Docker)
1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space) →
   **SDK: Docker** → blank template.
2. Push the **contents of `/backend`** to the Space repo (the `Dockerfile` and
   `backend/README.md` — whose YAML header sets `sdk: docker` and `app_port: 8000` —
   must sit at the Space repo root).
3. In the Space → **Settings → Variables and secrets**, add: `GEMINI_API_KEY`,
   `GROQ_API_KEY`, `DATABASE_URL` (Neon), `API_KEY` (a long random secret),
   `ADMIN_KEY` (a different secret, shared only with admins), and
   `CORS_ORIGINS=https://<your-frontend>.vercel.app`.
4. The Space builds the image and serves at `https://<user>-<space>.hf.space`.
   API base: `https://<user>-<space>.hf.space/api`. Health: `/api/health`.

> Free Spaces **sleep when idle** — the first request after a nap takes ~30–60s to wake.
> Nothing is lost (vectors are in Neon). Fine for an internal tool.

### Frontend → Vercel
1. New Vercel project, root `/frontend` (Vite auto-detected; `vercel.json` included).
2. Set `VITE_API_BASE=https://<user>-<space>.hf.space/api` and `VITE_API_KEY=<same as backend API_KEY>`.
3. Deploy — `npm run build` → `dist`.

