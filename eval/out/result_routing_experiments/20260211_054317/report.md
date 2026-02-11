# MedGemma 4B — Result Evaluation, Planning & Routing Experiments

**Date:** 2026-02-11 06:02
**Model:** `google/medgemma-1.5-4b-it`
**Endpoint:** `https://sbx7zjulvioxoh-8000.proxy.runpod.net`
**Total experiments:** 217
**Errors:** 7

## 1. Executive Summary

- **Exact correct:** 97/210 (46.2%)
- **Acceptable:** 123/210 (58.6%)
- **Total LLM calls:** 260
- **Avg latency per experiment:** 2401ms
- **Thinking tokens observed:** 3/210 (1.4%)

## 2. Strategy Comparison Table

| Category | Strategy | N | Exact | Acceptable | Avg Latency (ms) | Calls |
|----------|----------|---|-------|------------|-------------------|-------|
| Result Quality | direct | 17 | 16/17 (94.1%) | 16/17 (94.1%) | 1365 | 17 |
| Next Action Routing | routing_T0.0 | 20 | 10/20 (50.0%) | 16/20 (80.0%) | 1753 | 20 |
| Next Action Routing | routing_T0.3 | 18 | 9/18 (50.0%) | 14/18 (77.8%) | 1499 | 18 |
| Full Plan | no_prefix | 10 | 0/10 (0.0%) | 0/10 (0.0%) | 2525 | 10 |
| Full Plan | reason_first | 10 | 1/10 (10.0%) | 2/10 (20.0%) | 11067 | 20 |
| Full Plan | thinking_prefix | 10 | 0/10 (0.0%) | 1/10 (10.0%) | 2645 | 10 |
| Reactive Planning | snapshot_0 | 10 | 7/10 (70.0%) | 7/10 (70.0%) | 1661 | 10 |
| Reactive Planning | snapshot_1 | 10 | 6/10 (60.0%) | 6/10 (60.0%) | 1413 | 10 |
| Reactive Planning | snapshot_2 | 10 | 6/10 (60.0%) | 6/10 (60.0%) | 1592 | 10 |
| Sufficiency | no_think | 15 | 8/15 (53.3%) | 8/15 (53.3%) | 1760 | 15 |
| Sufficiency | think | 15 | 8/15 (53.3%) | 8/15 (53.3%) | 1382 | 15 |
| Error Recovery | no_think | 13 | 7/13 (53.8%) | 9/13 (69.2%) | 1717 | 13 |
| Error Recovery | think | 13 | 7/13 (53.8%) | 9/13 (69.2%) | 1473 | 13 |
| Plan Vs Reactive | full_plan | 10 | 0/10 (0.0%) | 0/10 (0.0%) | 2406 | 10 |
| Plan Vs Reactive | reactive_sim | 10 | 0/10 (0.0%) | 6/10 (60.0%) | 7042 | 50 |
| Thinking Effect | no_think | 10 | 6/10 (60.0%) | 8/10 (80.0%) | 1497 | 10 |
| Thinking Effect | think | 9 | 6/9 (66.7%) | 7/9 (77.8%) | 1307 | 9 |

## 3. Result Quality Assessment Analysis (Cat 1)

**Accuracy:** 16/17 (94.1%)

**Confusion Matrix (rows=expected, cols=predicted):**

| Expected \ Predicted | success_rich | success_part | no_results | error_retrya | error_fatal |
|---|---|---|---|---|---|
| success_rich | **6** | . | . | . | . |
| success_partial | 1 | **3** | . | . | . |
| no_results | . | . | **3** | . | . |
| error_retryable | . | . | . | **2** | . |
| error_fatal | . | . | . | . | **2** |

