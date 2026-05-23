| Metric | Value |
|---|---:|
| Ingredients | 20 |
| Artificial provider delay | 0.050 s |
| Max parallel lookups | 10 |
| Repeats | 3 |
| Workload | I/O-bound nutrition lookups through AIService + NutritionLookupPipeline |
| Cache state | disabled with nutrition_cache_ttl_seconds=0 for every run |
| Sequential average | 1.018 s |
| Concurrent average | 0.110 s |
| Speedup | 9.25x |
| Parallel efficiency | 92.5% |
