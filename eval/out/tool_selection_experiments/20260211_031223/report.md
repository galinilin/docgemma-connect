# MedGemma 4B — Tool Selection & Argument Extraction Experiments

**Date:** 2026-02-11 03:25
**Model:** `google/medgemma-1.5-4b-it`
**Endpoint:** `https://sbx7zjulvioxoh-8000.proxy.runpod.net`
**Total experiments:** 320
**Errors:** 0

## 1. Executive Summary

- **Tool exact match:** 251/320 (78.4%)
- **Tool acceptable match:** 281/320 (87.8%)
- **Total LLM calls:** 540
- **Avg latency per experiment:** 1577ms
- **Arg value accuracy:** 399/528 (75.6%)
- **Thinking tokens observed:** 20/320 (6.2%)

## 2. Strategy Comparison Table

| Category | Strategy | N | Tool Exact | Tool Accept | Avg Args OK | Avg Latency (ms) | Calls |
|----------|----------|---|-----------|-------------|-------------|-------------------|-------|
| Direct Baseline | baseline | 20 | 16/20 (80.0%) | 18/20 (90.0%) | 88% | 889 | 20 |
| Prefix Completion | prefix_analytical | 20 | 17/20 (85.0%) | 19/20 (95.0%) | 88% | 911 | 20 |
| Prefix Completion | prefix_cognitive | 20 | 16/20 (80.0%) | 18/20 (90.0%) | 91% | 914 | 20 |
| Boolean Probing | boolean_probe | 20 | 5/20 (25.0%) | 7/20 (35.0%) | 0% | 2396 | 200 |
| Reasoning Then Select | reasoning_then_select | 20 | 11/20 (55.0%) | 13/20 (65.0%) | 55% | 9349 | 40 |
| Few Shot Variation | 0shot | 20 | 16/20 (80.0%) | 18/20 (90.0%) | 76% | 859 | 20 |
| Few Shot Variation | 10shot | 20 | 16/20 (80.0%) | 18/20 (90.0%) | 88% | 901 | 20 |
| Few Shot Variation | 1shot | 20 | 17/20 (85.0%) | 19/20 (95.0%) | 91% | 811 | 20 |
| Few Shot Variation | 3shot | 20 | 17/20 (85.0%) | 19/20 (95.0%) | 79% | 887 | 20 |
| Tool Description Verbosity | full_desc | 20 | 19/20 (95.0%) | 20/20 (100.0%) | 94% | 987 | 20 |
| Tool Description Verbosity | names_only | 20 | 19/20 (95.0%) | 20/20 (100.0%) | 88% | 930 | 20 |
| Tool Description Verbosity | short_desc | 20 | 16/20 (80.0%) | 18/20 (90.0%) | 88% | 897 | 20 |
| Joint Vs Two Stage | joint | 20 | 16/20 (80.0%) | 18/20 (90.0%) | 88% | 895 | 20 |
| Joint Vs Two Stage | two_stage | 20 | 18/20 (90.0%) | 20/20 (100.0%) | 88% | 1827 | 40 |
| Field Ordering | critical_first | 20 | 16/20 (80.0%) | 18/20 (90.0%) | 88% | 902 | 20 |
| Field Ordering | critical_last | 20 | 16/20 (80.0%) | 18/20 (90.0%) | 21% | 878 | 20 |

## 3. Per-Category Deep Dives

### 3.1. Direct Baseline

Tool exact: **16/20** (80.0%)

| Experiment | Query | Expected | Selected | Correct? | Args OK |
|------------|-------|----------|----------|----------|---------|
| `cat1-baseline-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat1-baseline-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat1-baseline-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat1-baseline-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat1-baseline-Q-05` | Q-05 | search_patient | search_patient | Exact | 1/1 |
| `cat1-baseline-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat1-baseline-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat1-baseline-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat1-baseline-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 3/3 |
| `cat1-baseline-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat1-baseline-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat1-baseline-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat1-baseline-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat1-baseline-Q-14` | Q-14 | search_patient | search_patient | Exact | 0/1 |
| `cat1-baseline-Q-15` | Q-15 | check_drug_safety | get_patient_chart | WRONG | 1/1 |
| `cat1-baseline-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat1-baseline-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat1-baseline-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat1-baseline-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat1-baseline-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |

