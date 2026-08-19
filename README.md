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
- Created the `ai-assistant-documents` index and indexed processed chunks.
- Implemented RAG search and document-processing endpoints.
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
- Embeddings are still simulated in the current implementation.
- Bedrock embeddings with Amazon Titan Text Embeddings V2 are the next
  planned phase.

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
