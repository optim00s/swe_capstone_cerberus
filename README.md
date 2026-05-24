# AI Food Analyzer

AI Food Analyzer is a software-engineering capstone project for **Topic 2 -- AI Food Analyzer**. The app accepts a meal image, identifies visible ingredients, estimates portions, retrieves nutrition facts, computes total calories/macronutrients, and exposes the result through a CLI, HTTP API, and minimal web UI.

The provided `ai/` package is treated as an external contract and is **not modified**. This repository builds the application layer around it: configuration, validation, retries, caching, concurrency, persistence, logging, tests, Docker, and user-facing entrypoints.


## Features

- **Meal image analysis** using the provided VLM-based `ai.identify_ingredients` interface.
- **Nutrition lookup** through the provided nutrition-provider abstraction, with USDA support.
- **Macronutrient totals** calculated from ingredient weights and per-100g nutrition facts.
- **Offline mode** for demos and tests without API keys or network access.
- **FastAPI HTTP API** with multipart image upload support.
- **HTMX/Jinja web UI** served from `/ui`.
- **CLI** for local terminal usage.
- **Input validation** for file type and image size.
- **Bounded async concurrency** for parallel nutrition lookups.
- **Retry, timeout, and rate-limit protection** around provider calls.
- **Nutrition caching** with memory or PostgreSQL backends.
- **History persistence** with JSONL or PostgreSQL backends.
- **Docker and Docker Compose** support.
- **Offline tests with coverage threshold**.

## Project structure

```text
swe_capstone_cerberus/
├── ai/                         # Provided AI package; do not modify
├── data/                       # Sample meal images and generator
├── foodanalyzer/               # CLI package entrypoint: python -m foodanalyzer
├── scripts/                    # Benchmark/cache helper scripts
├── src/
│   ├── api.py                  # FastAPI app and UI/API routes
│   ├── cli.py                  # Command-line interface
│   ├── config.py               # Environment-based settings
│   ├── models.py               # Pydantic response/history models
│   ├── validation.py           # Image validation helpers
│   ├── benchmark.py            # Sequential vs concurrent benchmark logic
│   ├── concurrency/
│   │   └── pipeline.py         # Bounded async nutrition lookup pipeline
│   ├── core/
│   │   └── analyzer.py         # Main orchestration layer
│   ├── services/
│   │   ├── ai_service.py       # AI facade with retry/cache/rate limiting
│   │   ├── nutrition_cache.py  # Memory/PostgreSQL nutrition cache
│   │   ├── offline.py          # Offline demo providers
│   │   ├── openrouter_provider.py
│   │   ├── rate_limiter.py
│   │   └── retry.py
│   ├── storage/
│   │   └── repository.py       # JSONL/PostgreSQL history storage
│   └── web/
│       ├── static/
│       ├── templates/
│       └── views.py            # HTMX/Jinja render helpers
├── tests/                      # Smoke tests and SE-layer tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-ai.txt
├── .env.example
└── TOPIC.md
```

## Requirements

- Python **3.12+**
- `pip`
- Docker / Docker Compose, optional but recommended for PostgreSQL and containerized runs
- API keys only for online mode:
  - `OPENROUTER_API_KEY` for OpenRouter VLM usage
  - `USDA_API_KEY` for USDA FoodData Central nutrition lookup

Offline mode does **not** require API keys.

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/optim00s/swe_capstone_cerberus.git
cd swe_capstone_cerberus
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create `.env`

```bash
cp .env.example .env
```

For a simple offline/local run, use:

```env
OFFLINE_MODE=true
STORAGE_BACKEND=jsonl
NUTRITION_CACHE_BACKEND=memory
HISTORY_JSONL_PATH=artefacts/history.jsonl
UPLOAD_DIR=runtime/uploads
LOG_LEVEL=INFO
MAX_IMAGE_SIZE_MB=5
MAX_PARALLEL_LOOKUPS=10
RETRY_ATTEMPTS=3
RETRY_BASE_DELAY_SECONDS=0.2
AI_TIMEOUT_SECONDS=30
RATE_LIMIT_TOKENS=10
RATE_LIMIT_REFILL_PER_SECOND=10
HTTP_PORT=8000
```

For online mode with OpenRouter and USDA, set:

```env
OFFLINE_MODE=false
LLM_PROVIDER=openrouter
LLM_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_REASONING_ENABLED=false

NUTRITION_PROVIDER=usda
USDA_API_KEY=your_usda_key_here

STORAGE_BACKEND=postgres
NUTRITION_CACHE_BACKEND=postgres
DATABASE_URL=postgresql://foodanalyzer:foodanalyzer@localhost:5432/foodanalyzer
```

Never commit real API keys.

---

## Run offline demo

The sample PNGs are already included. If needed, regenerate them with:

```bash
python data/_make_samples.py
```

Run the provided AI-layer demo:

```bash
python demo_ai.py --offline
python demo_ai.py --offline --image data/rice_chicken_broccoli.png
python demo_ai.py --offline --image data/no_meal_blue.png
```

---

## Run the CLI

Offline CLI analysis:

```bash
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline --no-storage
```

JSON output:

```bash
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline --json --no-storage
```

Save analysis history with JSONL storage:

```bash
OFFLINE_MODE=true STORAGE_BACKEND=jsonl NUTRITION_CACHE_BACKEND=memory \
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline
```

Show recent history:

```bash
python -m foodanalyzer history --limit 5
```

---

## Run the HTTP API

Start the FastAPI server:

```bash
uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Analyze an image in offline mode:

```bash
curl -X POST "http://127.0.0.1:8000/analyze?offline=true" \
  -F "file=@data/rice_chicken_broccoli.png"
```

Analyze an image in online mode:

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -F "file=@data/rice_chicken_broccoli.png"
```

API docs are available at:

```text
http://127.0.0.1:8000/docs
```

---

## Run the web UI

Start the server:

```bash
uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/ui
```

The UI lets you upload a PNG/JPEG meal image and optionally use offline sample mode.

---

## Run with Docker

Build the image:

```bash
docker build -t foodanalyzer .
```

Run offline with JSONL storage:

```bash
docker run --rm -p 8000:8000 \
  -e OFFLINE_MODE=true \
  -e STORAGE_BACKEND=jsonl \
  -e NUTRITION_CACHE_BACKEND=memory \
  foodanalyzer
```

Open:

```text
http://127.0.0.1:8000/ui
```

---

## Run with Docker Compose and PostgreSQL

Create `.env` first, then run:

```bash
docker compose up --build
```

This starts:

- PostgreSQL on port `5432`
- FastAPI backend on port `8000`

Useful commands:

```bash
docker compose ps
docker compose logs -f backend
docker compose down
```

To remove the PostgreSQL volume too:

```bash
docker compose down -v
```

---

## Tests

Run all tests:

```bash
pytest -v
```

Run with coverage:

```bash
pytest --cov=src --cov-report=term-missing -v
```

Run only the provided AI smoke tests:

```bash
pytest tests/test_ai_smoke.py -v
```

Run static type checks:

```bash
mypy src
```

The project is configured to require high coverage for the `src/` layer.

---

## Benchmark concurrency

Run the sequential-vs-concurrent nutrition lookup benchmark:

```bash
python scripts/bench.py --n 20 --delay 0.05 --parallel 10 --repeats 3
```

Markdown output for reports:

```bash
python scripts/bench.py --n 20 --delay 0.05 --parallel 10 --repeats 3 --format markdown
```

JSON output:

```bash
python scripts/bench.py --format json
```

---

## Probe nutrition cache behavior

Offline cache probe:

```bash
python scripts/cache_probe.py --ingredient broccoli --repeats 2 --offline
```

This is useful for checking repeated nutrition lookups and cache statistics.

---

## Main API response shape

`POST /analyze` returns:

```json
{
  "result": {
    "id": "...",
    "status": "ok",
    "image_path": "runtime/uploads/...png",
    "created_at": "...",
    "ingredients": [],
    "rows": [],
    "totals": {
      "kcal": 0,
      "protein_g": 0,
      "carbs_g": 0,
      "fat_g": 0
    },
    "errors": []
  }
}
```

Possible statuses:

- `ok` -- meal recognized and all nutrition lookups succeeded
- `partial` -- meal recognized, but at least one nutrition lookup failed
- `unknown_meal` -- no recognizable meal was found in the image

---

## Environment variables

