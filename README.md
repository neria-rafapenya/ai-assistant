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
- Created the DynamoDB development tables for documents and conversations.
- Added DynamoDB repository implementations with SQLite retained as the local
  fallback, selected through `PERSISTENCE_BACKEND`.
- Validated document processing state persistence in DynamoDB from Lambda.
- Validated chat message persistence in DynamoDB with the FastAPI backend.
- Added a GitHub Actions CI workflow that runs backend tests and frontend
  lint/build checks on pushes to `main` and pull requests.
- Added a GitHub Actions CD workflow that publishes the API image to ECR,
  forces an ECS deployment, uploads the frontend to S3 and invalidates
  CloudFront.
- Created the GitHub OIDC identity provider and the dedicated IAM role
  `github-actions-deploy-role` for deployments from the `main` branch of
  `neria-rafapenya/ai-assistant`.
- Added a separate `backend/Dockerfile.backend` for serving the FastAPI API;
  the existing `Dockerfile.lambda` remains dedicated to document jobs.
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
  document processor.
- Prepared a Lambda container image definition with the backend runtime
  dependencies.
- Created the ECR repository `ai-assistant-document-processor` in
  `eu-west-1`.
- Built, tagged and published the Lambda container image to ECR. The image
  was rebuilt for the Lambda-compatible `linux/amd64` platform.
- Created the Lambda function `ai-assistant-document-processor` from the ECR
  image and configured its execution role.
- Configured S3 to publish PDF creation events from `incoming/` to SQS.
- Configured Lambda to consume the SQS queue with a 60-second timeout and
  1024 MB of memory.
- Added an SQS standard queue and dead-letter queue between S3 and Lambda.
- Updated the Lambda handler to process SQS-wrapped S3 notifications.
- Validated the S3 → SQS → Lambda document-processing flow.
- Implemented an Orchestrator that selects the general or RAG route,
  identifies sources and delegates generation to the configured provider.
- Added a simulated provider for safe local development.
- Integrated Amazon Bedrock Converse with Amazon Nova Lite through the
  European inference profile `eu.amazon.nova-lite-v1:0`.
- Added controlled per-request provider selection, keeping `simulated` as
  the default to avoid accidental Bedrock usage.
- Validated the flow with backend tests, frontend build/lint and controlled
  AWS calls.
- Created the Cognito User Pool `eu-west-1_5fX8JYeKk` and the public SPA app
  client `ai-assistant-web`.
- Configured Cognito managed login for the CloudFront and localhost callback
  and sign-out URLs with the Authorization Code flow.
- Validated the Cognito OIDC login flow locally from `http://localhost:5173/`.
- Registered both local and CloudFront callback and sign-out URLs in the
  Cognito app client.
- Integrated OIDC login/logout in React and protected the Tarot, Sueños and
  Historial routes while keeping `/dev` available for technical testing.
- Added backend validation for Cognito access tokens and user identification
  through the immutable `sub` claim.
- Updated frontend API calls to send the authenticated bearer token.
- Added the authenticated profile API and a three-step profile wizard at
  `/perfil`.
- Added profile fields for date of birth, profession, goals, interests,
  response style and topics to avoid. Age and zodiac sign are derived by the
  backend.
- Added optional health information with explicit consent validation. Health
  information is not stored unless the user gives consent.
- Added SQLite and DynamoDB profile repositories. The development DynamoDB
  table is `ai-assistant-profiles-dev` with `user_id` as its partition key.
- Configured ECS CORS for both the CloudFront and localhost origins.
- Updated CD to deploy the API through ECS Express Mode using the commit SHA
  image tag.
- Added authenticated daily usage limits: 5 tarot readings and 20 assistant
  queries per user. Limits are enforced in the backend before Bedrock is
  invoked and can be bypassed only for explicitly configured sandbox users.
- Added a DynamoDB usage-counter repository with atomic updates and a
  `GET /api/v1/usage` endpoint for frontend notices.

## Current status

- Real Bedrock text generation is working.
- OpenSearch RAG indexing is working.
- Bedrock embeddings with Titan V2 are working in the development index.
- The simulated embedding provider remains available as a local fallback.
- Automatic S3-to-SQS-to-Lambda PDF processing is working in the development
  account.
- The FastAPI backend is deployed on Amazon ECS Express Mode.
- The React frontend is deployed to S3 and served through the enabled
  CloudFront distribution.
- ECS runtime access is configured through `ecsTaskExecutionRole` for S3,
  Bedrock, OpenSearch Serverless and DynamoDB.
- The API profile endpoint is deployed and the profile table is active in
  DynamoDB.
- The usage table `ai-assistant-usage-dev` is active in DynamoDB. The ECS task
  role still needs `dynamodb:UpdateItem` on that table before enabling the new
  backend image.