### 3.2. Prefix Completion

Tool exact: **33/40** (82.5%)

| Experiment | Query | Expected | Selected | Correct? | Args OK |
|------------|-------|----------|----------|----------|---------|
| `cat2-prefix-cognitive-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat2-prefix-cognitive-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat2-prefix-cognitive-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat2-prefix-cognitive-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat2-prefix-cognitive-Q-05` | Q-05 | search_patient | search_patient | Exact | 1/1 |
| `cat2-prefix-cognitive-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat2-prefix-cognitive-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat2-prefix-cognitive-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat2-prefix-cognitive-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 3/3 |
| `cat2-prefix-cognitive-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat2-prefix-cognitive-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat2-prefix-cognitive-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat2-prefix-cognitive-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat2-prefix-cognitive-Q-14` | Q-14 | search_patient | search_patient | Exact | 1/1 |
| `cat2-prefix-cognitive-Q-15` | Q-15 | check_drug_safety | get_patient_chart | WRONG | 1/1 |
| `cat2-prefix-cognitive-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat2-prefix-cognitive-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat2-prefix-cognitive-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat2-prefix-cognitive-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat2-prefix-cognitive-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |
| `cat2-prefix-analytical-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat2-prefix-analytical-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat2-prefix-analytical-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat2-prefix-analytical-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat2-prefix-analytical-Q-05` | Q-05 | search_patient | search_patient | Exact | 1/1 |
| `cat2-prefix-analytical-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat2-prefix-analytical-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat2-prefix-analytical-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat2-prefix-analytical-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 3/3 |
| `cat2-prefix-analytical-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat2-prefix-analytical-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat2-prefix-analytical-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat2-prefix-analytical-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat2-prefix-analytical-Q-14` | Q-14 | search_patient | search_patient | Exact | 0/1 |
| `cat2-prefix-analytical-Q-15` | Q-15 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat2-prefix-analytical-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat2-prefix-analytical-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat2-prefix-analytical-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat2-prefix-analytical-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat2-prefix-analytical-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |

### 3.3. Boolean Probing

Tool exact: **5/20** (25.0%)

| Experiment | Query | Expected | Selected | Correct? | Args OK |
|------------|-------|----------|----------|----------|---------|
| `cat3-bool-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 0/1 |
| `cat3-bool-Q-02` | Q-02 | search_medical_literature | check_drug_safety | WRONG | 0/1 |
| `cat3-bool-Q-03` | Q-03 | check_drug_interactions | check_drug_safety | WRONG | 0/1 |
| `cat3-bool-Q-04` | Q-04 | find_clinical_trials | search_medical_literature | WRONG | 0/1 |
| `cat3-bool-Q-05` | Q-05 | search_patient | search_medical_literature | WRONG | 0/1 |
| `cat3-bool-Q-06` | Q-06 | get_patient_chart | check_drug_safety | WRONG | 0/1 |
| `cat3-bool-Q-07` | Q-07 | add_allergy | check_drug_safety | WRONG | 0/4 |
| `cat3-bool-Q-08` | Q-08 | prescribe_medication | search_patient | WRONG | 0/4 |
| `cat3-bool-Q-09` | Q-09 | save_clinical_note | check_drug_safety | WRONG | 0/3 |
| `cat3-bool-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat3-bool-Q-11` | Q-11 | check_drug_safety | check_drug_safety | Exact | 0/1 |
| `cat3-bool-Q-12` | Q-12 | check_drug_interactions | check_drug_safety | Accept | 0/1 |
| `cat3-bool-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 0/1 |
| `cat3-bool-Q-14` | Q-14 | search_patient | search_medical_literature | WRONG | 0/1 |
| `cat3-bool-Q-15` | Q-15 | check_drug_safety | check_drug_safety | Exact | 0/1 |
| `cat3-bool-Q-16` | Q-16 | prescribe_medication | check_drug_safety | WRONG | 0/4 |
| `cat3-bool-Q-17` | Q-17 | add_allergy | check_drug_safety | WRONG | 0/2 |
| `cat3-bool-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 0/1 |
| `cat3-bool-Q-19` | Q-19 | check_drug_interactions | check_drug_safety | WRONG | 0/1 |
| `cat3-bool-Q-20` | Q-20 | save_clinical_note | check_drug_safety | WRONG | 0/2 |

