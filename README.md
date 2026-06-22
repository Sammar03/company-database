<a id="readme-top"></a>

# Knowledge Core

A company-document RAG assistant. Employees upload PDF, TXT, and Markdown files into a shared
knowledge base and chat with it to get answers that are grounded in those documents, cited to
the exact source, and aware of the conversation so far.

- **Live demo:** https://knowledge-core-tau.vercel.app
- Answers are drawn only from uploaded documents; when nothing relevant is found it says so
  rather than guessing.
- Anyone can upload; only an admin (holding a separate key) can delete documents.

<details>
  <summary>Table of contents</summary>

- [Built With](#built-with)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)

</details>

## Built With

**Frontend**
- React
- Vite
- TypeScript
- Tailwind CSS

**Backend**
- FastAPI
- PostgreSQL + pgvector (Neon)

**AI services**
- Google Gemini — text embeddings
- Groq — answer generation, reranking, and follow-up query rewriting

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

To get a local copy up and running, follow these steps. The backend and frontend are separate
apps and run on different ports (backend `8010`, frontend `5173`).

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
  ```sh
  npm install npm@latest -g
  ```
- Three free credentials:
  - A **Gemini** API key — https://aistudio.google.com/apikey
  - A **Groq** API key — https://console.groq.com/keys
  - A **Neon** Postgres connection string — https://neon.tech (use the pooled string, keep `?sslmode=require`)

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/Sammar03/Knowledge-Core.git
   cd Knowledge-Core
   ```
2. Set up the backend (from the repo root)
   ```sh
   cd backend
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   ```
3. Add your keys to `backend/.env`
   ```env
   GEMINI_API_KEY=your-gemini-key
   GROQ_API_KEY=your-groq-key
   DATABASE_URL=postgresql://user:password@your-host.neon.tech/neondb?sslmode=require
   ```
4. Run the backend (it auto-creates the pgvector table and index on first start)
   ```sh
   uvicorn app.main:app --reload --port 8010
   ```
5. Set up the frontend (in a second terminal, from the repo root)
   ```sh
   cd frontend
   npm install
   cp .env.example .env
   ```
6. Point the frontend at the backend in `frontend/.env`
   ```env
   VITE_API_BASE=http://localhost:8010/api
   ```
7. Run the frontend
   ```sh
   npm run dev                      # http://localhost:5173
   ```

> Optional: set `API_KEY` (and a matching `VITE_API_KEY`) plus `ADMIN_KEY` in the env files to
> turn on viewer auth and admin-only deletion. Left empty, both are disabled for local use.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

1. Open http://localhost:5173.
2. Upload one or more documents (PDF, TXT, MD) via the attach button or drag-and-drop. They are
   parsed, chunked, embedded, and stored in the shared knowledge base.
3. Ask a question in plain language. The answer is generated only from the uploaded documents
   and includes numbered citations — click a number to expand the exact source passage.
4. Ask follow-up questions; the assistant uses the conversation so far to stay on topic.
5. If an answer genuinely isn't in the documents, the assistant replies that it couldn't find it
   rather than inventing one.
6. To delete a document, enter the admin key (the **Admin** control in the sidebar); deletion is
   restricted to admins.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
