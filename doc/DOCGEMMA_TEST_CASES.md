# DocGemma Test Cases

Test cases for the DocGemma Connect agent. All cases assume a medical expert user with full tool access.

## Test Case Schema

Each test case includes:
- `id`: Unique identifier
- `prompt`: The user's input text
- `has_image`: Whether an image is attached
- `image_type`: Type of image if attached (xray, ct, mri, pathology, dermatology)
- `expected_complexity`: direct | complex
- `expected_tools`: List of tools that should be called
- `expected_subtasks`: Number of subtasks if decomposed
- `notes`: Additional context for the test

---

## Category 1: Direct/Simple Queries (10 cases)

### D1: Greeting
```yaml
id: D1
prompt: "Good morning, I'm Dr. Smith starting my shift."
has_image: false
image_type: null
expected_complexity: direct
expected_tools: []
expected_subtasks: 0
notes: Simple greeting, no tools needed.
```

### D2: Thank You
```yaml
id: D2
prompt: "Thanks, that's exactly what I needed."
has_image: false
image_type: null
expected_complexity: direct
expected_tools: []
expected_subtasks: 0
notes: Gratitude expression, no action needed.
```

### D3: Basic Mechanism Question
```yaml
id: D3
prompt: "Quick refresher - what's the mechanism of action for metformin?"
has_image: false
image_type: null
expected_complexity: direct
expected_tools: []
expected_subtasks: 0
notes: Textbook knowledge, no tools needed.
```

### D4: Definition Request
```yaml
id: D4
prompt: "Define SIADH for me."
has_image: false
image_type: null
expected_complexity: direct
expected_tools: []
expected_subtasks: 0
notes: Basic clinical definition, can answer from training.
```

### D5: Clarification Follow-up
```yaml
id: D5
prompt: "Can you elaborate on the renal dosing adjustment you mentioned?"
has_image: false
image_type: null
expected_complexity: direct
expected_tools: []
expected_subtasks: 0
notes: Follow-up clarification, uses conversation context.
```

### D6: Physiology Question
```yaml
id: D6
prompt: "Walk me through the renin-angiotensin-aldosterone system."
has_image: false
image_type: null
expected_complexity: direct
expected_tools: []
expected_subtasks: 0
notes: Basic physiology, no external data needed.
```

### D7: Drug Class Question
```yaml
id: D7
prompt: "What are the main classes of antihypertensives?"
has_image: false
image_type: null
expected_complexity: direct
expected_tools: []
expected_subtasks: 0
notes: Standard pharmacology knowledge.
```

### D8: Calculation Question
```yaml
id: D8
prompt: "How do you calculate creatinine clearance using Cockcroft-Gault?"
has_image: false
image_type: null
expected_complexity: direct
expected_tools: []
expected_subtasks: 0
notes: Formula explanation, no lookup needed.
```

### D9: Capabilities Question
```yaml
id: D9
prompt: "What clinical decision support can you provide?"
has_image: false
image_type: null
expected_complexity: direct
expected_tools: []
expected_subtasks: 0
notes: Question about agent capabilities.
```

### D10: Abbreviation Question
```yaml
id: D10
prompt: "What does CHADS-VASc stand for?"
has_image: false
image_type: null
expected_complexity: direct
expected_tools: []
expected_subtasks: 0
notes: Standard acronym, no lookup needed.
```

---

## Category 2: Single Tool Queries (12 cases)

### S1: Drug Safety Check
```yaml
id: S1
prompt: "Pull up the boxed warnings for Xarelto."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["check_drug_safety"]
expected_subtasks: 1
notes: Single FDA safety lookup.
```

### S2: Drug Interaction Check
```yaml
id: S2
prompt: "Check for interactions between warfarin and amiodarone."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["check_drug_interactions"]
expected_subtasks: 1
notes: Two-drug interaction check.
```

### S3: Literature Search - Treatment
```yaml
id: S3
prompt: "What's the latest evidence on PCSK9 inhibitors for secondary prevention in statin-intolerant patients?"
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["search_medical_literature"]
expected_subtasks: 1
notes: Specialized literature query.
```

### S4: Clinical Trial Search
```yaml
id: S4
prompt: "Find recruiting trials for metastatic triple-negative breast cancer."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["find_clinical_trials"]
expected_subtasks: 1
notes: Clinical trial search for specific condition.
```

