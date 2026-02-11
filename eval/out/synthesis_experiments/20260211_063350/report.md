# MedGemma 4B — Response Synthesis Experiments

**Date:** 2026-02-11 06:50
**Model:** `google/medgemma-1.5-4b-it`
**Endpoint:** `https://sbx7zjulvioxoh-8000.proxy.runpod.net`
**Total experiments:** 215
**Errors:** 0

## 1. Executive Summary

- **Avg key fact rate:** 83.9%
- **Source-clean responses:** 186/215 (86.5%)
- **Avg word count:** 70
- **Avg latency:** 2480ms
- **Thinking tokens observed:** 16/215 (7.4%)
- **Gemini judged:** 211 results
- **Avg completeness:** 8.9/10
- **Avg accuracy:** 9.6/10
- **Avg conciseness:** 9.1/10
- **Avg clinical tone:** 9.5/10
- **Avg source hiding:** 10.0/10
- **Avg overall:** 8.9/10

## 2. Strategy Comparison Table

| Category | Strategy | N | Fact Rate | Clean | Avg Words | Avg Latency | Gemini Overall |
|----------|----------|---|-----------|-------|-----------|-------------|----------------|
| Baseline | production | 30 | 83% | 26/30 | 64 | 2103ms | 8.8 |
| Thinking | thinking_prefix | 30 | 68% | 28/30 | 72 | 4448ms | 8.8 |
| Temperature | T=0.1 | 15 | 80% | 14/15 | 40 | 1210ms | 8.9 |
| Temperature | T=0.3 | 15 | 86% | 14/15 | 39 | 1193ms | 8.9 |
| Temperature | T=0.5 | 15 | 90% | 14/15 | 43 | 1333ms | 8.7 |
| Temperature | T=0.7 | 15 | 87% | 12/15 | 52 | 1705ms | 8.9 |
| Prompt Variation | brief | 15 | 86% | 10/15 | 47 | 1800ms | 9.3 |
| Prompt Variation | comprehensive | 15 | 80% | 12/15 | 210 | 5956ms | 8.4 |
| Prompt Variation | structured | 15 | 88% | 9/15 | 94 | 3097ms | 8.3 |
| Reasoning Ctx | no_reasoning | 10 | 94% | 9/10 | 79 | 2338ms | 9.1 |
| Reasoning Ctx | with_reasoning | 10 | 100% | 10/10 | 78 | 2054ms | 9.5 |
| Token Limit | tok=128 | 10 | 86% | 9/10 | 48 | 1546ms | 9.4 |
| Token Limit | tok=256 | 10 | 90% | 9/10 | 52 | 1617ms | 9.7 |
| Token Limit | tok=512 | 10 | 85% | 10/10 | 51 | 1672ms | 9.4 |

## 3. Baseline Synthesis Analysis (Cat 1)

### By Scenario Type

| Type | N | Avg Fact Rate | Clean | Avg Words | Gemini Overall |
|------|---|---------------|-------|-----------|----------------|
| direct | 5 | 100% | 5/5 | 39 | 9.6 |
| empty | 3 | 67% | 2/3 | 15 | 10.0 |
| error | 4 | 25% | 4/4 | 121 | 4.8 |
| multi_tool | 3 | 100% | 3/3 | 27 | 10.0 |
| partial | 4 | 88% | 3/4 | 34 | 8.8 |
| reasoning_tool | 5 | 90% | 5/5 | 147 | 9.0 |
| success_rich | 6 | 100% | 4/6 | 42 | 9.7 |

### Per-Scenario Detail

