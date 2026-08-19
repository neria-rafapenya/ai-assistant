from datetime import datetime
import json
import logging
from pathlib import PurePath
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.embeddings import SimulatedEmbeddingProvider
from app.chat_repository import SQLiteChatRepository
from app.ingestion import extract_chunks
from app.orchestrator import Orchestrator
from app.prompt_builder import PromptBuilder
from app.providers import BedrockChatProvider, ProviderManager, SimulatedChatProvider
from app.rag_service import RAGService
from app.settings import settings
from app.vector_store import create_vector_store


logger = logging.getLogger(__name__)


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


class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    provider: str | None = None
    route: str | None = None
    sources: list[str] = Field(default_factory=list)
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageResponse]


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
vector_index = create_vector_store(
    backend=settings.vector_store_backend,
    local_index_path=settings.local_index_path,
    dimensions=settings.embedding_dimensions,
    opensearch_endpoint=settings.opensearch_endpoint,
    opensearch_index=settings.opensearch_index,
    aws_region=settings.aws_region,
    opensearch_service=settings.opensearch_service,
)
providers = {"simulated": chat_provider}
if settings.bedrock_model_id:
    providers["bedrock"] = BedrockChatProvider(
        region=settings.aws_region,
        model_id=settings.bedrock_model_id,
        max_tokens=settings.bedrock_max_tokens,
        temperature=settings.bedrock_temperature,
    )
provider_manager = ProviderManager(providers, default_provider=settings.ai_provider)
rag_service = RAGService(embedding_provider, vector_index)
prompt_builder = PromptBuilder()
orchestrator = Orchestrator(
    provider_manager=provider_manager,
    rag_service=rag_service,
    prompt_builder=prompt_builder,
)
chat_repository = SQLiteChatRepository(settings.chat_database_path)

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


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Comprobar el estado del backend",
    description=(
        "Verifica que la API está activa y devuelve la región de AWS "
        "configurada para el entorno actual."
    ),
    tags=["System"],
)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        aws_region=settings.aws_region,
    )


@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    summary="Enviar un mensaje al asistente",
    description=(
        "Envía una consulta al Orchestrator. El Orchestrator decide si debe "
        "usar la ruta general o la ruta RAG y devuelve la respuesta junto "
        "con el proveedor, la ruta y las fuentes utilizadas."
    ),
    tags=["Chat"],
)
def chat(payload: ChatRequest) -> ChatResponse:
    session_id = payload.session_id or str(uuid4())
    try:
        result = orchestrator.handle(payload.message)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Provider error",
        ) from exc

    chat_repository.save_message(
        session_id=session_id,
        role="user",
        content=payload.message,
    )
    chat_repository.save_message(
        session_id=session_id,
        role="assistant",
        content=result.reply,
        provider=result.provider,
        route=result.route,
        sources=result.sources,
    )

    return ChatResponse(
        reply=result.reply,
        session_id=session_id,
        provider=result.provider,
        route=result.route,
        sources=result.sources,
    )


@app.get(
    "/api/v1/chat/{session_id}/messages",
    response_model=ChatHistoryResponse,
    summary="Recuperar el historial de una sesión",
    description=(
        "Devuelve los mensajes persistidos de una sesión de chat en orden "
        "cronológico."
    ),
    tags=["Chat"],
)
def get_chat_history(session_id: str) -> ChatHistoryResponse:
    messages = chat_repository.list_messages(session_id)
    return ChatHistoryResponse(session_id=session_id, messages=messages)


@app.get(
    "/api/v1/documents",
    response_model=DocumentsResponse,
    summary="Listar documentos de entrada",
    description=(
        "Obtiene desde Amazon S3 los documentos disponibles bajo el prefijo "
        "incoming/."
    ),
    tags=["Documents"],
)
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


@app.post(
    "/api/v1/documents/upload-url",
    response_model=UploadUrlResponse,
    summary="Generar una URL prefirmada de subida",
    description=(
        "Genera una URL temporal para que el frontend pueda subir "
        "directamente un PDF a Amazon S3 sin exponer credenciales AWS. "
        "El objeto se crea bajo incoming/."
    ),
    tags=["Documents"],
)
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


@app.post(
    "/api/v1/documents/process",
    response_model=ProcessDocumentResponse,
    summary="Procesar un documento PDF",
    description=(
        "Descarga un PDF desde incoming/ en Amazon S3, extrae sus fragmentos, "
        "los indexa en el índice local y guarda el resultado bajo processed/."
    ),
    tags=["Documents"],
)
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
    try:
        vector_index.upsert(index_records)
    except Exception as exc:
        logger.exception("Could not index document in OpenSearch")
        raise HTTPException(
            status_code=502,
            detail=f"Could not index the processed document in OpenSearch: {exc}",
        ) from exc

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


@app.get(
    "/api/v1/rag/search",
    response_model=SearchResponse,
    summary="Buscar contexto en el índice RAG",
    description=(
        "Busca los fragmentos más relevantes para una consulta usando el "
        "índice vectorial local actual. Estos resultados sirven como contexto "
        "para la ruta RAG del Orchestrator."
    ),
    tags=["RAG"],
)
def search_rag(
    query: str = Query(min_length=1, max_length=4000),
    limit: int = Query(default=5, ge=1, le=20),
) -> SearchResponse:
    results = vector_index.search(embedding_provider.embed(query), limit)
    return SearchResponse(
        query=query,
        results=[SearchResult(**result) for result in results],
    )