### S5: Patient Record Lookup
```yaml
id: S5
prompt: "Pull up the records for patient John Smith, DOB 03/15/1978."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["get_patient_record"]
expected_subtasks: 1
notes: EHR read operation.
```

### S6: Patient Record Update
```yaml
id: S6
prompt: "Add penicillin allergy to patient Maria Garcia's chart - anaphylaxis in childhood."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["update_patient_record"]
expected_subtasks: 1
notes: EHR write operation.
```

### S7: Literature Search - Guidelines
```yaml
id: S7
prompt: "Find current AHA guidelines on anticoagulation in atrial fibrillation."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["search_medical_literature"]
expected_subtasks: 1
notes: Guideline-specific literature search.
```

### S8: Drug Safety - Side Effects
```yaml
id: S8
prompt: "What are the FDA warnings for finasteride?"
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["check_drug_safety"]
expected_subtasks: 1
notes: Drug safety profile lookup.
```

### S9: Literature Search - Dosing
```yaml
id: S9
prompt: "What's the recommended vancomycin dosing for a patient with eGFR of 35?"
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["search_medical_literature"]
expected_subtasks: 1
notes: Renal dosing adjustment query.
```

### S10: Multiple Drug Interactions
```yaml
id: S10
prompt: "Check interactions between metformin, lisinopril, and atorvastatin."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["check_drug_interactions"]
expected_subtasks: 1
notes: Multi-drug interaction check.
```

### S11: Trial Search - Rare Disease
```yaml
id: S11
prompt: "Any recruiting trials for Fabry disease enzyme replacement therapy?"
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["find_clinical_trials"]
expected_subtasks: 1
notes: Rare disease trial search.
```

### S12: Literature Search - Differential
```yaml
id: S12
prompt: "Recent literature on workup for fatigue, weight loss, night sweats, and cervical lymphadenopathy."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["search_medical_literature"]
expected_subtasks: 1
notes: DDx support via literature.
```

---

## Category 3: Multi-Tool Queries (10 cases)

### M1: Record + Interaction Check
```yaml
id: M1
prompt: "Get patient 402's medication list and check if we can safely add Paxlovid for COVID."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["get_patient_record", "check_drug_interactions"]
expected_subtasks: 2
notes: Sequential operation - must get meds first, then check.
```

### M2: Safety + Interactions
```yaml
id: M2
prompt: "Patient has CKD stage 3 on metformin. Considering SGLT2 inhibitor - check contraindications and interactions."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["check_drug_safety", "check_drug_interactions"]
expected_subtasks: 2
notes: Both safety and interactions needed.
```

### M3: Record + Update
```yaml
id: M3
prompt: "Pull patient Thompson's record and add that they're starting warfarin 5mg daily."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["get_patient_record", "update_patient_record"]
expected_subtasks: 2
notes: Read then write operation.
```

### M4: Literature + Trials
```yaml
id: M4
prompt: "Find latest research on ketamine for treatment-resistant depression and any recruiting trials."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["search_medical_literature", "find_clinical_trials"]
expected_subtasks: 2
notes: Research plus trial search.
```

### M5: Three-Part Query
```yaml
id: M5
prompt: "Patient 789 with new A-fib. Pull their record, check apixaban interactions with current meds, and find latest anticoagulation guidelines."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["get_patient_record", "check_drug_interactions", "search_medical_literature"]
expected_subtasks: 3
notes: Three sequential tool calls needed.
```

### M6: Update + Safety
```yaml
id: M6
prompt: "Document that patient Chen is starting amiodarone 200mg daily and pull up the monitoring requirements."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["update_patient_record", "check_drug_safety"]
expected_subtasks: 2
notes: Write operation plus safety lookup.
```

### M7: Record + Literature
```yaml
id: M7
prompt: "Get patient Williams' HbA1c history and find current ADA guidelines on diabetes management."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["get_patient_record", "search_medical_literature"]
expected_subtasks: 2
notes: Patient data plus guideline search.
```

### M8: Comprehensive Drug Check
```yaml
id: M8
prompt: "Patient starting on tacrolimus - need boxed warnings, interactions with their cyclosporine history, and monitoring guidelines."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["check_drug_safety", "check_drug_interactions", "search_medical_literature"]
expected_subtasks: 3
notes: Full drug workup.
```

