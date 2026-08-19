# ai-assistant

## What we did

This project is an AWS-first AI assistant with a React frontend and a
FastAPI backend. The current implementation includes:

- Created the monorepo structure for `frontend/` and `backend/`.
- Configured local development with Python virtual environment, FastAPI,
  Uvicorn, boto3 and automated tests.
- Configured Git/GitHub workflow and environment variables through `.env`
  and `.env.example`.
- Created an AWS development identity through IAM Identity Center with a
  dedicated developer user and development permissions.
- Created an AWS Budget alert for development cost monitoring.
- Created the S3 document bucket with server-side encryption and the
  `incoming/`, `processed/` and `failed/` prefixes.
- Implemented presigned S3 upload URLs so the frontend uploads documents
  without exposing AWS credentials.
- Implemented PDF processing, text extraction and chunk generation.
- Added local persistence for chat sessions and messages with SQLite.
- Added a vector-store abstraction with local and OpenSearch Serverless
  implementations.
- Created the OpenSearch Serverless vector collection and configured its
  data access policy for the IAM Identity Center role.
- Created the `ai-assistant-documents` index and the
  `ai-assistant-documents-bedrock-512` index.
- Added the Bedrock embedding provider using Titan Text Embeddings V2 with
  configurable vector dimensions.
- Reprocessed documents with real 512-dimensional embeddings and validated
  semantic search in OpenSearch.
- Implemented RAG search and document-processing endpoints.
- Automated document processing after a successful frontend upload, while
  keeping manual reprocessing available for retries.
- Added SQLite persistence for document processing state, attempts, errors,
  processed output and chunk counts.
- Added a maximum retry limit and the document status endpoint.
- Prepared an S3 `ObjectCreated` Lambda handler that reuses the backend
  document processor; deployment and queue wiring remain pending.
- Implemented an Orchestrator that selects the general or RAG route,
  identifies sources and delegates generation to the configured provider.
- Added a simulated provider for safe local development.
- Integrated Amazon Bedrock Converse with Amazon Nova Lite through the
  European inference profile `eu.amazon.nova-lite-v1:0`.
- Added controlled per-request provider selection, keeping `simulated` as
  the default to avoid accidental Bedrock usage.
- Validated the flow with backend tests, frontend build/lint and controlled
  AWS calls.

## Current status

- Real Bedrock text generation is working.
- OpenSearch RAG indexing is working.
- Bedrock embeddings with Titan V2 are working in the development index.
- The simulated embedding provider remains available as a local fallback.

## TODO

### Ingestion and document lifecycle

- Deploy the S3 event-driven workflow using Lambda and/or SQS for production.
- Migrate document and conversation persistence from SQLite to DynamoDB or
  another managed production database.
- Add a durable queue, exponential backoff and dead-letter handling for
  processing jobs.
- Add document deletion and re-indexing controls.

### RAG and assistant quality

- Improve chunking for semantic sections instead of fixed-size chunks only.
- Tune multilingual retrieval for Spanish tarot and dream-interpretation
  content.
- Add citations and clearer source references to assistant responses.
- Add evaluation queries and relevance metrics for RAG quality.

### Security and application features

- Add user authentication and authorization to FastAPI and React.
- Isolate documents, conversations and indexes by user or tenant.
- Add request validation, rate limiting and production CORS configuration.
- Implement the tarot-reading and dream-interpretation domain workflows.

### Operations and cost control

- Add structured logging, metrics and error monitoring.
- Add dashboards for S3, OpenSearch and Bedrock usage.
- Create cost simulations by volume of documents, chunks and conversations.
- Review and minimize IAM permissions before production.

### Deployment

- Containerize the backend and frontend.
- Define infrastructure as code.
- Deploy the API, frontend and asynchronous processing workflow.
- Add CI/CD, staging and production environments.
- Add backups, retention policies and disaster-recovery procedures.

## Environment variables

Configured in `.env` and documented in `.env.example`:

- `VITE_API_BASE_URL=http://localhost:8000`
- `FRONTEND_ORIGIN=http://localhost:5173`
- `AWS_REGION=eu-west-1`
- `S3_BUCKET_NAME=`
- `AI_PROVIDER=simulated`
- `VECTOR_STORE_BACKEND=opensearch`
- `OPENSEARCH_ENDPOINT=`
- `OPENSEARCH_INDEX=ai-assistant-documents`
- `OPENSEARCH_SERVICE=aoss`
- `BEDROCK_MODEL_ID=eu.amazon.nova-lite-v1:0`
- `BEDROCK_MAX_TOKENS=128`
- `BEDROCK_TEMPERATURE=0.2`
- `EMBEDDING_PROVIDER=simulated`
- `BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0`
- `EMBEDDING_DIMENSIONS=512`