**Multi-true rate:** 19/20 queries had >1 tool marked suitable
**Zero-true rate:** 0/20 queries had no tool marked suitable

**Per-tool true rate:**

| Tool | True Count |
|------|-----------|
| check_drug_safety | 13/20 |
| search_medical_literature | 18/20 |
| check_drug_interactions | 12/20 |
| find_clinical_trials | 13/20 |
| search_patient | 13/20 |
| get_patient_chart | 14/20 |
| add_allergy | 8/20 |
| prescribe_medication | 15/20 |
| save_clinical_note | 11/20 |
| analyze_medical_image | 12/20 |

### 3.4. Reasoning Then Select

Tool exact: **11/20** (55.0%)

| Experiment | Query | Expected | Selected | Correct? | Args OK |
|------------|-------|----------|----------|----------|---------|
| `cat4-reasoning-Q-01` | Q-01 | check_drug_safety | search_medical_literature | WRONG | 0/1 |
| `cat4-reasoning-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat4-reasoning-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 0/1 |
| `cat4-reasoning-Q-04` | Q-04 | find_clinical_trials | search_medical_literature | WRONG | 1/1 |
| `cat4-reasoning-Q-05` | Q-05 | search_patient | search_patient | Exact | 0/1 |
| `cat4-reasoning-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat4-reasoning-Q-07` | Q-07 | add_allergy | get_patient_chart | WRONG | 1/4 |
| `cat4-reasoning-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat4-reasoning-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 2/3 |
| `cat4-reasoning-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat4-reasoning-Q-11` | Q-11 | check_drug_safety | get_patient_chart | WRONG | 0/1 |
| `cat4-reasoning-Q-12` | Q-12 | check_drug_interactions | search_medical_literature | WRONG | 0/1 |
| `cat4-reasoning-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat4-reasoning-Q-14` | Q-14 | search_patient | search_patient | Exact | 0/1 |
| `cat4-reasoning-Q-15` | Q-15 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat4-reasoning-Q-16` | Q-16 | prescribe_medication | get_patient_chart | WRONG | 3/4 |
| `cat4-reasoning-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 1/2 |
| `cat4-reasoning-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat4-reasoning-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat4-reasoning-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |

**Reasoning samples (first 200 chars):**

- `Q-01`: __
- `Q-02`: __
- `Q-03`: __
- `Q-04`: __
- `Q-05`: __

### 3.5. Few Shot Variation

Tool exact: **66/80** (82.5%)

| Experiment | Query | Expected | Selected | Correct? | Args OK |
|------------|-------|----------|----------|----------|---------|
| `cat5-0shot-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat5-0shot-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat5-0shot-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 0/1 |
| `cat5-0shot-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat5-0shot-Q-05` | Q-05 | search_patient | search_patient | Exact | 0/1 |
| `cat5-0shot-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat5-0shot-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat5-0shot-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat5-0shot-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 2/3 |
| `cat5-0shot-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat5-0shot-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat5-0shot-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 0/1 |
| `cat5-0shot-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat5-0shot-Q-14` | Q-14 | search_patient | search_patient | Exact | 1/1 |
| `cat5-0shot-Q-15` | Q-15 | check_drug_safety | get_patient_chart | WRONG | 0/1 |
| `cat5-0shot-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat5-0shot-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat5-0shot-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat5-0shot-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat5-0shot-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |
| `cat5-1shot-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat5-1shot-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat5-1shot-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat5-1shot-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat5-1shot-Q-05` | Q-05 | search_patient | search_patient | Exact | 1/1 |
| `cat5-1shot-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat5-1shot-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat5-1shot-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat5-1shot-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 3/3 |
| `cat5-1shot-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat5-1shot-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat5-1shot-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat5-1shot-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat5-1shot-Q-14` | Q-14 | search_patient | search_patient | Exact | 1/1 |
| `cat5-1shot-Q-15` | Q-15 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat5-1shot-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat5-1shot-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat5-1shot-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat5-1shot-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat5-1shot-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |
| `cat5-3shot-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat5-3shot-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat5-3shot-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 0/1 |
| `cat5-3shot-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat5-3shot-Q-05` | Q-05 | search_patient | search_patient | Exact | 0/1 |
| `cat5-3shot-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat5-3shot-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat5-3shot-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat5-3shot-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 3/3 |
| `cat5-3shot-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat5-3shot-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat5-3shot-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 0/1 |
| `cat5-3shot-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat5-3shot-Q-14` | Q-14 | search_patient | search_patient | Exact | 0/1 |
| `cat5-3shot-Q-15` | Q-15 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat5-3shot-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat5-3shot-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat5-3shot-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat5-3shot-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat5-3shot-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |
| `cat5-10shot-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat5-10shot-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat5-10shot-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat5-10shot-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat5-10shot-Q-05` | Q-05 | search_patient | search_patient | Exact | 1/1 |
| `cat5-10shot-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat5-10shot-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat5-10shot-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat5-10shot-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 3/3 |
| `cat5-10shot-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat5-10shot-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat5-10shot-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat5-10shot-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat5-10shot-Q-14` | Q-14 | search_patient | search_patient | Exact | 0/1 |
| `cat5-10shot-Q-15` | Q-15 | check_drug_safety | get_patient_chart | WRONG | 1/1 |
| `cat5-10shot-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat5-10shot-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat5-10shot-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat5-10shot-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat5-10shot-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |

### 3.6. Tool Description Verbosity

Tool exact: **54/60** (90.0%)

| Experiment | Query | Expected | Selected | Correct? | Args OK |
|------------|-------|----------|----------|----------|---------|
| `cat6-names_only-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat6-names_only-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat6-names_only-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat6-names_only-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat6-names_only-Q-05` | Q-05 | search_patient | search_patient | Exact | 0/1 |
| `cat6-names_only-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat6-names_only-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 3/4 |
| `cat6-names_only-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat6-names_only-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 3/3 |
| `cat6-names_only-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat6-names_only-Q-11` | Q-11 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat6-names_only-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat6-names_only-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat6-names_only-Q-14` | Q-14 | search_patient | search_patient | Exact | 1/1 |
| `cat6-names_only-Q-15` | Q-15 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat6-names_only-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat6-names_only-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat6-names_only-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat6-names_only-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat6-names_only-Q-20` | Q-20 | save_clinical_note | save_clinical_note | Exact | 1/2 |
| `cat6-short_desc-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat6-short_desc-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat6-short_desc-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat6-short_desc-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat6-short_desc-Q-05` | Q-05 | search_patient | search_patient | Exact | 1/1 |
| `cat6-short_desc-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat6-short_desc-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat6-short_desc-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat6-short_desc-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 3/3 |
| `cat6-short_desc-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat6-short_desc-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat6-short_desc-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat6-short_desc-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat6-short_desc-Q-14` | Q-14 | search_patient | search_patient | Exact | 0/1 |
| `cat6-short_desc-Q-15` | Q-15 | check_drug_safety | get_patient_chart | WRONG | 1/1 |
| `cat6-short_desc-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat6-short_desc-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat6-short_desc-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat6-short_desc-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat6-short_desc-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |
| `cat6-full_desc-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat6-full_desc-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat6-full_desc-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat6-full_desc-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat6-full_desc-Q-05` | Q-05 | search_patient | search_patient | Exact | 1/1 |
| `cat6-full_desc-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat6-full_desc-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat6-full_desc-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat6-full_desc-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 3/3 |
| `cat6-full_desc-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat6-full_desc-Q-11` | Q-11 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat6-full_desc-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat6-full_desc-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat6-full_desc-Q-14` | Q-14 | search_patient | search_patient | Exact | 1/1 |
| `cat6-full_desc-Q-15` | Q-15 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat6-full_desc-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat6-full_desc-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat6-full_desc-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat6-full_desc-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat6-full_desc-Q-20` | Q-20 | save_clinical_note | save_clinical_note | Exact | 1/2 |