### M9: Trial Eligibility Check
```yaml
id: M9
prompt: "Patient 123 with refractory CLL - pull their treatment history and find any CAR-T trials they might qualify for."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["get_patient_record", "find_clinical_trials"]
expected_subtasks: 2
notes: Patient history needed for trial matching.
```

### M10: Safety + Interactions + Literature
```yaml
id: M10
prompt: "Evaluating isotretinoin for patient - need FDA warnings, interaction check with their current meds (SSRIs), and latest teratogenicity data."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: ["check_drug_safety", "check_drug_interactions", "search_medical_literature"]
expected_subtasks: 3
notes: Comprehensive pre-prescribing workup.
```

---

## Category 4: Image Analysis - Single Tool (8 cases)

### I1: Chest X-Ray
```yaml
id: I1
prompt: "CXR for patient in bed 4. Presenting with fever and productive cough x3 days. Read please."
has_image: true
image_type: xray
expected_complexity: complex
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
notes: Standard CXR interpretation with clinical context.
```

### I2: CT Abdomen
```yaml
id: I2
prompt: "CT abdomen for patient with RLQ pain. Rule out appendicitis."
has_image: true
image_type: ct
expected_complexity: complex
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
notes: CT interpretation for acute abdomen.
```

### I3: Brain MRI
```yaml
id: I3
prompt: "MRI brain for patient with new neurological deficits. Evaluate for acute stroke or mass lesion."
has_image: true
image_type: mri
expected_complexity: complex
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
notes: Neuroimaging interpretation.
```

### I4: Pathology Slide
```yaml
id: I4
prompt: "H&E slide from breast biopsy. Evaluate for malignancy and grade if applicable."
has_image: true
image_type: pathology
expected_complexity: complex
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
notes: Histopathology interpretation.
```

### I5: Longitudinal CXR
```yaml
id: I5
prompt: "Today's CXR for comparison with last week. Patient post-pneumonia treatment. Has the consolidation improved?"
has_image: true
image_type: xray
expected_complexity: complex
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
notes: Longitudinal comparison - MedGemma 1.5 capability.
```

### I6: Dermatology Consult
```yaml
id: I6
prompt: "Derm consult. 67yo male with this lesion on his back, present 6 months, recently changed color."
has_image: true
image_type: dermatology
expected_complexity: complex
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
notes: Skin lesion evaluation.
```

### I7: Chest CT - PE Workup
```yaml
id: I7
prompt: "Chest CT for patient Martinez. PE workup - assess for filling defects."
has_image: true
image_type: ct
expected_complexity: complex
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
notes: CT pulmonary angiography interpretation.
```

### I8: Musculoskeletal X-Ray
```yaml
id: I8
prompt: "Ankle X-ray, patient with inversion injury. Rule out fracture."
has_image: true
image_type: xray
expected_complexity: complex
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
notes: Trauma X-ray interpretation.
```

---

## Category 5: Image + Multi-Tool Queries (8 cases)

### IM1: CXR + Record + Literature
```yaml
id: IM1
prompt: "CXR shows RUL mass. Patient ID 555. Pull their smoking history and find current lung cancer screening guidelines."
has_image: true
image_type: xray
expected_complexity: complex
expected_tools: ["analyze_medical_image", "get_patient_record", "search_medical_literature"]
expected_subtasks: 3
notes: Complex multi-tool with image analysis.
```

### IM2: Image + Record Update
```yaml
id: IM2
prompt: "Read this chest CT for patient Martinez and add the findings to their record."
has_image: true
image_type: ct
expected_complexity: complex
expected_tools: ["analyze_medical_image", "update_patient_record"]
expected_subtasks: 2
notes: Image interpretation plus EHR documentation.
```

### IM3: Derm + Literature
```yaml
id: IM3
prompt: "Evaluate this pigmented lesion and find current melanoma screening guidelines."
has_image: true
image_type: dermatology
expected_complexity: complex
expected_tools: ["analyze_medical_image", "search_medical_literature"]
expected_subtasks: 2
notes: Skin lesion with guideline lookup.
```

### IM4: Path + Trials
```yaml
id: IM4
prompt: "This path slide shows what looks like HER2+ breast cancer. Confirm and find any recruiting trials."
has_image: true
image_type: pathology
expected_complexity: complex
expected_tools: ["analyze_medical_image", "find_clinical_trials"]
expected_subtasks: 2
notes: Pathology confirmation plus trial search.
```