| Scenario | Tool | Expected | Predicted | Correct? |
|----------|------|----------|-----------|----------|
| S-01 | check_drug_safety | success_rich | success_rich | OK |
| S-02 | search_medical_literature | success_rich | success_rich | OK |
| S-03 | check_drug_interactions | success_rich | success_rich | OK |
| S-04 | find_clinical_trials | success_rich | success_rich | OK |
| S-05 | search_patient | success_rich | success_rich | OK |
| S-06 | get_patient_chart | success_rich | success_rich | OK |
| P-01 | check_drug_safety | success_partial | success_rich | WRONG |
| P-02 | search_patient | success_partial | success_partial | OK |
| P-03 | check_drug_interactions | success_partial | success_partial | OK |
| P-04 | search_medical_literature | success_partial | success_partial | OK |
| E-01 | search_medical_literature | no_results | no_results | OK |
| E-02 | find_clinical_trials | no_results | no_results | OK |
| E-03 | search_patient | no_results | no_results | OK |
| X-01 | check_drug_safety | error_retryable | error_retryable | OK |
| X-02 | get_patient_chart | error_fatal | error_fatal | OK |
| X-03 | check_drug_interactions | error_fatal | error_fatal | OK |
| X-04 | search_medical_literature | error_retryable | error_retryable | OK |

## 4. Next-Action Routing Analysis (Cat 2)

**routing_T0.0:** exact=10/20 (50.0%), acceptable=16/20 (80.0%)
**routing_T0.3:** exact=9/18 (50.0%), acceptable=14/18 (77.8%)

**Action Confusion Matrix (all temps combined):**

| Expected \ Predicted | synthesize | retry_same | retry_differ | call_another | ask_user |
|---|---|---|---|---|---|
| synthesize | **10** | . | 2 | . | . |
| retry_same | . | **4** | . | . | . |
| retry_different_args | . | . | **2** | . | . |
| call_another_tool | 4 | 2 | . | **6** | . |
| ask_user | 2 | 2 | 4 | . | . |

## 5. Full-Plan Decomposition Analysis (Cat 3)

**no_prefix:** sequence exact=0/10 (0.0%), tools correct (any order)=0/10 (0.0%)
**thinking_prefix:** sequence exact=0/10 (0.0%), tools correct (any order)=1/10 (10.0%)
**reason_first:** sequence exact=1/10 (10.0%), tools correct (any order)=2/10 (20.0%)

| Task | no_prefix | thinking | reason_first | Expected |
|------|-----------|----------|--------------|----------|
| T-01 | X searc,get_p,check,check,presc | X searc,get_p,check,searc,check | X searc,get_p,check,check,check | searc,get_p,check |
| T-02 | X check,check,searc,find_,searc | X check,searc,check,searc,check | X searc,get_p,check,searc,save_ | check,searc |
| T-03 | X searc,get_p,check,check,save_ | ~ get_p,check,save_,check,save_ | X searc,get_p,check,check,save_ | get_p,check,save_ |
| T-04 | X searc,find_,check,check | X searc,find_,check,check | X searc,searc,analy,analy,analy | searc,find_ |
| T-05 | X searc,get_p,check,add_a,presc | X check,searc,get_p,add_a,presc | X searc,get_p,check,check,presc | searc,add_a,presc |
| T-06 | X check,searc,get_p,presc,save_ | X check,searc,check,find_,searc | X presc,save_,get_p,get_p,get_p | presc,save_ |
| T-07 | X check,check,searc,get_p,save_ | X check,check,searc,find_,searc | X searc,get_p,check,check,searc | check,check,searc |
| T-08 | X searc,get_p,check,check | X searc,get_p,check,check,searc | OK searc,get_p,check | searc,get_p,check |
| T-09 | X searc,find_,check,check | X searc,find_,check,check | ~ searc,searc,searc,searc,find_ | searc,find_ |
| T-10 | X get_p,searc,check,check | X get_p,check,check,searc,save_ | X searc,searc,searc,searc,searc | get_p,check,check |

## 6. Reactive Planning Analysis (Cat 4)

**snapshot_0:** correct next tool=7/10 (70.0%)
**snapshot_1:** correct next tool=6/10 (60.0%)
**snapshot_2:** correct next tool=6/10 (60.0%)

