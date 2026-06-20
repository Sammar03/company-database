---
title: Company Database API
emoji: 📄
colorFrom: gray
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# Company Database — Backend API

FastAPI RAG backend: Gemini embeddings + Groq generation (with a Groq reranker) +
Neon Postgres/pgvector. Built from the `Dockerfile` in this directory.

This file's YAML header configures the Hugging Face Space (Docker SDK, port 8000).
See the repo-root `README.md` for full architecture and local-dev docs.

## Required Space secrets
Set these under **Settings → Variables and secrets** (not in code):

- `GEMINI_API_KEY` — Google AI Studio key (embeddings)
- `GROQ_API_KEY` — Groq key (generation + reranking)
- `DATABASE_URL` — Neon Postgres connection string (keep `?sslmode=require`)
- `API_KEY` — long random shared secret; clients must send it as `X-API-Key`
- `ADMIN_KEY` — separate secret for deleting documents (`X-Admin-Key`); admins only, never in the frontend
- `CORS_ORIGINS` — your deployed frontend origin, e.g. `https://your-app.vercel.app`

Health check: `GET /api/health` → `{"status":"ok"}`. API base: `/api`.