| Scenario | Query | Fact Rate | Clean | Words | Gemini |
|----------|-------|-----------|-------|-------|--------|
| SC-01 | Check FDA safety warnings for dofetilide... | 100% | Y | 28 | 10 |
| SC-02 | Search for studies on SGLT2 inhibitors a... | 100% | Y | 63 | 9 |
| SC-03 | Check drug interactions between warfarin... | 100% | Y | 21 | 10 |
| SC-04 | Find clinical trials for triple-negative... | 100% | N | 83 | 9 |
| SC-05 | Search for patient Maria Garcia... | 100% | Y | 8 | 10 |
| SC-06 | Get the chart for patient abc-123... | 100% | N | 49 | 10 |
| SC-07 | Is metformin safe for patients with CKD?... | 50% | Y | 55 | 9 |
| SC-08 | Find patient James Wilson... | 100% | N | 47 | 9 |
| SC-09 | Check interactions between warfarin and ... | 100% | Y | 12 | 9 |
| SC-10 | Search for studies on rare enzyme defici... | 100% | Y | 22 | 8 |
| SC-11 | Search PubMed for xylotriazole enzyme de... | 0% | Y | 21 | 10 |
| SC-12 | Find clinical trials for hereditary angi... | 100% | Y | 10 | 10 |
| SC-13 | Search for patient Xyz Nonexist... | 100% | N | 13 | 10 |
| SC-14 | Check FDA warnings for amiodarone... | 0% | Y | 22 | 1 |
| SC-15 | Get chart for this patient... | 100% | Y | 12 | 10 |
| SC-16 | Check interactions for aspirin... | 0% | Y | 269 | 1 |
| SC-17 | Search for diabetes management articles... | 0% | Y | 181 | 7 |
| SC-18 | Find patient John Smith and review his c... | 100% | Y | 24 | 10 |
| SC-19 | Review patient Smith's chart and check m... | 100% | Y | 47 | 10 |
| SC-20 | Find Maria Garcia and get her complete c... | 100% | Y | 10 | 10 |
| SC-21 | Hello, how are you?... | 100% | Y | 38 | 10 |
| SC-22 | What is hypertension?... | 100% | Y | 33 | 8 |
| SC-23 | Thanks for the help!... | 100% | Y | 10 | 10 |
| SC-24 | What are ACE inhibitors used for?... | 100% | Y | 31 | 10 |
| SC-25 | Explain the mechanism of action of metfo... | 100% | Y | 82 | 10 |
| SC-26 | Best antihypertensive for CKD stage 3?... | 100% | Y | 136 | 9 |
| SC-27 | Patient on warfarin needs dental procedu... | 75% | Y | 57 | 10 |
| SC-28 | New T2DM patient, what's the latest on S... | 100% | Y | 67 | 10 |
| SC-29 | Treatment options for triple-negative br... | 100% | Y | 392 | 7 |
| SC-30 | Review Maria Garcia's medications for po... | 75% | Y | 82 | 9 |

## 4. Thinking Effect Analysis (Cat 2 vs Cat 1)

### Paired Comparison

| Scenario | Baseline Facts | Thinking Facts | Baseline Words | Thinking Words | Baseline Gemini | Thinking Gemini |
|----------|----------------|----------------|----------------|----------------|-----------------|-----------------|
| SC-01 | 100% | 0% | 28 | 0 | 10 | — |
| SC-02 | 100% | 100% | 63 | 38 | 9 | 10 |
| SC-03 | 100% | 100% | 21 | 71 | 10 | 10 |
| SC-04 | 100% | 100% | 83 | 74 | 9 | 10 |
| SC-05 | 100% | 0% | 8 | 0 | 10 | — |
| SC-06 | 100% | 0% | 49 | 0 | 10 | — |
| SC-07 | 50% | 50% | 55 | 81 | 9 | 9 |
| SC-08 | 100% | 67% | 47 | 73 | 9 | 10 |
| SC-09 | 100% | 100% | 12 | 5 | 9 | 4 |
| SC-10 | 100% | 100% | 22 | 33 | 8 | 9 |
| SC-11 | 0% | 0% | 21 | 38 | 10 | 9 |
| SC-12 | 100% | 100% | 10 | 252 | 10 | 9 |
| SC-13 | 100% | 0% | 13 | 243 | 10 | 0 |
| SC-14 | 0% | 0% | 22 | 68 | 1 | 8 |
| SC-15 | 100% | 100% | 12 | 11 | 10 | 10 |
| SC-16 | 0% | 100% | 269 | 17 | 1 | 10 |
| SC-17 | 0% | 0% | 181 | 44 | 7 | 10 |
| SC-18 | 100% | 100% | 24 | 56 | 10 | 10 |
| SC-19 | 100% | 100% | 47 | 164 | 10 | 10 |
| SC-20 | 100% | 50% | 10 | 8 | 10 | 9 |
| SC-21 | 100% | 100% | 38 | 15 | 10 | 9 |
| SC-22 | 100% | 100% | 33 | 41 | 8 | 6 |
| SC-23 | 100% | 100% | 10 | 10 | 10 | 10 |
| SC-24 | 100% | 100% | 31 | 35 | 10 | 9 |
| SC-25 | 100% | 100% | 82 | 37 | 10 | 10 |
| SC-26 | 100% | 0% | 136 | 0 | 9 | — |
| SC-27 | 75% | 100% | 57 | 227 | 10 | 9 |
| SC-28 | 100% | 100% | 67 | 43 | 10 | 10 |
| SC-29 | 100% | 100% | 392 | 352 | 7 | 9 |
| SC-30 | 75% | 75% | 82 | 123 | 9 | 10 |

**Aggregates:** Baseline fact rate=83%, Thinking=68% | Baseline words=64, Thinking=72 | Baseline Gemini=8.8, Thinking=8.8