### 3.7. Joint Vs Two Stage

Tool exact: **34/40** (85.0%)

| Experiment | Query | Expected | Selected | Correct? | Args OK |
|------------|-------|----------|----------|----------|---------|
| `cat7-joint-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat7-two_stage-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat7-joint-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat7-two_stage-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat7-joint-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat7-two_stage-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat7-joint-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat7-two_stage-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat7-joint-Q-05` | Q-05 | search_patient | search_patient | Exact | 1/1 |
| `cat7-two_stage-Q-05` | Q-05 | search_patient | search_patient | Exact | 1/1 |
| `cat7-joint-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat7-two_stage-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat7-joint-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat7-two_stage-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat7-joint-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat7-two_stage-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat7-joint-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 3/3 |
| `cat7-two_stage-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 2/3 |
| `cat7-joint-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat7-two_stage-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat7-joint-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat7-two_stage-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat7-joint-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat7-two_stage-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat7-joint-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat7-two_stage-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat7-joint-Q-14` | Q-14 | search_patient | search_patient | Exact | 0/1 |
| `cat7-two_stage-Q-14` | Q-14 | search_patient | search_patient | Exact | 1/1 |
| `cat7-joint-Q-15` | Q-15 | check_drug_safety | get_patient_chart | WRONG | 1/1 |
| `cat7-two_stage-Q-15` | Q-15 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat7-joint-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat7-two_stage-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat7-joint-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat7-two_stage-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat7-joint-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat7-two_stage-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat7-joint-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat7-two_stage-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat7-joint-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |
| `cat7-two_stage-Q-20` | Q-20 | save_clinical_note | save_clinical_note | Exact | 1/2 |

