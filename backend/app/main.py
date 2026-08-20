from datetime import date, datetime, timezone
import json
import logging
from pathlib import PurePath
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.embeddings import BedrockEmbeddingProvider, SimulatedEmbeddingProvider
from app.auth import AuthenticatedUser, get_current_user
from app.chat_repository import DynamoDBChatRepository, SQLiteChatRepository
from app.document_repository import DynamoDBDocumentRepository, SQLiteDocumentRepository
from app.ingestion import extract_chunks
from app.orchestrator import Orchestrator
from app.prompt_builder import PromptBuilder
from app.providers import BedrockChatProvider, ProviderManager, SimulatedChatProvider
from app.profile_repository import DynamoDBProfileRepository, SQLiteProfileRepository
from app.rag_service import RAGService
from app.settings import settings
from app.tarot import MAJOR_ARCANA, build_tarot_prompt
from app.tarot_repository import (
    DynamoDBTarotReadingRepository,
    SQLiteTarotReadingRepository,
    create_reading_record,
)
from app.vector_store import create_vector_store


logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str = "ok"
    aws_region: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    provider: str | None = Field(
        default=None,
        description=(
            "Proveedor opcional para esta petición. Si se omite, se usa "
            "AI_PROVIDER. Valores disponibles: simulated o bedrock."
        ),
    )


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


class DocumentStatusResponse(BaseModel):
    source_key: str
    status: str
    attempts: int
    processed_key: str | None = None
    chunks: int | None = None
    last_error: str | None = None


class SearchResult(BaseModel):
    id: str
    source_key: str
    page: int
    text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class UserProfileRequest(BaseModel):
    date_of_birth: date | None = None
    profession: str | None = Field(default=None, max_length=200)
    goals: list[str] = Field(default_factory=list, max_length=10)
    interests: list[str] = Field(default_factory=list, max_length=20)
    response_style: str | None = Field(default=None, max_length=50)
    topics_to_avoid: list[str] = Field(default_factory=list, max_length=20)
    health_conditions: str | None = Field(default=None, max_length=2000)
    health_data_consent: bool = False


class UserProfileResponse(UserProfileRequest):
    user_id: str
    age: int | None = None
    zodiac_sign: str | None = None
    health_data_consent_at: datetime | None = None
    onboarding_completed: bool


class TarotCardRequest(BaseModel):
    position: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=80)


class TarotReadRequest(BaseModel):
    question: str = Field(min_length=5, max_length=4000)
    spread: str = Field(pattern="^(one|three)$")
    style: str = Field(default="reflexivo", max_length=50)
    cards: list[TarotCardRequest] = Field(min_length=1, max_length=3)
    provider: str | None = None


class TarotReadResponse(BaseModel):
    reading_id: str
    created_at: datetime
    reading: str
    provider: str
    spread: str
    cards: list[TarotCardRequest]


class TarotReadingItem(TarotReadResponse):
    question: str
    style: str


class TarotReadingsResponse(BaseModel):
    readings: list[TarotReadingItem]


app = FastAPI(
    title="AI Assistant Backend",
    version="0.1.0",
)

chat_provider = SimulatedChatProvider()
if settings.embedding_provider == "bedrock":
    embedding_provider = BedrockEmbeddingProvider(
        region=settings.aws_region,
        model_id=settings.bedrock_embedding_model_id,
        dimensions=settings.embedding_dimensions,
    )
elif settings.embedding_provider == "simulated":
    embedding_provider = SimulatedEmbeddingProvider(settings.embedding_dimensions)
else:
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
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
if settings.persistence_backend == "dynamodb":
    chat_repository = DynamoDBChatRepository(
        settings.dynamodb_conversations_table_name,
        settings.aws_region,
    )
    document_repository = DynamoDBDocumentRepository(
        settings.dynamodb_documents_table_name,
        settings.aws_region,
    )
elif settings.persistence_backend == "sqlite":
    chat_repository = SQLiteChatRepository(settings.chat_database_path)
    document_repository = SQLiteDocumentRepository(settings.chat_database_path)
else:
    raise ValueError(f"Unknown persistence backend: {settings.persistence_backend}")

