# USDA spelling miss: `meal_1.jpg` jalapeno / jalapeño

This artefact records an observed online-mode nutrition lookup edge case.

## Input

Image:

![alt text](meal_1.jpg)

Observed meal contents:

- glass noodles
- meatballs
- cucumber
- lettuce
- carrots
- peanuts
- jalapeno / jalapeño
- cilantro

The VLM recognized the jalapeno ingredient with the accented spelling:

```text
jalapeño
```

## Runtime mode

Observed through the HTMX Web UI:

```text
/ui/analyze-page
```

Mode:

- `Offline Sample Mode`: off
- `Save to History`: on
- Nutrition source: USDA/provider path

## Observed result

The analysis completed and most ingredients resolved successfully through USDA. The `jalapeño` row failed because the exact accented spelling did not match the USDA provider lookup.

UI warning:

```text
nutrition_lookup[jalapeño] failed after 3 attempts:
ProviderError: USDA: no match for 'jalapeño'
```

Summary:

| Metric | Value |
| --- | ---: |
| Energy | 1349 kcal |
| Protein | 68.3 g |
| Carbs | 79.9 g |
| Fat | 27.8 g |

Ingredient rows:

| Ingredient | Portion | kcal | Protein | Carbs | Fat | Status | Source |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| glass noodles | 150.0 g | 681 | 2.7 g | 36.0 g | 0.3 g | Resolved | USDA |
| meatballs | 300.0 g | 591 | 63.0 g | 24.0 g | 27.0 g | Resolved | USDA |
| cucumber | 80.0 g | 8 | 0.5 g | 1.7 g | 0.1 g | Resolved | USDA |
| lettuce | 60.0 g | 0 | 0.4 g | 2.0 g | 0.0 g | Resolved | USDA |
| carrots | 20.0 g | 68 | 1.6 g | 15.9 g | 0.3 g | Resolved | USDA |
| peanuts | 15.0 g | 0 | 0.0 g | 0.0 g | 0.0 g | Resolved | USDA |
| jalapeño | 5.0 g | 0 | 0.0 g | 0.0 g | 0.0 g | Missing | Fallback |
| cilantro | 5.0 g | 1 | 0.1 g | 0.2 g | 0.0 g | Resolved | USDA |

## Why this matters

This is not an image-recognition failure. The VLM identified the ingredient correctly enough for a human reader, but the nutrition provider did not match the accented spelling.

The issue is a lookup-normalization edge case:

```text
jalapeño -> no USDA match
jalapeno -> likely searchable without the accent
```

The pipeline behaved as designed:

1. kept processing the remaining ingredients,
2. marked the unresolved ingredient as missing/fallback,
3. returned a completed result with an analysis warning,
4. preserved partial nutrition totals instead of crashing.

## Expected behavior from the software layer

The software layer handled the provider miss gracefully:

- retry wrapper attempted the lookup,
- provider error was captured,
- the row was marked `Missing`,
- the UI displayed a warning,
- the analysis result still rendered.

This is the correct behavior for a partial provider failure.

## Possible mitigation

Future improvements:

- normalize diacritics before nutrition lookup,
- try an ASCII fallback query after a USDA miss,
- maintain a small alias table for common ingredients:
  - `jalapeño` -> `jalapeno`
  - `bell pepper` -> `sweet pepper`
  - `cilantro` -> `coriander leaves`
- show the normalized lookup term in debug logs,
- let users edit ingredient names before nutrition lookup,
- cache successful alias mappings.