### 3.8. Field Ordering

Tool exact: **32/40** (80.0%)

| Experiment | Query | Expected | Selected | Correct? | Args OK |
|------------|-------|----------|----------|----------|---------|
| `cat8-critical_first-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 1/1 |
| `cat8-critical_last-Q-01` | Q-01 | check_drug_safety | check_drug_safety | Exact | 0/1 |
| `cat8-critical_first-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat8-critical_last-Q-02` | Q-02 | search_medical_literature | search_medical_literature | Exact | 0/1 |
| `cat8-critical_first-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat8-critical_last-Q-03` | Q-03 | check_drug_interactions | check_drug_interactions | Exact | 0/1 |
| `cat8-critical_first-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 1/1 |
| `cat8-critical_last-Q-04` | Q-04 | find_clinical_trials | find_clinical_trials | Exact | 0/1 |
| `cat8-critical_first-Q-05` | Q-05 | search_patient | search_patient | Exact | 1/1 |
| `cat8-critical_last-Q-05` | Q-05 | search_patient | search_patient | Exact | 0/1 |
| `cat8-critical_first-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat8-critical_last-Q-06` | Q-06 | get_patient_chart | get_patient_chart | Exact | 1/1 |
| `cat8-critical_first-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 4/4 |
| `cat8-critical_last-Q-07` | Q-07 | add_allergy | add_allergy | Exact | 1/4 |
| `cat8-critical_first-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat8-critical_last-Q-08` | Q-08 | prescribe_medication | prescribe_medication | Exact | 1/4 |
| `cat8-critical_first-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 3/3 |
| `cat8-critical_last-Q-09` | Q-09 | save_clinical_note | save_clinical_note | Exact | 1/3 |
| `cat8-critical_first-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat8-critical_last-Q-10` | Q-10 | analyze_medical_image | analyze_medical_image | Exact | 0/1 |
| `cat8-critical_first-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat8-critical_last-Q-11` | Q-11 | check_drug_safety | search_medical_literature | Accept | 0/1 |
| `cat8-critical_first-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat8-critical_last-Q-12` | Q-12 | check_drug_interactions | check_drug_interactions | Exact | 0/1 |
| `cat8-critical_first-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 1/1 |
| `cat8-critical_last-Q-13` | Q-13 | find_clinical_trials | search_medical_literature | Accept | 0/1 |
| `cat8-critical_first-Q-14` | Q-14 | search_patient | search_patient | Exact | 0/1 |
| `cat8-critical_last-Q-14` | Q-14 | search_patient | search_patient | Exact | 0/1 |
| `cat8-critical_first-Q-15` | Q-15 | check_drug_safety | get_patient_chart | WRONG | 1/1 |
| `cat8-critical_last-Q-15` | Q-15 | check_drug_safety | get_patient_chart | WRONG | 0/1 |
| `cat8-critical_first-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 4/4 |
| `cat8-critical_last-Q-16` | Q-16 | prescribe_medication | prescribe_medication | Exact | 1/4 |
| `cat8-critical_first-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 2/2 |
| `cat8-critical_last-Q-17` | Q-17 | add_allergy | add_allergy | Exact | 1/2 |
| `cat8-critical_first-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 1/1 |
| `cat8-critical_last-Q-18` | Q-18 | search_medical_literature | search_medical_literature | Exact | 0/1 |
| `cat8-critical_first-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 1/1 |
| `cat8-critical_last-Q-19` | Q-19 | check_drug_interactions | check_drug_interactions | Exact | 0/1 |
| `cat8-critical_first-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |
| `cat8-critical_last-Q-20` | Q-20 | save_clinical_note | get_patient_chart | WRONG | 1/2 |

