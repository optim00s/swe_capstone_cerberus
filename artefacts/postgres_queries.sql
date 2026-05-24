-- Food Analyzer PostgreSQL inspection queries.
-- Open this file in pgAdmin Query Tool connected to the foodanalyzer database.
-- These queries are artefacts for reviewer/TA verification, not application code.

-- 1. Nutrition cache status, including TTL validity.
select
  ingredient_key,
  facts->>'name' as matched_name,
  facts->>'source' as source,
  (facts->>'kcal_per_100g')::numeric as kcal_per_100g,
  updated_at,
  expires_at,
  now() as current_time,
  expires_at - updated_at as ttl_interval,
  case when expires_at >= now() then 'valid' else 'expired' end as cache_status
from nutrition_cache
order by updated_at desc;

-- 2. Analysis history summary.
select
  id,
  created_at,
  status,
  image_path,
  jsonb_array_length(ingredients) as ingredient_count,
  round((totals->>'kcal')::numeric, 2) as total_kcal,
  round((totals->>'protein_g')::numeric, 2) as total_protein_g,
  round((totals->>'carbs_g')::numeric, 2) as total_carbs_g,
  round((totals->>'fat_g')::numeric, 2) as total_fat_g,
  errors
from analysis_history
order by created_at desc;

-- 3. Analysis history expanded into one row per ingredient.
select
  h.created_at,
  h.id,
  r.ordinality as row_no,
  r.item->'ingredient'->>'name' as ingredient,
  (r.item->'ingredient'->>'estimated_grams')::numeric as grams,
  (r.item->'nutrition'->>'kcal')::numeric as kcal,
  (r.item->'nutrition'->>'protein_g')::numeric as protein_g,
  (r.item->'nutrition'->>'carbs_g')::numeric as carbs_g,
  (r.item->'nutrition'->>'fat_g')::numeric as fat_g,
  r.item->'facts'->>'source' as source,
  r.item->>'error' as error
from analysis_history h
cross join lateral jsonb_array_elements(h.rows) with ordinality as r(item, ordinality)
order by h.created_at desc, r.ordinality;

-- 4. Cache evidence for analysis rows.
-- This infers whether a history row could have used an already-valid cache row.
-- It is evidence, not a dedicated cache-event audit table.
with history_rows as (
  select
    h.created_at,
    h.id,
    lower(regexp_replace(trim(r.item->'ingredient'->>'name'), '\s+', ' ', 'g')) as cache_key,
    r.item->'ingredient'->>'name' as ingredient,
    (r.item->'nutrition'->>'kcal')::numeric as kcal,
    (r.item->'nutrition'->>'protein_g')::numeric as protein_g,
    (r.item->'nutrition'->>'carbs_g')::numeric as carbs_g,
    (r.item->'nutrition'->>'fat_g')::numeric as fat_g,
    r.item->'facts'->>'source' as facts_source
  from analysis_history h
  cross join lateral jsonb_array_elements(h.rows) with ordinality as r(item, ordinality)
)
select
  h.created_at as analysis_time,
  h.id,
  h.ingredient,
  h.kcal,
  h.protein_g,
  h.carbs_g,
  h.fat_g,
  h.facts_source,
  c.updated_at as cache_written_at,
  c.expires_at as cache_expires_at,
  case
    when c.updated_at < h.created_at and c.expires_at >= h.created_at
      then 'likely cache hit'
    when c.updated_at >= h.created_at
      then 'cache row written/updated around or after this analysis'
    else 'no valid cache evidence'
  end as cache_evidence
from history_rows h
left join nutrition_cache c
  on c.ingredient_key = h.cache_key
order by h.created_at desc, h.ingredient;

-- 5. Cache evidence for one ingredient.
-- Change the literal below, for example: 'broccoli', 'cucumber', 'rice noodles'.
with history_rows as (
  select
    h.created_at,
    h.id,
    lower(regexp_replace(trim(r.item->'ingredient'->>'name'), '\s+', ' ', 'g')) as cache_key,
    r.item->'ingredient'->>'name' as ingredient,
    (r.item->'nutrition'->>'kcal')::numeric as kcal,
    (r.item->'nutrition'->>'protein_g')::numeric as protein_g,
    (r.item->'nutrition'->>'carbs_g')::numeric as carbs_g,
    (r.item->'nutrition'->>'fat_g')::numeric as fat_g,
    r.item->'facts'->>'source' as facts_source
  from analysis_history h
  cross join lateral jsonb_array_elements(h.rows) with ordinality as r(item, ordinality)
)
select
  h.created_at as analysis_time,
  h.ingredient,
  h.kcal,
  h.protein_g,
  h.carbs_g,
  h.fat_g,
  h.facts_source,
  c.updated_at as cache_written_at,
  c.expires_at as cache_expires_at,
  case
    when c.updated_at < h.created_at and c.expires_at >= h.created_at
      then 'likely cache hit'
    when c.updated_at >= h.created_at
      then 'cache row written/updated around or after this analysis'
    else 'no valid cache evidence'
  end as cache_evidence
from history_rows h
left join nutrition_cache c
  on c.ingredient_key = h.cache_key
where h.cache_key = 'broccoli'
order by h.created_at desc;

-- 6. Clear nutrition cache rows.
-- Uncomment before running when you want a fresh cache demo.
-- delete from nutrition_cache;

-- 7. Clear project PostgreSQL tables.
-- Destructive: uncomment only when you intentionally want to reset demo data.
-- drop table if exists analysis_history cascade;
-- drop table if exists nutrition_cache cascade;