| Variable | Example | Purpose |
|---|---|---|
| `OFFLINE_MODE` | `true` | Use local fake providers without network/API keys |
| `LLM_PROVIDER` | `openrouter` | VLM provider selector |
| `LLM_MODEL` | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | VLM model name |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter-compatible base URL |
| `OPENROUTER_API_KEY` | `...` | OpenRouter API key |
| `OPENROUTER_REASONING_ENABLED` | `false` | Whether reasoning mode is requested |
| `NUTRITION_PROVIDER` | `usda` | Nutrition provider selector |
| `USDA_API_KEY` | `...` | USDA FoodData Central API key |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `HTTP_PORT` | `8000` | API port |
| `MAX_IMAGE_SIZE_MB` | `5` | Upload size limit |
| `MAX_PARALLEL_LOOKUPS` | `10` | Bounded concurrency limit |
| `AI_TIMEOUT_SECONDS` | `30` | Provider call timeout |
| `RETRY_ATTEMPTS` | `3` | Retry count for provider calls |
| `RETRY_BASE_DELAY_SECONDS` | `0.2` | Base retry backoff delay |
| `RATE_LIMIT_TOKENS` | `10` | Token-bucket capacity |
| `RATE_LIMIT_REFILL_PER_SECOND` | `10` | Token refill rate |
| `STORAGE_BACKEND` | `jsonl` / `postgres` / `none` | History storage backend |
| `HISTORY_JSONL_PATH` | `artefacts/history.jsonl` | JSONL history path |
| `UPLOAD_DIR` | `runtime/uploads` | Uploaded image directory |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `NUTRITION_CACHE_BACKEND` | `memory` / `postgres` / `none` | Nutrition cache backend |
| `NUTRITION_CACHE_TTL_SECONDS` | `86400` | Cache TTL in seconds |

---

## Important project rules

- Do **not** modify the provided `ai/` directory.
- Do **not** delete or weaken `tests/test_ai_smoke.py`.
- Do **not** hard-code or commit real API keys.
- Use `.env` for local secrets and `.env.example` for safe examples.
- Keep tests offline and deterministic.

---

## Troubleshooting

### `Meal not recognized in image.`

The VLM returned no ingredients. In offline mode, sample filenames drive the fake result, so use a known sample such as:

```bash
data/rice_chicken_broccoli.png
```

### `image exceeds configured size limit`

Increase `MAX_IMAGE_SIZE_MB` in `.env`, or use a smaller PNG/JPEG file.

### PostgreSQL connection error

For local development, either start Docker Compose:

```bash
docker compose up --build
```

or switch to offline-friendly storage:

```env
STORAGE_BACKEND=jsonl
NUTRITION_CACHE_BACKEND=memory
```

### Provider/API failure

Check that these are set correctly:

```env
OPENROUTER_API_KEY=...
USDA_API_KEY=...
OFFLINE_MODE=false
```

For demos without external services, use offline mode.

---

## Appendix: Visual Diagrams

These diagrams summarize the implementation architecture, runtime flow, cache behavior, and PostgreSQL data model.

### 1. Architecture Diagram

```mermaid
flowchart TB
    user[User]

    subgraph entrypoints[Entry points]
        cli[CLI<br/>python -m foodanalyzer]
        api[FastAPI JSON API<br/>POST /analyze]
        ui[HTMX Web UI<br/>GET /ui]
    end

    subgraph app[Application layer]
        validation[validate_image_path<br/>size + extension checks]
        analyzer[MealAnalyzer<br/>core/analyzer.py]
        pipeline[NutritionLookupPipeline<br/>bounded asyncio gather]
    end

    subgraph services[Service boundary]
        ai_service[AIService<br/>retry + timeout + rate limit]
        cache_choice{NUTRITION_CACHE_BACKEND}
        memory_cache[CachedNutritionProvider<br/>in-memory TTL]
        pg_cache[PostgresCachedNutritionProvider<br/>PostgreSQL TTL]
        no_cache[Direct provider<br/>cache disabled]
    end

    subgraph providers[AI and nutrition providers]
        offline_vlm[OfflineVLM]
        openrouter[OpenRouterVLM<br/>OpenAI-compatible SDK]
        offline_nutrition[OfflineNutritionProvider]
        usda[USDA nutrition provider<br/>provided ai package]
        totals[compute_totals<br/>provided ai package]
    end

    subgraph storage[Storage]
        repo_choice{STORAGE_BACKEND}
        postgres_history[(PostgreSQL<br/>analysis_history)]
        jsonl_history[(JSONL<br/>artefacts/history.jsonl)]
        no_history[NullHistoryRepository]
    end

    user --> cli
    user --> api
    user --> ui

    cli --> analyzer
    api --> analyzer
    ui --> analyzer

    analyzer --> validation
    validation --> ai_service
    analyzer --> pipeline
    pipeline --> ai_service
    ai_service --> cache_choice

    cache_choice -- memory --> memory_cache
    cache_choice -- postgres --> pg_cache
    cache_choice -- none --> no_cache

    ai_service --> offline_vlm
    ai_service --> openrouter
    memory_cache --> offline_nutrition
    memory_cache --> usda
    pg_cache --> offline_nutrition
    pg_cache --> usda
    no_cache --> offline_nutrition
    no_cache --> usda

    ai_service --> totals
    analyzer --> repo_choice
    repo_choice -- postgres --> postgres_history
    repo_choice -- jsonl --> jsonl_history
    repo_choice -- none --> no_history
```

