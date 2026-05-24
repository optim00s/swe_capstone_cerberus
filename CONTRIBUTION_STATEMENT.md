# Contribution Statement

**Team:** Cerberus Team  
**Topic:** Topic 2 -- AI Food & Nutrition Analyzer  
**Repository:** [https://github.com/optim00s/swe_capstone_cerberus](https://github.com/optim00s/swe_capstone_cerberus)  
**Final tag:** `v1.0-final`  
**Submission date:** 2026-05-24

---

## Contribution policy

This statement summarizes the work division for the final submitted repository. The percentages add to 100% and match the ownership split used in the report and defense slides. Each member reviewed and adapted their own work before merge, and the team jointly verified the final code, documentation, report, slides, and reproducibility artifacts.

---

## Sharaf Feyzullayev (`@optim00s`)

**Owned:**
- Core analysis orchestration around `src/core/analyzer.py`
- Bounded nutrition lookup pipeline in `src/concurrency/pipeline.py`
- Retry, rate-limit, and cache integration across the service boundary
- Cache probing and related artifact generation
- HTMX/Jinja UI flow and web result presentation
- Related analyzer, pipeline, cache, and UI tests

**Co-owned:**
- `src/services/ai_service.py` with provider/cache/rate-limit integration
- `src/services/retry.py`
- `src/services/rate_limiter.py`
- `src/services/nutrition_cache.py`
- `src/web/templates/*`
- `src/web/static/*`
- Final report and slides review

**Reviewed:**
- CLI/API integration behavior
- Docker and CI commands
- README and run instructions
- Final submission artifacts

**Approximate share of commits/work:** 34%

---

## Nijat Samadov (`@NijatSamadov`)

**Owned:**
- FastAPI application entry points in `src/api.py`
- CLI entry points in `src/cli.py` and `foodanalyzer/`
- Typed environment configuration in `src/config.py`
- Image validation rules in `src/validation.py`
- Pydantic request/response/history models in `src/models.py`
- OpenRouter provider wrapper in `src/services/openrouter_provider.py`
- `.env.example` and entry-point tests

**Co-owned:**
- API/UI behavior connecting upload, validation, analyzer execution, and rendered response fragments
- Offline/online configuration paths
- Error handling for invalid uploads, unknown meals, and provider failures
- Final report, slides, and README wording

**Reviewed:**
- Service-layer retry/cache/rate-limit changes
- Docker Compose environment behavior
- GitHub Actions CI workflow
- Final documentation and artifact consistency

**Approximate share of commits/work:** 33%

---

## Samir Abdullazade (`@samirabdullazade`)

**Owned:**
- History persistence through JSONL and PostgreSQL storage paths in `src/storage/repository.py`
- PostgreSQL-backed cache/storage verification
- Docker packaging with `Dockerfile`, `.dockerignore`, and `docker-compose.yml`
- Dependency files and runtime packaging checks
- Benchmark artifacts and reproducibility notes
- README documentation and storage/benchmark tests

**Co-owned:**
- PostgreSQL data model and query artifacts
- Docker + database local run instructions
- CI Docker build and Docker Compose smoke-check workflow
- Final report appendix artifacts

**Reviewed:**
- API/CLI behavior that saves history
- Environment variable documentation
- Test coverage and benchmark commands
- Final README/report/slides consistency

**Approximate share of commits/work:** 33%

---

## AI Tool Disclosure

We used AI coding assistants for scaffolding, review, wording, and command preparation. All AI-aided output was reviewed, adapted, tested, and diff-checked by the team before inclusion. The provided `ai/` package was treated as a course-supplied dependency, and its public behavior was not changed.

| Module / file | Assistant | What we did with it |
|---|---|---|
| `src/web/templates/*`, `src/web/static/*` | Cursor | Helped draft and refine Jinja/HTMX templates, CSS styling, and small UI layout fixes. The team reviewed the generated markup/styles against the running web UI before committing. |
| Repository structure, Git commands, PR descriptions, CI/Docker workflow notes | Codex 5.5 | Helped plan repository organization, command sequences, GitHub Actions CI, Docker build/run instructions, and PR checklist wording. The team executed the commands, inspected diffs, and kept only reviewed changes. |
| `report/report.tex`, `slides/slides.tex`, README wording, risk documentation | Codex 5.5 and Claude models | Helped phrase report/slides sections, diagram placement notes, and retry/cache/rate-limit explanations. The team rebuilt PDFs and manually adjusted the final text. |
| Service-boundary documentation around retry, cache, rate limiting, and provider failure modes | Claude models | Suggested review prompts and clearer wording. The team checked the wording against the implemented code and tests. |

We affirm that we can defend every line of code in this repository during the oral defense. "The AI wrote it" is not an answer we will use.

---

## Signatures

By signing below, we affirm that:
- The contributions described above are accurate.
- The committed percentages reflect actual work, not artificially split commits.
- Every line of code in the repository can be defended by at least one team member.
- AI assistant usage has been disclosed as described above.

| Member | Signature | Date |
|---|---|---|
| Sharaf Feyzullayev | __________F.S.__________ | 2026-05-24 |
| Nijat Samadov | __________S.N.__________ | 2026-05-24 |
| Samir Abdullazade | ____________A.S.____________ | 2026-05-24 |