## 5. Temperature Analysis (Cat 3)

| Temperature | N | Avg Fact Rate | Clean | Avg Words | Gemini Overall |
|-------------|---|---------------|-------|-----------|----------------|
| 0.1 | 15 | 80% | 14/15 | 40 | 8.9 |
| 0.3 | 15 | 86% | 14/15 | 39 | 8.9 |
| 0.5 | 15 | 90% | 14/15 | 43 | 8.7 |
| 0.7 | 15 | 87% | 12/15 | 52 | 8.9 |

### Per-Scenario Temperature Effect

| Scenario | T=0.1 Facts | T=0.3 Facts | T=0.5 Facts | T=0.7 Facts |
|----------|-------------|-------------|-------------|-------------|
| SC-01 | 100% | 100% | 100% | 100% |
| SC-02 | 100% | 100% | 100% | 100% |
| SC-03 | 100% | 100% | 100% | 100% |
| SC-04 | 100% | 100% | 100% | 100% |
| SC-05 | 100% | 100% | 100% | 50% |
| SC-06 | 100% | 100% | 100% | 100% |
| SC-07 | 50% | 50% | 50% | 50% |
| SC-08 | 67% | 67% | 100% | 100% |
| SC-11 | 0% | 100% | 100% | 100% |
| SC-14 | 0% | 0% | 0% | 0% |
| SC-18 | 100% | 100% | 100% | 100% |
| SC-19 | 80% | 80% | 100% | 100% |
| SC-21 | 100% | 100% | 100% | 100% |
| SC-22 | 100% | 100% | 100% | 100% |
| SC-26 | 100% | 100% | 100% | 100% |

## 6. Prompt Variation Analysis (Cat 4)

| Variant | N | Avg Fact Rate | Clean | Avg Words | Gemini Overall |
|---------|---|---------------|-------|-----------|----------------|
| structured | 15 | 88% | 9/15 | 94 | 8.3 |
| brief | 15 | 86% | 10/15 | 47 | 9.3 |
| comprehensive | 15 | 80% | 12/15 | 210 | 8.4 |

### vs Production Baseline (Cat 1, same 15 scenarios)

- **Production baseline:** fact_rate=83%, words=45, gemini=8.9
- **structured:** fact_rate=88%, words=94, gemini=8.3
- **brief:** fact_rate=86%, words=47, gemini=9.3
- **comprehensive:** fact_rate=80%, words=210, gemini=8.4

## 7. Reasoning Context Effect (Cat 5)

| Condition | N | Avg Fact Rate | Clean | Avg Words | Gemini Overall |
|-----------|---|---------------|-------|-----------|----------------|
| With reasoning | 10 | 100% | 10/10 | 78 | 9.5 |
| No reasoning | 10 | 94% | 9/10 | 79 | 9.1 |

### Paired Comparison

| Scenario | With Facts | Without Facts | With Gemini | Without Gemini |
|----------|-----------|--------------|-------------|----------------|
| SC-01 | 100% | 100% | 10 | 9 |
| SC-02 | 100% | 100% | 8 | 10 |
| SC-03 | 100% | 100% | 10 | 10 |
| SC-06 | 100% | 100% | 10 | 10 |
| SC-18 | 100% | 100% | 10 | 10 |
| SC-26 | 100% | 67% | 9 | 7 |
| SC-27 | 100% | 100% | 10 | 9 |
| SC-28 | 100% | 100% | 10 | 10 |
| SC-29 | 100% | 100% | 8 | 7 |
| SC-30 | 100% | 75% | 10 | 9 |

## 8. Token Limit Analysis (Cat 6)

| Max Tokens | N | Avg Fact Rate | Avg Words | Gemini Overall | Gemini Conciseness |
|------------|---|---------------|-----------|----------------|-------------------|
| 128 | 10 | 86% | 48 | 9.4 | 8.8 |
| 256 | 10 | 90% | 52 | 9.7 | 9.4 |
| 512 | 10 | 85% | 51 | 9.4 | 8.9 |

### Quality vs Brevity Tradeoff by Scenario

| Scenario | 128 Facts / Words | 256 Facts / Words | 512 Facts / Words |
|----------|-------------------|-------------------|-------------------|
| SC-01 | 100% / 44w | 100% / 28w | 100% / 31w |
| SC-02 | 100% / 50w | 100% / 69w | 67% / 34w |
| SC-03 | 100% / 18w | 100% / 17w | 100% / 15w |
| SC-06 | 100% / 43w | 100% / 49w | 100% / 48w |
| SC-07 | 50% / 46w | 50% / 57w | 50% / 42w |
| SC-18 | 100% / 28w | 100% / 28w | 100% / 32w |
| SC-19 | 60% / 73w | 80% / 32w | 80% / 36w |
| SC-26 | 100% / 81w | 100% / 101w | 100% / 142w |
| SC-28 | 100% / 33w | 100% / 40w | 100% / 33w |
| SC-30 | 50% / 59w | 75% / 97w | 50% / 98w |