## 4. Tool Confusion Matrix

Rows = expected tool, Columns = selected tool. Cell = count across all experiments.

| Expected \ Selected | add allergy | analyze medi | check drug i | check drug s | find clinica | get patient  | prescribe me | save clinica | search medic | search patie |
|---|---|---|---|---|---|---|---|---|---|---|
| add allergy | **29** | . | . | 2 | . | 1 | . | . | . | . |
| analyze medical imag | . | **16** | . | . | . | . | . | . | . | . |
| check drug interacti | . | . | **44** | 3 | . | . | . | . | 1 | . |
| check drug safety | . | . | . | **25** | . | 9 | . | . | 14 | . |
| find clinical trials | . | . | . | . | **14** | . | . | . | 18 | . |
| get patient chart | . | . | . | 1 | . | **15** | . | . | . | . |
| prescribe medication | . | . | . | 1 | . | 1 | **29** | . | . | 1 |
| save clinical note | . | . | . | 2 | . | 12 | . | **18** | . | . |
| search medical liter | . | . | . | 1 | . | . | . | . | **31** | . |
| search patient | . | . | . | . | . | . | . | . | 2 | **30** |

## 5. Argument Extraction Analysis

Per-argument miss rates across all experiments.

| Argument | Expected N | Present | Correct | Miss Rate |
|----------|-----------|---------|---------|-----------|
| dosage | 32 | 28 | 28 | 12.5% |
| drug_list | 48 | 40 | 36 | 16.7% |
| drug_name | 48 | 27 | 27 | 43.8% |
| frequency | 32 | 28 | 28 | 12.5% |
| medication_name | 32 | 27 | 27 | 15.6% |
| name | 32 | 16 | 16 | 50.0% |
| note_text | 32 | 26 | 14 | 18.8% |
| note_type | 16 | 12 | 11 | 25.0% |
| patient_id | 112 | 105 | 105 | 6.2% |
| query | 80 | 70 | 56 | 12.5% |
| reaction | 16 | 13 | 13 | 18.8% |
| severity | 16 | 12 | 12 | 25.0% |
| substance | 32 | 26 | 26 | 18.8% |

### Per-Tool Argument Accuracy

**check_drug_safety:**
  - drug_name: 27/48 correct

**search_medical_literature:**
  - query: 28/32 correct

**check_drug_interactions:**
  - drug_list: 36/48 correct

**find_clinical_trials:**
  - query: 28/32 correct

**search_patient:**
  - name: 16/32 correct

**get_patient_chart:**
  - patient_id: 15/16 correct

**add_allergy:**
  - patient_id: 30/32 correct
  - reaction: 13/16 correct
  - severity: 12/16 correct
  - substance: 26/32 correct

**prescribe_medication:**
  - dosage: 28/32 correct
  - frequency: 28/32 correct
  - medication_name: 27/32 correct
  - patient_id: 30/32 correct

**save_clinical_note:**
  - note_text: 14/32 correct
  - note_type: 11/16 correct
  - patient_id: 30/32 correct

**analyze_medical_image:**
  - query: 0/16 correct

## 6. Few-Shot Scaling Curve

