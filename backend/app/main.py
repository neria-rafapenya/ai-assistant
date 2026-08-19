from datetime import datetime
import json
from pathlib import PurePath
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.embeddings import SimulatedEmbeddingProvider
from app.ingestion import extract_chunks
from app.orchestrator import Orchestrator
from app.providers import SimulatedChatProvider
from app.settings import settings
from app.vector_index import LocalVectorIndex


class HealthResponse(BaseModel):
    status: str = "ok"
    aws_region: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str | None = None
    provider: str
    route: str = "general"
    sources: list[str] = Field(default_factory=list)


class DocumentItem(BaseModel):
    key: str
    size: int
    last_modified: datetime


class DocumentsResponse(BaseModel):
    documents: list[DocumentItem]


class UploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)


class UploadUrlResponse(BaseModel):
    upload_url: str
    key: str
    expires_in: int


class ProcessDocumentRequest(BaseModel):
    key: str = Field(min_length=len("incoming/"), max_length=1024)


class ProcessDocumentResponse(BaseModel):
    status: str
    source_key: str
    processed_key: str
    chunks: int
    indexed_chunks: int


class SearchResult(BaseModel):
    id: str
    source_key: str
    page: int
    text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


app = FastAPI(
    title="AI Assistant Backend",
    version="0.1.0",
)

chat_provider = SimulatedChatProvider()
embedding_provider = SimulatedEmbeddingProvider(settings.embedding_dimensions)
vector_index = LocalVectorIndex(settings.local_index_path, settings.embedding_dimensions)
orchestrator = Orchestrator(
    chat_provider=chat_provider,
    embedding_provider=embedding_provider,
    vector_store=vector_index,
)

s3_client = boto3.client(
    "s3",
    region_name=settings.aws_region,
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"},
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        aws_region=settings.aws_region,
    )


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        result = orchestrator.handle(payload.message)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Provider error",
        ) from exc

    return ChatResponse(
        reply=result.reply,
        session_id=payload.session_id,
        provider=result.provider,
        route=result.route,
        sources=result.sources,
    )


@app.get("/api/v1/documents", response_model=DocumentsResponse)
def list_documents() -> DocumentsResponse:
    if not settings.s3_bucket_name:
        raise HTTPException(
            status_code=503,
            detail="S3 bucket is not configured",
        )

    try:
        response = s3_client.list_objects_v2(
            Bucket=settings.s3_bucket_name,
            Prefix="incoming/",
        )
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not read documents from S3",
        ) from exc

    documents = [
        DocumentItem(
            key=item["Key"],
            size=item["Size"],
            last_modified=item["LastModified"],
        )
        for item in response.get("Contents", [])
        if not item["Key"].endswith("/")
    ]

    return DocumentsResponse(documents=documents)


@app.post("/api/v1/documents/upload-url", response_model=UploadUrlResponse)
def create_upload_url(payload: UploadUrlRequest) -> UploadUrlResponse:
    if not settings.s3_bucket_name:
        raise HTTPException(
            status_code=503,
            detail="S3 bucket is not configured",
        )

    if payload.content_type != "application/pdf":
        raise HTTPException(
            status_code=415,
            detail="Only PDF uploads are supported",
        )

    filename = PurePath(payload.filename).name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="The filename must have a .pdf extension",
        )

    key = f"incoming/{uuid4()}-{filename}"
    expires_in = 900

    try:
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": key,
                "ContentType": payload.content_type,
            },
            ExpiresIn=expires_in,
        )
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not create S3 upload URL",
        ) from exc

    return UploadUrlResponse(
        upload_url=upload_url,
        key=key,
        expires_in=expires_in,
    )


@app.post("/api/v1/documents/process", response_model=ProcessDocumentResponse)
def process_document(payload: ProcessDocumentRequest) -> ProcessDocumentResponse:
    if not settings.s3_bucket_name:
        raise HTTPException(
            status_code=503,
            detail="S3 bucket is not configured",
        )

    if not payload.key.startswith("incoming/") or not payload.key.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents inside incoming/ can be processed",
        )

    try:
        response = s3_client.get_object(
            Bucket=settings.s3_bucket_name,
            Key=payload.key,
        )
        pdf_bytes = response["Body"].read()
        chunks = extract_chunks(pdf_bytes)
    except (ClientError, BotoCoreError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not read or process the PDF from S3",
        ) from exc

    processed_key = f"processed/{PurePath(payload.key).stem}.json"
    processed_document = {
        "status": "processed",
        "source_key": payload.key,
        "chunks": chunks,
    }

    index_records = [
        {
            "id": f"{payload.key}#{chunk['chunk_id']}",
            "source_key": payload.key,
            "page": chunk["page"],
            "text": chunk["text"],
            "embedding": embedding_provider.embed(str(chunk["text"])),
        }
        for chunk in chunks
    ]
    vector_index.upsert(index_records)

    try:
        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=processed_key,
            Body=json.dumps(processed_document, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not save the processed document to S3",
        ) from exc

    return ProcessDocumentResponse(
        status="processed",
        source_key=payload.key,
        processed_key=processed_key,
        chunks=len(chunks),
        indexed_chunks=len(index_records),
    )


@app.get("/api/v1/rag/search", response_model=SearchResponse)
def search_rag(
    query: str = Query(min_length=1, max_length=4000),
    limit: int = Query(default=5, ge=1, le=20),
) -> SearchResponse:
    results = vector_index.search(embedding_provider.embed(query), limit)
    return SearchResponse(
        query=query,
        results=[SearchResult(**result) for result in results],
    )