## 9. Key Fact Inclusion Analysis

### Most Frequently Missing Facts (Cat 1 Baseline)

| Fact Pattern | Times Missing | Times Tested | Hit Rate |
|-------------|---------------|--------------|----------|
| `no.*warning|no.*boxed|no FDA` | 1 | 1 | 0.0% |
| `no.*result|no.*found|no.*article|0 resul` | 1 | 1 | 0.0% |
| `timed out|unavailable|unable|error|retry` | 1 | 1 | 0.0% |
| `two|2|another|second|at least.*drug|addi` | 1 | 1 | 0.0% |
| `error|unavailable|unable|service|issue|t` | 1 | 1 | 0.0% |
| `warfarin` | 1 | 3 | 66.7% |
| `Maria Garcia` | 1 | 3 | 66.7% |

## 10. Source Leakage Analysis

| Leaked Term | Occurrences | % of Non-Direct Experiments |
|-------------|-------------|----------------------------|
| `search_patient` | 8 | 4.2% |
| `tool` | 8 | 4.2% |
| `get_patient_chart` | 5 | 2.6% |
| `search_medical_literature` | 3 | 1.6% |
| `PubMed` | 3 | 1.6% |
| `the tool` | 2 | 1.0% |
| `check_drug_safety` | 2 | 1.0% |
| `ClinicalTrials.gov` | 1 | 0.5% |
| `find_clinical_trials` | 1 | 0.5% |

## 11. Deterministic vs Gemini Agreement

### Fact Rate vs Gemini Completeness

| Fact Rate Range | N | Avg Gemini Completeness | Avg Gemini Overall |
|-----------------|---|-------------------------|-------------------|
| 0-25% | 17 | 5.2 | 5.4 |
| 50-75% | 25 | 8.6 | 8.6 |
| 75-100% | 169 | 9.3 | 9.3 |

### Source Clean vs Gemini Source Hiding

| Deterministic | N | Avg Gemini Source Hiding |
|---------------|---|-------------------------|
| Clean | 182 | 10.0 |
| Leaked | 29 | 10.0 |

## 12. Latency Analysis

| Category | Strategy | N | Avg Latency (ms) | Min | Max |
|----------|----------|---|-------------------|-----|-----|
| Baseline | production | 30 | 2103 | 342 | 8418 |
| Thinking | thinking_prefix | 30 | 4448 | 748 | 8427 |
| Temperature | T=0.1 | 15 | 1210 | 496 | 3448 |
| Temperature | T=0.3 | 15 | 1193 | 428 | 3132 |
| Temperature | T=0.5 | 15 | 1333 | 427 | 3303 |
| Temperature | T=0.7 | 15 | 1705 | 486 | 4417 |
| Prompt Variation | brief | 15 | 1800 | 646 | 7608 |
| Prompt Variation | comprehensive | 15 | 5956 | 778 | 8446 |
| Prompt Variation | structured | 15 | 3097 | 370 | 5191 |
| Reasoning Ctx | no_reasoning | 10 | 2338 | 502 | 5350 |
| Reasoning Ctx | with_reasoning | 10 | 2054 | 411 | 5184 |
| Token Limit | tok=128 | 10 | 1546 | 626 | 2325 |
| Token Limit | tok=256 | 10 | 1617 | 433 | 2915 |
| Token Limit | tok=512 | 10 | 1672 | 386 | 3462 |

## 13. Recommendations

### Best Strategy by Gemini Dimension

- **completeness:** 6_token_limit/tok=256 (9.6/10)
- **accuracy:** 4_prompt_variation/structured (10.0/10)
- **conciseness:** 3_temperature/T=0.7 (9.5/10)
- **clinical_tone:** 6_token_limit/tok=256 (10.0/10)
- **source_hiding:** 1_baseline/production (10.0/10)
- **overall:** 6_token_limit/tok=256 (9.7/10)

### Best Strategy by Deterministic Metrics

- **Baseline:** production (combined=0.84)
- **Thinking:** thinking_prefix (combined=0.76)
- **Temperature:** T=0.5 (combined=0.91)
- **Prompt Variation:** brief (combined=0.81)
- **Reasoning Ctx:** with_reasoning (combined=1.00)
- **Token Limit:** tok=256 (combined=0.90)