- The public frontend URL is `https://d38nzp4j8k9sdf.cloudfront.net`.
- The public backend URL is
  `https://ai-5428103d948647f2ac9aa11b2ba6f07a.ecs.eu-west-1.on.aws`.
- A custom domain has not been configured yet.

## TODO

### Ingestion and document lifecycle

- Add backups, retention and production data-management policies for the
  DynamoDB tables.
- Add usage dashboards and a product decision for paid plans or monthly
  quotas.
- Add explicit retry/backoff observability and operational alerts for
  processing jobs.
- Add document deletion and re-indexing controls.

### RAG and assistant quality

- Improve chunking for semantic sections instead of fixed-size chunks only.
- Tune multilingual retrieval for Spanish tarot and dream-interpretation
  content.
- Add citations and clearer source references to assistant responses.
- Add evaluation queries and relevance metrics for RAG quality.

### Security and application features

- Associate conversations, documents and vector-index records with the
  authenticated Cognito `sub` and enforce per-user access.
- Load the authenticated user's profile into the prompt context for relevant
  chat and tarot interactions.
- Add profile deletion, consent revocation, retention and audit controls.
- Review the legal basis, privacy notice and data-protection requirements for
  optional health information before enabling production use.
- Add request validation, rate limiting and production security monitoring.
- Implement the tarot-reading and dream-interpretation domain workflows.

### Operations and cost control

- Add structured logging, metrics and error monitoring.
- Add dashboards for S3, OpenSearch and Bedrock usage.
- Create cost simulations by volume of documents, chunks and conversations.
- Review and minimize IAM permissions before production.

### Deployment

- Add staging and production CD environments.
- Validate the first GitHub Actions CD run end to end using the OIDC role,
  repository secret and CloudFront distribution variable.
- Define infrastructure as code.
- Add backups, retention policies and disaster-recovery procedures.

## Deployment commands

The commands below assume that Docker Desktop is running, the AWS CLI is
configured with the `ai-assistant-dev` SSO profile, and AWS resources are in
`eu-west-1`.

### Common deployment setup

```bash
cd /Users/rafa_penya/Documents/GitHub/ai-assistant
source .venv/bin/activate
export AWS_PROFILE=ai-assistant-dev
export AWS_REGION=eu-west-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity \
  --profile ai-assistant-dev \
  --query Account \
  --output text)

aws sso login --profile ai-assistant-dev
aws sts get-caller-identity --profile ai-assistant-dev
```

Authenticate Docker against ECR:

```bash
aws ecr get-login-password \
  --region eu-west-1 \
  --profile ai-assistant-dev \
  | docker login \
  --username AWS \
  --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com
```

### Lambda document processor

The document processor is prepared as a Lambda container image using
`backend/Dockerfile.lambda`. The following procedure builds the image and
publishes it to Amazon ECR in `eu-west-1`.

### Prerequisites

- Docker Desktop must be running.
- AWS CLI must be configured with the `ai-assistant-dev` SSO profile.
- The current directory must be `backend/`.

Check Docker before building:

```bash
docker info
```

If Docker is not running on macOS:

```bash
open -a Docker
```

### Build and publish

```bash
cd /Users/rafa_penya/Documents/GitHub/ai-assistant/backend
```

Create the ECR repository once:

```bash
aws ecr create-repository \
  --repository-name ai-assistant-document-processor \
  --image-scanning-configuration scanOnPush \
  --region eu-west-1 \
  --profile ai-assistant-dev
```

Build the Lambda image:

```bash
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  --load \
  -f Dockerfile.lambda \
  -t ai-assistant-document-processor:latest \
  .
```

Tag and publish the image:

```bash
docker tag \
  ai-assistant-document-processor:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-document-processor:latest

docker push \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-document-processor:latest
```

Update the existing Lambda function to the newly published image:

```bash
aws lambda update-function-code \
  --function-name ai-assistant-document-processor \
  --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-document-processor:latest \
  --region eu-west-1 \
  --profile ai-assistant-dev
```

Verify the asynchronous pipeline after uploading a PDF:

```bash
aws s3 cp /ruta/al/documento.pdf \
  s3://ai-assistant-documents-dev-740862652747/incoming/deploy-test.pdf \
  --profile ai-assistant-dev \
  --region eu-west-1

aws logs tail /aws/lambda/ai-assistant-document-processor \
  --since 15m \
  --profile ai-assistant-dev \
  --region eu-west-1

aws s3 ls s3://ai-assistant-documents-dev-740862652747/processed/ \
  --profile ai-assistant-dev \
  --region eu-west-1
```

The Lambda function, S3 notification, SQS trigger and execution role were
created/configured in the AWS Console. The commands above publish and update
the deployable image and verify the resulting flow.