| Task | Snap 0 | Snap 1 | Snap 2 |
|------|--------|--------|--------|
| T-01 | OK (search_p) | OK (get_pati) | OK (check_dr) |
| T-02 | OK (check_dr) | X (check_dr) | X (check_dr) |
| T-03 | X (search_p) | OK (check_dr) | OK (save_cli) |
| T-04 | OK (search_m) | OK (find_cli) | X (find_cli) |
| T-05 | OK (search_p) | X (search_p) | OK (prescrib) |
| T-06 | X (search_p) | OK (save_cli) | X (search_p) |
| T-07 | OK (check_dr) | OK (check_dr) | OK (search_m) |
| T-08 | OK (search_p) | X (search_p) | OK (check_dr) |
| T-09 | X (find_cli) | OK (find_cli) | X (find_cli) |
| T-10 | OK (get_pati) | X (check_dr) | OK (check_dr) |

## 7. Full-Plan vs Reactive Head-to-Head (Cat 7)

**full_plan:** exact=0/10 (0.0%), acceptable=0/10 (0.0%), avg calls=1.0, avg latency=2406ms
**reactive_sim:** exact=0/10 (0.0%), acceptable=6/10 (60.0%), avg calls=5.0, avg latency=7042ms

| Task | Full-Plan | Reactive | Expected |
|------|-----------|----------|----------|
| T-01 | X searc,get_p,check,check,presc | X searc,get_p,check,check,check | searc,get_p,check |
| T-02 | X check,check,searc,find_,searc | X check,check,check,check,check | check,searc |
| T-03 | X searc,get_p,check,check,save_ | X searc,get_p,check,check,check | get_p,check,save_ |
| T-04 | X searc,find_,check,check | ~ searc,find_,find_,find_,find_ | searc,find_ |
| T-05 | X searc,get_p,check,add_a,presc | ~ searc,searc,add_a,presc,searc | searc,add_a,presc |
| T-06 | X check,searc,get_p,presc,save_ | X searc,presc,save_,check,save_ | presc,save_ |
| T-07 | X check,check,searc,get_p,save_ | ~ check,check,searc,searc,searc | check,check,searc |
| T-08 | X searc,get_p,check,check | ~ searc,searc,get_p,check,check | searc,get_p,check |
| T-09 | X searc,find_,check,check | ~ find_,searc,find_,find_,find_ | searc,find_ |
| T-10 | X get_p,searc,check,check | ~ get_p,check,check,check,check | get_p,check,check |

## 8. Sufficiency Assessment Analysis (Cat 5)

**no_think:** correct=8/15 (53.3%)
**think:** correct=8/15 (53.3%)

| Scenario | Expected | no_think | think |
|----------|----------|----------|-------|
| SUF-01 | sufficient | X (insuf) | X (insuf) |
| SUF-02 | sufficient | X (insuf) | X (insuf) |
| SUF-03 | sufficient | X (insuf) | X (insuf) |
| SUF-04 | sufficient | X (insuf) | X (insuf) |
| SUF-05 | sufficient | X (insuf) | X (insuf) |
| SUF-06 | insufficient | OK (insuf) | OK (insuf) |
| SUF-07 | insufficient | OK (insuf) | OK (insuf) |
| SUF-08 | insufficient | OK (insuf) | OK (insuf) |
| SUF-09 | insufficient | OK (insuf) | OK (insuf) |
| SUF-10 | insufficient | OK (insuf) | OK (insuf) |
| SUF-11 | insufficient | OK (insuf) | OK (insuf) |
| SUF-12 | insufficient | OK (insuf) | OK (insuf) |
| SUF-13 | insufficient | OK (insuf) | OK (insuf) |
| SUF-14 | sufficient | X (insuf) | X (insuf) |
| SUF-15 | sufficient | X (insuf) | X (insuf) |

## 9. Error Recovery Analysis (Cat 6)

**no_think:** exact=7/13 (53.8%), acceptable=9/13 (69.2%)
**think:** exact=7/13 (53.8%), acceptable=9/13 (69.2%)

**Strategy Confusion Matrix:**

