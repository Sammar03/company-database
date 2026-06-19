"""Document endpoints: upload (ingest), list, delete."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from ..auth import require_api_key
from ..config import get_settings
from ..embeddings import embed_documents
from ..ingest import SUPPORTED_EXTENSIONS, parse_and_chunk
from ..models import (
    DeleteResponse,
    DocumentInfo,
    DocumentListResponse,
    IndexedDocument,
    IngestResponse,
)
from ..vectorstore import add_chunks, delete_document, list_documents

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_api_key)])
logger = logging.getLogger(__name__)


def _ext_ok(filename: str) -> bool:
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)


@router.post("", response_model=IngestResponse)
async def upload_documents(files: list[UploadFile]) -> IngestResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    settings = get_settings()
    if len(files) > settings.max_files_per_request:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files (max {settings.max_files_per_request} per request).",
        )
    max_bytes = settings.max_upload_mb * 1024 * 1024
    indexed: list[IndexedDocument] = []
    errors: list[str] = []

    for file in files:
        name = file.filename or "unnamed"
        if not _ext_ok(name):
            errors.append(f"{name}: unsupported file type (allowed: pdf, txt, md).")
            continue

        # Read at most max_bytes+1 so an oversized upload can't be materialised in
        # full in memory — we only need to know it exceeds the limit.
        data = await file.read(max_bytes + 1)
        if len(data) == 0:
            errors.append(f"{name}: empty file.")
            continue
        if len(data) > max_bytes:
            errors.append(f"{name}: exceeds {settings.max_upload_mb} MB limit.")
            continue

        try:
            chunks, pages = parse_and_chunk(
                name, data, settings.chunk_size, settings.chunk_overlap
            )
            if not chunks:
                errors.append(f"{name}: no extractable text (scanned PDF?).")
                continue
            if len(chunks) > settings.max_chunks_per_doc:
                errors.append(
                    f"{name}: too large to index ({len(chunks)} chunks; limit "
                    f"{settings.max_chunks_per_doc}). Split it into smaller files."
                )
                continue
            embeddings = embed_documents([c.text for c in chunks])
            # Replace any previous version of this file so re-uploads don't leave
            # stale chunks behind (ids are filename::index).
            delete_document(name)
            add_chunks(chunks, embeddings)
            indexed.append(IndexedDocument(filename=name, pages=pages, chunks=len(chunks)))
        except Exception:  # noqa: BLE001 — report per-file, keep going
            # Log the detail server-side; never leak internals to the client.
            logger.exception("Failed to ingest %s", name)
            errors.append(f"{name}: could not be processed.")

    return IngestResponse(indexed=indexed, errors=errors)


@router.get("", response_model=DocumentListResponse)
async def get_documents() -> DocumentListResponse:
    docs = [DocumentInfo(filename=name, chunks=count) for name, count in list_documents()]
    return DocumentListResponse(documents=docs)


@router.delete("/{filename}", response_model=DeleteResponse)
async def remove_document(filename: str) -> DeleteResponse:
    removed = delete_document(filename)
    if removed == 0:
        raise HTTPException(status_code=404, detail=f"Document not found: {filename}")
    return DeleteResponse(deleted=filename, removed_chunks=removed)