### FastAPI backend image

The HTTP API uses `backend/Dockerfile.backend`, separate from the Lambda
processor image. Create its ECR repository once:

```bash
cd /Users/rafa_penya/Documents/GitHub/ai-assistant/backend

aws ecr create-repository \
  --repository-name ai-assistant-api \
  --image-scanning-configuration scanOnPush \
  --region eu-west-1 \
  --profile ai-assistant-dev
```

Build and publish the API image:

```bash
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  --load \
  -f Dockerfile.backend \
  -t ai-assistant-api:latest \
  .

docker tag ai-assistant-api:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-api:latest

docker push \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-api:latest
```

The API image is deployed through Amazon ECS Express Mode. The service uses
the `ecsTaskExecutionRole` and an ECS Express infrastructure role. The runtime
role has access to the S3 document bucket, Bedrock model invocation, the
OpenSearch Serverless collection and both DynamoDB tables.

The image has been built and published successfully. The Lambda function,
SQS trigger, S3 notification and DynamoDB document persistence are now
working in the development account. Chat persistence has also been validated
against DynamoDB from the FastAPI backend.
The ECR image is the deployment artifact; it is not a public application
domain.

## Frontend deployment to S3

The React frontend is deployed separately from the Docker-based backend. Each
frontend release is built and synchronized to the private S3 bucket
`ai-assistant-frontend-dev-740862652747`, then served publicly through
CloudFront.

### Build and upload a frontend release

Run from `frontend/`:

```bash
cd /Users/rafa_penya/Documents/GitHub/ai-assistant/frontend

# Vite reads VITE_API_BASE_URL from the root .env file.
npm run build

aws s3 sync dist/ \
  s3://ai-assistant-frontend-dev-740862652747/ \
  --profile ai-assistant-dev \
  --region eu-west-1
```

The upload is repeatable: run the same commands after each frontend change.
The bucket is private; CloudFront is the public distribution layer. Invalidate
its cache after a release when needed:

```bash
aws cloudfront create-invalidation \
  --distribution-id DISTRIBUTION_ID \
  --paths "/*" \
  --profile ai-assistant-dev
```

### GitHub Actions CD configuration

The workflow `.github/workflows/deploy.yml` runs on pushes to `main` and can
also be started manually. Configure these GitHub repository values before
using it:

- GitHub Environment `dev`: the deploy job runs in this environment so OIDC
  trust policies scoped to `repo:neria-rafapenya/ai-assistant:environment:dev`
  can assume the AWS role.
- Secret `AWS_DEPLOY_ROLE_ARN`: IAM role trusted by GitHub Actions through
  OIDC, with permissions for ECR push, ECS deployment, S3 frontend upload and
  CloudFront invalidation.
- Variable `CLOUDFRONT_DISTRIBUTION_ID`: current distribution ID
  `E2B4Q04OL4DTCN`.
- The secret contains only the ARN of `github-actions-deploy-role`; no AWS
  access keys are stored in GitHub.

The workflow builds React with the public ECS API URL, publishes the API
image, updates the ECS Express Mode service with the commit SHA image tag,
uploads `frontend/dist/` to S3 and invalidates CloudFront. The ECS
`FRONTEND_ORIGIN` configuration must allow both the
deployed frontend and the local development frontend:

```text
https://d38nzp4j8k9sdf.cloudfront.net,http://localhost:5173
```

The origins must be written without trailing slashes. After changing an ECS
environment variable, wait for the new deployment to reach `Running` before
testing the API from the browser.

The usage table has been created in the development account:

```text
arn:aws:dynamodb:eu-west-1:740862652747:table/ai-assistant-usage-dev
```

Add this statement to the existing policy attached to `ecsTaskExecutionRole`
(the current ECS service uses that role as its task role too):

```json
{
  "Effect": "Allow",
  "Action": "dynamodb:UpdateItem",
  "Resource": "arn:aws:dynamodb:eu-west-1:740862652747:table/ai-assistant-usage-dev"
}
```

The deploy workflow preserves the current ECS environment and adds the usage
configuration automatically: `DAILY_TAROT_LIMIT=5`, `DAILY_CHAT_LIMIT=20`,
`DYNAMODB_USAGE_TABLE_NAME=ai-assistant-usage-dev` and the configured sandbox
email. The sandbox email is for development only and must be removed before
production.

The S3 document bucket must also allow this CloudFront origin for browser
uploads using presigned URLs. S3 accepts `PUT`, `GET` and `HEAD` in
`AllowedMethods`; `OPTIONS` must not be added to the S3 CORS method list.

For the current local-to-remote API test, use this value in `.env` before the
build:

