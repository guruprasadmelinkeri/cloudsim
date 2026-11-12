# Gemini free-tier setup

Gemini is optional. Design editing, persistence, cost estimation, graph analysis, optimization heuristics, comparison and PDF export work without a key. The backend sends advisor requests to Google; keep the key in the backend environment only.

1. Open [Google AI Studio](https://aistudio.google.com/) and sign in. Create/select a project for local development.
2. In AI Studio, generate an API key for that project using the [API key guide](https://ai.google.dev/gemini-api/docs/api-key).
3. Review the current [model list](https://ai.google.dev/gemini-api/docs/models), [pricing/free-tier eligibility](https://ai.google.dev/gemini-api/docs/pricing), and model-specific [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits). Free access changes by model and project. This app discovers models exposed by your API key, filters to Gemini 3 Flash text-generation models, and prefers IDs beginning with `gemini-3.0` when available. The list-models API does not report free-tier eligibility, so confirm the selected model is free for your project in AI Studio. Do not enable billing or choose a paid-only model for a free-tier setup.
4. From the repository root, create `backend/.env` (it is ignored by Git) with:

   ```dotenv
   GEMINI_API_KEY=your-secret-key
   # Optional. Leave empty for automatic Gemini 3 Flash model discovery.
   # Or pin a model ID you verified as free-tier in AI Studio.
   GEMINI_MODEL=
   ```

5. Install backend dependencies from `backend/` with `python -m pip install -r requirements.txt`. `google-genai` is the official Python SDK.
6. Start the backend and check `http://localhost:8000/api/intelligence/health` for `gemini_configured: true`. Then submit a prompt from `/intelligence`; the live advisor request is the connection test. It consumes quota. Automated tests mock Gemini and make no API calls.
7. View current project usage and limits in AI Studio’s usage/rate-limit dashboard. Gemini rate limits include requests per minute, input tokens per minute and requests per day; they vary per model and project.
8. Troubleshooting: missing-key responses mean check `backend/.env` and restart FastAPI; model errors mean verify model availability and free-tier eligibility in AI Studio; 429/`RESOURCE_EXHAUSTED` means wait for the applicable quota reset or lower request volume (the app does not switch models to bypass quota); 401/403 means check the key, project and API access; timeouts/network errors can be retried later. If automatic discovery is unavailable, set `GEMINI_MODEL` to an exact eligible Gemini 3 Flash model ID. The remaining intelligence tools do not depend on Gemini.

Google documents: [AI Studio](https://aistudio.google.com/), [keys](https://ai.google.dev/gemini-api/docs/api-key), [models](https://ai.google.dev/gemini-api/docs/models), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).