### 2. End-to-End Workflow Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Entry as CLI / API / HTMX UI
    participant Analyzer as MealAnalyzer
    participant Validator as validate_image_path
    participant Service as AIService
    participant VLM as VLM Provider
    participant Pipeline as NutritionLookupPipeline
    participant Nutrition as Nutrition Provider / Cache
    participant Totals as compute_totals
    participant Repo as HistoryRepository

    User->>Entry: Submit meal image
    Entry->>Analyzer: analyze(image_path, persist=true/false)
    Analyzer->>Validator: Validate path, extension, size
    Validator-->>Analyzer: Valid image path

    Analyzer->>Service: identify(image_path)
    Service->>Service: Rate limit + retry + timeout wrapper
    Service->>VLM: identify_ingredients(image_path)
    VLM-->>Service: Ingredient list with estimated grams
    Service-->>Analyzer: Ingredients

    alt No recognizable meal
        Analyzer->>Repo: Save unknown_meal result if persistence enabled
        Analyzer-->>Entry: AnalysisResult(status=unknown_meal)
    else Ingredients found
        Analyzer->>Pipeline: lookup_all(ingredients)
        par Bounded per-ingredient lookups
            Pipeline->>Service: lookup_nutrition(ingredient)
            Service->>Nutrition: lookup(ingredient)
            Nutrition-->>Service: NutritionFacts
            Service-->>Pipeline: NutritionFacts
        end
        Pipeline-->>Analyzer: IngredientNutrition rows
        Analyzer->>Totals: compute_totals(ingredients, facts_by_name)
        Totals-->>Analyzer: Total kcal/protein/carbs/fat
        Analyzer->>Repo: Save HistoryRecord if persistence enabled
        Analyzer-->>Entry: AnalysisResult(status=ok or partial)
    end

    Entry-->>User: JSON response, CLI table, or rendered HTML
```

### 3. Offline vs Online Logic

```mermaid
flowchart TD
    start[Start analysis] --> mode{OFFLINE_MODE?}

    mode -- true --> offline_vlm[Use OfflineVLM]
    offline_vlm --> filename[Read sample image filename keywords]
    filename --> offline_ingredients{Known meal keywords found?}
    offline_ingredients -- no --> unknown[Return unknown_meal result]
    offline_ingredients -- yes --> offline_list[Build local ingredient list<br/>name + estimated grams]
    offline_list --> offline_nutrition[Use OfflineNutritionProvider]
    offline_nutrition --> offline_facts[Local per-100g nutrition facts<br/>source=offline]

    mode -- false --> online_vlm[Use OpenRouterVLM]
    online_vlm --> data_url[Encode image as data URL]
    data_url --> openrouter_api[Call OpenRouter vision model]
    openrouter_api --> model_json[Parse strict JSON ingredient response]
    model_json --> online_list[Ingredient list<br/>name + estimated grams + confidence]
    online_list --> usda_provider[Use USDA/provider from provided ai package]
    usda_provider --> online_facts[Provider nutrition facts<br/>source=USDA/provider]

    offline_facts --> rows[Create IngredientNutrition rows]
    online_facts --> rows
    rows --> totals[Compute totals]
    totals --> persist{Persist history?}
    persist -- yes --> history[(PostgreSQL / JSONL history)]
    persist -- no --> response[Return AnalysisResult]
    history --> response
    unknown --> persist