| Shots | Tool Exact | Tool Accept | Avg Args OK |
|-------|-----------|-------------|-------------|
| 0shot | 16/20 (80.0%) | 18/20 (90.0%) | 25/33 |
| 1shot | 17/20 (85.0%) | 19/20 (95.0%) | 30/33 |
| 3shot | 17/20 (85.0%) | 19/20 (95.0%) | 26/33 |
| 10shot | 16/20 (80.0%) | 18/20 (90.0%) | 29/33 |

## 7. Field Ordering Effect

**critical_first:** tool exact=16/20 (80.0%), tool accept=18/20 (90.0%), args=29/33
**critical_last:** tool exact=16/20 (80.0%), tool accept=18/20 (90.0%), args=7/33

| Query | Critical-First Tool | Critical-Last Tool | First Args | Last Args |
|-------|--------------------|--------------------|------------|-----------|
| Q-01 | OK | OK | 1/1 | 0/1 |
| Q-02 | OK | OK | 1/1 | 0/1 |
| Q-03 | OK | OK | 1/1 | 0/1 |
| Q-04 | OK | OK | 1/1 | 0/1 |
| Q-05 | OK | OK | 1/1 | 0/1 |
| Q-06 | OK | OK | 1/1 | 1/1 |
| Q-07 | OK | OK | 4/4 | 1/4 |
| Q-08 | OK | OK | 4/4 | 1/4 |
| Q-09 | OK | OK | 3/3 | 1/3 |
| Q-10 | OK | OK | 0/1 | 0/1 |
| Q-11 | search_medical_literature | search_medical_literature | 0/1 | 0/1 |
| Q-12 | OK | OK | 1/1 | 0/1 |
| Q-13 | search_medical_literature | search_medical_literature | 1/1 | 0/1 |
| Q-14 | OK | OK | 0/1 | 0/1 |
| Q-15 | get_patient_chart | get_patient_chart | 1/1 | 0/1 |
| Q-16 | OK | OK | 4/4 | 1/4 |
| Q-17 | OK | OK | 2/2 | 1/2 |
| Q-18 | OK | OK | 1/1 | 0/1 |
| Q-19 | OK | OK | 1/1 | 0/1 |
| Q-20 | get_patient_chart | get_patient_chart | 1/2 | 1/2 |

## 8. Latency Analysis

| Strategy | Avg Total (ms) | Avg Per-Call (ms) | Calls/Exp |
|----------|---------------|-------------------|-----------|
| baseline | 889 | 889 | 1.0 |
| prefix_analytical | 911 | 911 | 1.0 |
| prefix_cognitive | 914 | 914 | 1.0 |
| boolean_probe | 2396 | 240 | 10.0 |
| reasoning_then_select | 9349 | 4675 | 2.0 |
| 0shot | 859 | 859 | 1.0 |
| 10shot | 901 | 901 | 1.0 |
| 1shot | 811 | 811 | 1.0 |
| 3shot | 887 | 887 | 1.0 |
| full_desc | 987 | 987 | 1.0 |
| names_only | 930 | 930 | 1.0 |
| short_desc | 897 | 897 | 1.0 |
| joint | 895 | 895 | 1.0 |
| two_stage | 1827 | 913 | 2.0 |
| critical_first | 902 | 902 | 1.0 |
| critical_last | 878 | 878 | 1.0 |

## 9. Thinking Token Correlation

- **With thinking tokens:** 20 experiments, tool exact=11/20 (55.0%)
- **Without thinking tokens:** 300 experiments, tool exact=240/300 (80.0%)

## 10. Gemini vs Deterministic Eval Agreement

- **Tool agreement:** 320/320 (100.0%)
- **Avg Gemini args score:** 7.7/10
- **Avg Gemini overall score:** 7.6/10

| Gemini Tool Verdict | Count | Det. Exact Match |
|--------------------:|------:|-----------------:|
| correct | 251 | 251 |
| acceptable | 30 | 0 |
| wrong | 39 | 0 |

## 11. Recommendations

_Based on experimental findings — fill in after reviewing results._

1. **Best strategy:** `6_tool_description_verbosity:full_desc` (19/20 = 95% exact)
2. **Prefix completion effect:**
3. **Boolean probing viability:**
4. **Few-shot sweet spot:**
5. **Field ordering impact:**
6. **Two-stage vs joint:**
7. **Recommended production configuration:**