if settings.persistence_backend == "dynamodb":
    profile_repository = DynamoDBProfileRepository(
        settings.dynamodb_profiles_table_name,
        settings.aws_region,
    )
else:
    profile_repository = SQLiteProfileRepository(settings.chat_database_path)

if settings.persistence_backend == "dynamodb":
    tarot_reading_repository = DynamoDBTarotReadingRepository(
        settings.dynamodb_tarot_readings_table_name,
        settings.aws_region,
    )
else:
    tarot_reading_repository = SQLiteTarotReadingRepository(settings.chat_database_path)

s3_client = boto3.client(
    "s3",
    region_name=settings.aws_region,
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"},
    ),
)


allowed_origins = [
    origin.strip()
    for origin in settings.frontend_origin.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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


def calculate_age(date_of_birth: date | None) -> int | None:
    if date_of_birth is None:
        return None
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def calculate_zodiac_sign(date_of_birth: date | None) -> str | None:
    if date_of_birth is None:
        return None
    month_day = (date_of_birth.month, date_of_birth.day)
    boundaries = [
        ((1, 20), "Acuario"), ((2, 19), "Piscis"), ((3, 21), "Aries"),
        ((4, 20), "Tauro"), ((5, 21), "Géminis"), ((6, 21), "Cáncer"),
        ((7, 23), "Leo"), ((8, 23), "Virgo"), ((9, 23), "Libra"),
        ((10, 23), "Escorpio"), ((11, 22), "Sagitario"), ((12, 22), "Capricornio"),
    ]
    for boundary, sign in reversed(boundaries):
        if month_day >= boundary:
            return sign
    return "Capricornio"


def serialize_profile(user_id: str, profile: dict) -> UserProfileResponse:
    date_of_birth = (
        date.fromisoformat(profile["date_of_birth"])
        if profile.get("date_of_birth")
        else None
    )
    return UserProfileResponse(
        user_id=user_id,
        date_of_birth=date_of_birth,
        profession=profile.get("profession"),
        goals=profile.get("goals", []),
        interests=profile.get("interests", []),
        response_style=profile.get("response_style"),
        topics_to_avoid=profile.get("topics_to_avoid", []),
        health_conditions=profile.get("health_conditions"),
        health_data_consent=profile.get("health_data_consent", False),
        health_data_consent_at=profile.get("health_data_consent_at"),
        age=calculate_age(date_of_birth),
        zodiac_sign=calculate_zodiac_sign(date_of_birth),
        onboarding_completed=bool(profile.get("date_of_birth") and profile.get("profession")),
    )


@app.get("/api/v1/profile", response_model=UserProfileResponse, tags=["Profile"])
def get_profile(current_user: AuthenticatedUser = Depends(get_current_user)) -> UserProfileResponse:
    profile = profile_repository.get(current_user.sub) or {}
    return serialize_profile(current_user.sub, profile)


@app.put("/api/v1/profile", response_model=UserProfileResponse, tags=["Profile"])
def save_profile(
    payload: UserProfileRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> UserProfileResponse:
    if payload.health_conditions and not payload.health_data_consent:
        raise HTTPException(
            status_code=422,
            detail="Explicit consent is required to store health information",
        )

    profile = payload.model_dump(mode="json")
    existing = profile_repository.get(current_user.sub) or {}
    if payload.health_data_consent:
        profile["health_data_consent_at"] = existing.get(
            "health_data_consent_at",
            datetime.now(timezone.utc).isoformat(),
        )
    else:
        profile["health_conditions"] = None
        profile["health_data_consent_at"] = None

    profile_repository.save(current_user.sub, profile)
    return serialize_profile(current_user.sub, profile)


@app.post("/api/v1/tarot/read", response_model=TarotReadResponse, tags=["Tarot"])
def tarot_read(
    payload: TarotReadRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TarotReadResponse:
    expected_count = 1 if payload.spread == "one" else 3
    if len(payload.cards) != expected_count:
        raise HTTPException(
            status_code=422,
            detail=f"The {payload.spread} spread requires {expected_count} card(s)",
        )

    if len({card.name for card in payload.cards}) != len(payload.cards):
        raise HTTPException(status_code=422, detail="Cards must be unique")

    unknown_cards = [card.name for card in payload.cards if card.name not in MAJOR_ARCANA]
    if unknown_cards:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown tarot card(s): {', '.join(unknown_cards)}",
        )

    profile = profile_repository.get(current_user.sub) or {}
    prompt = build_tarot_prompt(
        question=payload.question.strip(),
        spread=payload.spread,
        cards=[card.model_dump() for card in payload.cards],
        style=payload.style,
        profile=profile,
    )
    try:
        result = provider_manager.generate_reply(prompt, provider_name=payload.provider)
    except Exception as exc:
        logger.exception("Could not generate tarot reading")
        raise HTTPException(status_code=502, detail=f"Provider error: {exc}") from exc

    record = create_reading_record(
        question=payload.question.strip(),
        spread=payload.spread,
        style=payload.style,
        cards=[card.model_dump() for card in payload.cards],
        reading=result.reply,
        provider=result.provider,
    )
    try:
        tarot_reading_repository.save(current_user.sub, record)
    except Exception as exc:
        logger.exception("Could not persist tarot reading")
        raise HTTPException(status_code=502, detail="Could not save tarot reading") from exc

    return TarotReadResponse(
        reading_id=record["reading_id"],
        created_at=record["created_at"],
        reading=result.reply,
        provider=result.provider,
        spread=payload.spread,
        cards=payload.cards,
    )


@app.get("/api/v1/tarot/readings", response_model=TarotReadingsResponse, tags=["Tarot"])
def list_tarot_readings(
    limit: int = Query(default=20, ge=1, le=50),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TarotReadingsResponse:
    try:
        readings = tarot_reading_repository.list_for_user(current_user.sub, limit)
    except Exception as exc:
        logger.exception("Could not list tarot readings")
        raise HTTPException(status_code=502, detail="Could not load tarot readings") from exc
    return TarotReadingsResponse(readings=readings)


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
def chat(
    payload: ChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ChatResponse:
    session_id = payload.session_id or str(uuid4())
    try:
        result = orchestrator.handle(payload.message, provider_name=payload.provider)
    except Exception as exc:
        logger.exception("Could not generate chat response")
        raise HTTPException(
            status_code=502,
            detail=f"Provider error: {exc}",
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
def get_chat_history(
    session_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ChatHistoryResponse:
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
def list_documents(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DocumentsResponse:
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
def create_upload_url(
    payload: UploadUrlRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> UploadUrlResponse:
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
def process_document(
    payload: ProcessDocumentRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ProcessDocumentResponse:
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

    if not document_repository.start_processing(payload.key):
        raise HTTPException(status_code=409, detail="Maximum processing attempts reached")

    try:
        response = s3_client.get_object(
            Bucket=settings.s3_bucket_name,
            Key=payload.key,
        )
        pdf_bytes = response["Body"].read()
        chunks = extract_chunks(pdf_bytes)
    except (ClientError, BotoCoreError, ValueError) as exc:
        document_repository.mark_failed(payload.key, str(exc))
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
        document_repository.mark_failed(payload.key, str(exc))
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
        document_repository.mark_failed(payload.key, str(exc))
        raise HTTPException(
            status_code=502,
            detail="Could not save the processed document to S3",
        ) from exc

    document_repository.mark_completed(payload.key, processed_key, len(chunks))

    return ProcessDocumentResponse(
        status="processed",
        source_key=payload.key,
        processed_key=processed_key,
        chunks=len(chunks),
        indexed_chunks=len(index_records),
    )


@app.get(
    "/api/v1/documents/{document_key:path}/status",
    response_model=DocumentStatusResponse,
    summary="Consultar el estado de procesamiento",
    tags=["Documents"],
)
def document_status(
    document_key: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DocumentStatusResponse:
    document = document_repository.get(document_key)
    if document is None:
        raise HTTPException(status_code=404, detail="Document status not found")
    return DocumentStatusResponse(**{
        "source_key": document["source_key"], "status": document["status"],
        "attempts": document["attempts"], "processed_key": document["processed_key"],
        "chunks": document["chunks"], "last_error": document["last_error"],
    })


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
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> SearchResponse:
    results = vector_index.search(embedding_provider.embed(query), limit)
    return SearchResponse(
        query=query,
        results=[SearchResult(**result) for result in results],
    )