| Expected \ Predicted | retry_same | retry_differ | skip_and_con | ask_user |
|---|---|---|---|---|
| retry_same | **9** | . | . | . |
| retry_different_args | 1 | **5** | . | . |
| skip_and_continue | 2 | 2 | . | . |
| ask_user | 3 | 4 | . | . |

## 10. Thinking Mode Effect (Cat 8 + Cross-Category)

**no_think:** exact=6/10 (60.0%), acceptable=8/10 (80.0%)
**think:** exact=6/9 (66.7%), acceptable=7/9 (77.8%)

**Cross-category thinking comparison (Cat 5 + Cat 6 + Cat 8):**

- **Sufficiency:** no_think=8/15 → think=8/15
- **Error Recovery:** no_think=7/13 → think=7/13
- **Hard Scenarios:** no_think=6/10 → think=6/9

## 11. Latency Analysis

| Category | Strategy | Avg Total (ms) | Avg Per-Call (ms) | Calls/Exp |
|----------|----------|---------------|-------------------|-----------|
| result quality | direct | 1365 | 1365 | 1.0 |
| next action rou | routing_T0.0 | 1753 | 1753 | 1.0 |
| next action rou | routing_T0.3 | 1499 | 1499 | 1.0 |
| full plan | no_prefix | 2525 | 2525 | 1.0 |
| full plan | reason_first | 11067 | 5534 | 2.0 |
| full plan | thinking_prefix | 2645 | 2645 | 1.0 |
| reactive planni | snapshot_0 | 1661 | 1661 | 1.0 |
| reactive planni | snapshot_1 | 1413 | 1413 | 1.0 |
| reactive planni | snapshot_2 | 1592 | 1592 | 1.0 |
| sufficiency | no_think | 1760 | 1760 | 1.0 |
| sufficiency | think | 1382 | 1382 | 1.0 |
| error recovery | no_think | 1717 | 1717 | 1.0 |
| error recovery | think | 1473 | 1473 | 1.0 |
| plan vs reactiv | full_plan | 2406 | 2406 | 1.0 |
| plan vs reactiv | reactive_sim | 7042 | 1408 | 5.0 |
| thinking effect | no_think | 1497 | 1497 | 1.0 |
| thinking effect | think | 1307 | 1307 | 1.0 |

## 12. Gemini vs Deterministic Eval Agreement

- **Agreement:** 169/202 (83.7%)
- **Avg Gemini reasoning score:** 7.0/10
- **Avg Gemini overall score:** 7.1/10

| Gemini Verdict | Count | Det. Exact Match |
|---------------:|------:|-----------------:|
| correct | 125 | 92 |
| acceptable | 22 | 0 |
| wrong | 55 | 0 |

## 13. Recommendations

- **Result Quality:** Best strategy = `direct` (94% exact)
- **Next Action Routing:** Best strategy = `routing_T0.3` (50% exact)
- **Full Plan:** Best strategy = `reason_first` (10% exact)
- **Reactive Planning:** Best strategy = `snapshot_0` (70% exact)
- **Sufficiency:** Best strategy = `think` (53% exact)
- **Error Recovery:** Best strategy = `think` (54% exact)
- **Plan Vs Reactive:** Best strategy = `reactive_sim` (0% exact)
- **Thinking Effect:** Best strategy = `think` (67% exact)

_Fill in detailed recommendations after reviewing results._

## Errors

- `cat2-routing-T0.3-R-02`: Expecting ',' delimiter: line 3 column 274 (char 301)
- `cat2-routing-T0.3-R-03`: Expecting ',' delimiter: line 3 column 274 (char 301)
- `cat6-recovery-think-ERR-08`: Expecting ',' delimiter: line 3 column 274 (char 303)
- `cat6-recovery-no_think-ERR-09`: Expecting ',' delimiter: line 3 column 274 (char 303)
- `cat6-recovery-think-ERR-09`: Expecting ',' delimiter: line 3 column 274 (char 303)
- `cat6-recovery-no_think-ERR-13`: Expecting ',' delimiter: line 3 column 274 (char 303)
- `cat8-thinking-routing-think-R-09`: Expecting ',' delimiter: line 3 column 274 (char 311)