```

### 4. Nutrition Lookup With Cache Logic

```mermaid
flowchart TD
    start[lookup_nutrition ingredient] --> normalize[Normalize key<br/>trim, lowercase, collapse spaces]
    normalize --> backend{NUTRITION_CACHE_BACKEND}

    backend -- memory --> mem_read[Read in-memory cache]
    mem_read --> mem_valid{Entry exists and not expired?}
    mem_valid -- yes --> mem_hit[Cache hit<br/>return cached NutritionFacts]
    mem_valid -- no --> provider_call[Call wrapped nutrition provider]

    backend -- postgres --> pg_ttl{TTL seconds > 0?}
    pg_ttl -- no --> bypass[Bypass cache<br/>call wrapped provider]
    pg_ttl -- yes --> pg_read[Read nutrition_cache<br/>where expires_at >= now]
    pg_read --> pg_valid{Valid row exists?}
    pg_valid -- yes --> pg_hit[Cache hit<br/>return JSONB facts]
    pg_valid -- no --> provider_call

    backend -- none --> direct[No cache wrapper]
    direct --> provider_call
    bypass --> provider_call

    provider_call --> facts[NutritionFacts from offline/USDA provider]
    facts --> write_target{Cache backend writable?}
    write_target -- memory --> mem_write[Store in shared dict<br/>expires_at = now + TTL]
    write_target -- postgres --> pg_write[Upsert nutrition_cache<br/>facts JSONB + expires_at]
    write_target -- none --> return_direct[Return facts]
    mem_write --> return_facts[Return facts]
    pg_write --> return_facts
    return_direct --> return_facts
```

### 5. Nutrition Lookup Without Cache Logic

```mermaid
flowchart TD
    start[lookup_nutrition ingredient] --> limiter[Acquire rate-limit token]
    limiter --> retry[Run with retry_async<br/>attempts + timeout]
    retry --> provider{Provider mode}

    provider -- offline --> offline_provider[OfflineNutritionProvider.lookup]
    offline_provider --> offline_db[Local nutrition table]
    offline_db --> offline_found{Ingredient exists?}
    offline_found -- yes --> offline_facts[Return offline NutritionFacts]
    offline_found -- no --> provider_error[Raise ProviderError]

    provider -- online --> online_provider[Provided nutrition provider lookup]
    online_provider --> external[External nutrition API/provider]
    external --> online_success{Lookup successful?}
    online_success -- yes --> online_facts[Return NutritionFacts]
    online_success -- no --> provider_error

    provider_error --> retry_left{Retry attempts left?}
    retry_left -- yes --> retry
    retry_left -- no --> row_error[Pipeline records row error]

    offline_facts --> row_ok[Pipeline creates nutrition row]
    online_facts --> row_ok
    row_error --> partial[AnalysisResult status=partial]
    row_ok --> totals[Totals use available facts]
```

### 6. PostgreSQL Data Model and Flow

```mermaid
erDiagram
    ANALYSIS_HISTORY {
        text id PK
        timestamptz created_at
        text image_path
        text status
        jsonb ingredients
        jsonb rows
        jsonb totals
        jsonb errors
    }

    NUTRITION_CACHE {
        text ingredient_key PK
        jsonb facts
        timestamptz expires_at
        timestamptz updated_at
    }
```

```mermaid
flowchart LR
    analyzer[MealAnalyzer] --> history_repo[PostgresHistoryRepository]
    history_repo --> ensure_history[create table if not exists<br/>analysis_history]
    ensure_history --> save_history[insert / upsert HistoryRecord]
    save_history --> analysis_history[(analysis_history)]

    service[AIService] --> cache_provider[PostgresCachedNutritionProvider]
    cache_provider --> ensure_cache[create table if not exists<br/>nutrition_cache]
    ensure_cache --> read_cache[select facts<br/>where ingredient_key = key<br/>and expires_at >= now]
    read_cache --> cache_state{Cache row valid?}
    cache_state -- yes --> return_cached[Return cached NutritionFacts]
    cache_state -- no --> wrapped_provider[Call wrapped nutrition provider]
    wrapped_provider --> upsert_cache[insert / update facts + expires_at]
    upsert_cache --> nutrition_cache[(nutrition_cache)]
    nutrition_cache --> return_facts[Return fresh NutritionFacts]

    analysis_history -. reviewer query .-> pgadmin[pgAdmin / postgres_queries.sql]
    nutrition_cache -. reviewer query .-> pgadmin
```

---

## License

This repository is prepared for an academic software-engineering capstone submission.