```env
VITE_API_BASE_URL=https://ai-5428103d948647f2ac9aa11b2ba6f07a.ecs.eu-west-1.on.aws
```

## Current URLs and public domain

The application currently runs locally:

- Local backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`

The deployed backend API is available at:

```text
https://ai-5428103d948647f2ac9aa11b2ba6f07a.ecs.eu-west-1.on.aws
```

Health check:

```text
https://ai-5428103d948647f2ac9aa11b2ba6f07a.ecs.eu-west-1.on.aws/health
```

### Local Cognito login

The Cognito User Pool is `eu-west-1_5fX8JYeKk` and the SPA app client is
`ai-assistant-web`. Its allowed callback and sign-out URLs are:

```text
http://localhost:5173/
https://d38nzp4j8k9sdf.cloudfront.net/
```

The local `.env` file is stored at the repository root. Vite is configured to
read it from the frontend project through `envDir: ".."` in
`frontend/vite.config.ts`:

```env
VITE_COGNITO_ISSUER=https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_5fX8JYeKk
VITE_COGNITO_CLIENT_ID=4086ign9h6tpj0r5o1mhhab74n
VITE_COGNITO_REDIRECT_URI=http://localhost:5173/
VITE_COGNITO_LOGOUT_URI=http://localhost:5173/
```

Start the frontend from `frontend/`:

```bash
npm run dev
```

If the browser continues using an old OAuth configuration, stop the dev
server and restart Vite with a clean dependency cache:

```bash
npm run dev -- --force
```

## Demo validation from CloudFront

Use the public frontend URL for the end-to-end test:

1. Open `https://d38nzp4j8k9sdf.cloudfront.net`.
2. Upload a real PDF and verify that it appears in S3 under `incoming/`.
3. Process the document and verify the JSON appears under `processed/`.
4. Search for text contained in the PDF and verify the OpenSearch results.
5. Send a chat message and verify the Bedrock response and sources.

The upload uses a presigned S3 URL. If the browser reports a CORS error,
verify that the documents bucket allows the exact CloudFront origin and the
`PUT`, `GET` and `HEAD` methods. If the API returns `500` or `502`, inspect
the ECS logs first; the browser may display the backend error as a CORS
failure when an unhandled error response lacks CORS headers.

The end-to-end development validation has been completed from CloudFront:
frontend upload, document listing, PDF processing, semantic search and chat
with Bedrock.

There is no custom public domain yet. The ECR URI below identifies the stored
image, not the application URL:

```text
740862652747.dkr.ecr.eu-west-1.amazonaws.com/ai-assistant-document-processor:latest
```

## Environment variables

Configured in `.env` and documented in `.env.example`:

- `VITE_API_BASE_URL=http://localhost:8000`
- `VITE_COGNITO_ISSUER=https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_5fX8JYeKk`
- `VITE_COGNITO_CLIENT_ID=4086ign9h6tpj0r5o1mhhab74n`
- `VITE_COGNITO_REDIRECT_URI=http://localhost:5173/`
- `VITE_COGNITO_LOGOUT_URI=http://localhost:5173/`
- `COGNITO_ISSUER=https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_5fX8JYeKk`
- `COGNITO_CLIENT_ID=4086ign9h6tpj0r5o1mhhab74n`
- `FRONTEND_ORIGIN=http://localhost:5173` (local) or
  `https://d38nzp4j8k9sdf.cloudfront.net,http://localhost:5173` (ECS)
- `DYNAMODB_PROFILES_TABLE_NAME=ai-assistant-profiles-dev`
- `DYNAMODB_TAROT_READINGS_TABLE_NAME=ai-assistant-tarot-readings-dev`
- `DYNAMODB_USAGE_TABLE_NAME=ai-assistant-usage-dev`
- `AWS_REGION=eu-west-1`
- `S3_BUCKET_NAME=`
- `AI_PROVIDER=simulated` locally, or `bedrock` in the deployed environment
- `VECTOR_STORE_BACKEND=opensearch`
- `OPENSEARCH_ENDPOINT=`
- `OPENSEARCH_INDEX=ai-assistant-documents`
- `OPENSEARCH_SERVICE=aoss`
- `BEDROCK_MODEL_ID=eu.amazon.nova-lite-v1:0`
- `BEDROCK_MAX_TOKENS=128`
- `DAILY_TAROT_LIMIT=5`
- `DAILY_CHAT_LIMIT=20`
- `SANDBOX_USER_EMAILS=` (optional, development-only allowlist)
- `SANDBOX_USER_IDS=` (optional, preferred stable Cognito `sub` allowlist)
- `BEDROCK_TEMPERATURE=0.2`
- `EMBEDDING_PROVIDER=simulated`
- `BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0`
- `EMBEDDING_DIMENSIONS=512`