### IM5: CXR + Drug Safety
```yaml
id: IM5
prompt: "CXR for patient on amiodarone. Check for pulmonary toxicity and pull up the monitoring guidelines."
has_image: true
image_type: xray
expected_complexity: complex
expected_tools: ["analyze_medical_image", "check_drug_safety"]
expected_subtasks: 2
notes: Drug-induced lung disease evaluation.
```

### IM6: MRI + Record
```yaml
id: IM6
prompt: "Brain MRI for patient 892. Evaluate for progression and pull their prior imaging notes."
has_image: true
image_type: mri
expected_complexity: complex
expected_tools: ["analyze_medical_image", "get_patient_record"]
expected_subtasks: 2
notes: Imaging with patient history context.
```

### IM7: Full Workup
```yaml
id: IM7
prompt: "New patient CT chest shows nodule. Get their smoking history, check lung cancer screening guidelines, and find any early-stage NSCLC trials."
has_image: true
image_type: ct
expected_complexity: complex
expected_tools: ["analyze_medical_image", "get_patient_record", "search_medical_literature", "find_clinical_trials"]
expected_subtasks: 4
notes: Comprehensive lung nodule workup.
```

### IM8: Serial Imaging + Documentation
```yaml
id: IM8
prompt: "Follow-up CXR for patient Davis. Compare to baseline, document findings, and check if they're still on the antibiotic that was prescribed."
has_image: true
image_type: xray
expected_complexity: complex
expected_tools: ["analyze_medical_image", "update_patient_record", "get_patient_record"]
expected_subtasks: 3
notes: Longitudinal tracking with documentation.
```

---

## Category 6: Edge Cases - Clarification Needed (6 cases)

### EC1: Missing Patient ID
```yaml
id: EC1
prompt: "Check the patient's creatinine levels from yesterday."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_reason: "Missing patient identifier"
notes: Should trigger clarification - which patient?
```

### EC2: Vague Drug Query
```yaml
id: EC2
prompt: "Is there an interaction I should worry about?"
has_image: false
image_type: null
expected_complexity: complex
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_reason: "Missing drug names"
notes: Should trigger clarification - which medications?
```

### EC3: Ambiguous Statin
```yaml
id: EC3
prompt: "Check interactions with the statin my patient is on."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_reason: "Missing specific statin name"
notes: Should clarify which specific statin.
```

### EC4: Image Without Context
```yaml
id: EC4
prompt: "What do you see?"
has_image: true
image_type: xray
expected_complexity: complex
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
notes: Minimal context but image present - analyze and provide findings.
```

### EC5: Incomplete Update Request
```yaml
id: EC5
prompt: "Update the patient's medications."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_reason: "Missing patient ID and specific medication changes"
notes: Need both patient and what to update.
```

### EC6: Non-specific Trial Search
```yaml
id: EC6
prompt: "Find some clinical trials for my patient."
has_image: false
image_type: null
expected_complexity: complex
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_reason: "Missing condition/disease for trial search"
notes: Need to know what condition to search trials for.
```

---

## Test Summary Statistics

| Category | Count | Direct | Complex | Has Image |
|----------|-------|--------|---------|-----------|
| Direct/Simple | 10 | 10 | 0 | 0 |
| Single Tool | 12 | 0 | 12 | 0 |
| Multi-Tool | 10 | 0 | 10 | 0 |
| Image - Single Tool | 8 | 0 | 8 | 8 |
| Image + Multi-Tool | 8 | 0 | 8 | 8 |
| Edge Cases | 6 | 0 | 6 | 1 |
| **Total** | **54** | **10** | **44** | **17** |

### Tool Coverage

| Tool | # Test Cases Using It |
|------|----------------------|
| `analyze_medical_image` | 16 |
| `search_medical_literature` | 14 |
| `check_drug_safety` | 8 |
| `check_drug_interactions` | 9 |
| `get_patient_record` | 10 |
| `update_patient_record` | 5 |
| `find_clinical_trials` | 6 |

### Subtask Distribution

| Subtask Count | # Test Cases |
|---------------|-------------|
| 0 (direct or needs clarification) | 16 |
| 1 subtask | 20 |
| 2 subtasks | 12 |
| 3 subtasks | 5 |
| 4 subtasks | 1 |
