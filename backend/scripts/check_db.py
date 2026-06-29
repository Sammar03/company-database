from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg


def _vec(v: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


def _resolve_url() -> str | None:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip()
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    # Fall back to backend/.env
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        from dotenv import dotenv_values

        return dotenv_values(env_file).get("DATABASE_URL")
    return None


def main() -> int:
    url = _resolve_url()
    if not url:
        print("DATABASE_URL not set (pass it as an argument or set it in backend/.env).")
        return 1

    try:
        with psycopg.connect(url) as conn:
            version = conn.execute("SHOW server_version").fetchone()[0]
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            # Temp table auto-drops with the connection — leaves the DB untouched.
            conn.execute("CREATE TEMP TABLE _pgv_check (id int, embedding vector(3))")
            conn.execute(
                "INSERT INTO _pgv_check VALUES (1, %s::vector), (2, %s::vector)",
                (_vec([1.0, 0.0, 0.0]), _vec([0.0, 1.0, 0.0])),
            )
            rows = conn.execute(
                "SELECT id, 1 - (embedding <=> %s::vector) AS sim "
                "FROM _pgv_check ORDER BY embedding <=> %s::vector",
                (_vec([1.0, 0.0, 0.0]), _vec([1.0, 0.0, 0.0])),
            ).fetchall()
    except Exception as err:  # noqa: BLE001 — this is a diagnostic tool
        print(f"FAILED: {type(err).__name__}: {err}")
        return 1

    if not rows or rows[0][0] != 1:
        print(f"FAILED: unexpected query result {rows} (nearest to [1,0,0] should be id 1).")
        return 1

    print(
        f"OK — pgvector works. Postgres {version}. "
        f"Cosine search correct (nearest id={rows[0][0]}, sim={rows[0][1]:.3f})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
