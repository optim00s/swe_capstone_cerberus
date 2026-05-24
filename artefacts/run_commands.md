# Food Analyzer Run Commands

## Online/Offline Run

Online CLI:

```powershell
python -m foodanalyzer analyze data/rice_chicken_broccoli.png
```

Offline CLI:

```powershell
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline
```

Offline CLI JSON output:

```powershell
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline --json
```

No-storage demo:

```powershell
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline --no-storage
```

Show recent history:

```powershell
python -m foodanalyzer history --limit 10
```

Docker build:

```powershell
docker build -t foodanalyzer .
```

Docker offline API/UI:

```powershell
docker run --rm -p 8000:8000 -e OFFLINE_MODE=true -e STORAGE_BACKEND=none foodanalyzer
```

Docker CLI offline:

```powershell
docker run --rm foodanalyzer python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline --no-storage
```

## Benchmark Run

Markdown benchmark:

```powershell
python scripts/bench.py --n 20 --delay 0.05 --parallel 10 --repeats 3 --format markdown --output artefacts/benchmark.md
```

JSON benchmark:

```powershell
python scripts/bench.py --n 20 --delay 0.05 --parallel 10 --repeats 3 --format json --output artefacts/benchmark.json
```

## Online/Offline Cache Run (JSONL History)

Note: JSONL is not a cache backend. It is a history-storage fallback. In these commands, history goes to JSONL and nutrition cache uses memory.

JSONL history + offline + memory cache:

```powershell
$env:STORAGE_BACKEND="jsonl"
$env:HISTORY_JSONL_PATH="artefacts/history.jsonl"
$env:NUTRITION_CACHE_BACKEND="memory"
$env:NUTRITION_CACHE_TTL_SECONDS="86400"
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline
```

JSONL history + online + memory cache:

```powershell
$env:STORAGE_BACKEND="jsonl"
$env:HISTORY_JSONL_PATH="artefacts/history.jsonl"
$env:NUTRITION_CACHE_BACKEND="memory"
$env:NUTRITION_CACHE_TTL_SECONDS="86400"
python -m foodanalyzer analyze data/rice_chicken_broccoli.png
```

Memory cache probe offline:

```powershell
$env:NUTRITION_CACHE_BACKEND="memory"
python scripts/cache_probe.py --ingredient broccoli --repeats 2 --offline
```

## Online/Offline Cache Run (PostgreSQL)

PostgreSQL history + PostgreSQL nutrition cache:

```powershell
$env:STORAGE_BACKEND="postgres"
$env:NUTRITION_CACHE_BACKEND="postgres"
$env:NUTRITION_CACHE_TTL_SECONDS="86400"
$env:DATABASE_URL="postgresql://postgres:dev@localhost:5432/foodanalyzer"
python -m foodanalyzer analyze data/rice_chicken_broccoli.png --offline
```

PostgreSQL cache probe offline:

```powershell
$env:NUTRITION_CACHE_BACKEND="postgres"
$env:NUTRITION_CACHE_TTL_SECONDS="86400"
$env:DATABASE_URL="postgresql://postgres:dev@localhost:5432/foodanalyzer"
python scripts/cache_probe.py --ingredient broccoli --repeats 2 --offline
```

TTL visual demo:

```powershell
$env:NUTRITION_CACHE_BACKEND="postgres"
$env:NUTRITION_CACHE_TTL_SECONDS="10"
python scripts/cache_probe.py --ingredient broccoli --repeats 2 --offline
```

Docker PostgreSQL cache probe:

```powershell
docker run --rm `
  -e NUTRITION_CACHE_BACKEND=postgres `
  -e NUTRITION_CACHE_TTL_SECONDS=86400 `
  -e DATABASE_URL=postgresql://postgres:dev@host.docker.internal:5432/foodanalyzer `
  -e STORAGE_BACKEND=none `
  foodanalyzer python scripts/cache_probe.py --ingredient broccoli --repeats 2 --offline
```

PowerShell multiline commands need the trailing backtick character. As a single line:

```powershell
docker run --rm -e NUTRITION_CACHE_BACKEND=postgres -e NUTRITION_CACHE_TTL_SECONDS=86400 -e DATABASE_URL=postgresql://postgres:dev@host.docker.internal:5432/foodanalyzer -e STORAGE_BACKEND=none foodanalyzer python scripts/cache_probe.py --ingredient broccoli --repeats 2 --offline
```

## Uvicorn Runs

Development API/UI:

```powershell
python -m uvicorn src.api:app --reload
```

Specific host/port:

```powershell
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```

Production-style local:

```powershell
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://127.0.0.1:8000/ui
http://127.0.0.1:8000/ui/analyze-page
http://127.0.0.1:8000/docs
```

## Test Runs

All tests:

```powershell
python -m pytest -q
```

Coverage gate:

```powershell
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=85 -q
```

Selected tests:

```powershell
python -m pytest tests/test_nutrition_cache.py -q
python -m pytest tests/test_storage_postgres.py -q
python -m pytest tests/test_pipeline.py -q
python -m pytest tests/test_entrypoints.py tests/test_analyzer.py -q
```

Docker tests:

```powershell
docker run --rm foodanalyzer python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=85 -q
```

## Recommended Demo Config

Use this for the main PostgreSQL-backed demo:

```env
STORAGE_BACKEND=postgres
NUTRITION_CACHE_BACKEND=postgres
NUTRITION_CACHE_TTL_SECONDS=86400
DATABASE_URL=postgresql://postgres:dev@localhost:5432/foodanalyzer
UPLOAD_DIR=runtime/uploads
```
