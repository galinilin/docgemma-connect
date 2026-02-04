# DocGemma Connect - Comprehensive Test Cases v2

**Total Cases:** 120 (12 categories × 10 cases each)  
**Conversation Type:** Single-turn only  
**Target Users:** Medical experts (doctors, nurses, specialists)

---

## Test Case Schema

```yaml
id: string                    # Unique identifier (CATEGORY-NUMBER)
prompt: string                # User's input text
has_image: boolean            # Whether an image is attached
image_type: string | null     # xray, ct, mri, pathology, dermatology, ecg, fundoscopy
expected_complexity: string   # direct | complex
expected_thinking: boolean    # Whether thinking mode should activate
expected_tools: list[string]  # Tools that should be called
expected_subtasks: int        # Number of subtasks if decomposed
simulate_tool_failure: string | null  # Which tool should fail (for failure tests)
requires_clarification: boolean       # Whether agent should ask for more info
clarification_type: string | null     # patient_id, drug_name, condition, context, etc.
notes: string                 # Additional context for the test
```

---

## Category 1: Simple Questions (No Tools, No Thinking)

Direct factual questions that can be answered from model knowledge. No tool calls, no extended reasoning needed.

### SQ-01: Basic Drug Mechanism
```yaml
id: SQ-01
prompt: "What's the mechanism of action of metformin?"
has_image: false
image_type: null
expected_complexity: direct
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Standard pharmacology knowledge, textbook answer.
```

### SQ-02: Anatomy Question
```yaml
id: SQ-02
prompt: "Which nerve innervates the diaphragm?"
has_image: false
image_type: null
expected_complexity: direct
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Basic anatomy fact - phrenic nerve (C3-C5).
```

### SQ-03: Lab Value Interpretation
```yaml
id: SQ-03
prompt: "What's the normal range for serum potassium?"
has_image: false
image_type: null
expected_complexity: direct
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Standard reference range question.
```

### SQ-04: Medical Abbreviation
```yaml
id: SQ-04
prompt: "What does BID mean in prescription writing?"
has_image: false
image_type: null
expected_complexity: direct
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Common medical abbreviation.
```

### SQ-05: Pathophysiology Basics
```yaml
id: SQ-05
prompt: "Explain the pathophysiology of type 1 diabetes in brief."
has_image: false
image_type: null
expected_complexity: direct
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Concise explanation of autoimmune beta cell destruction.
```

### SQ-06: Drug Classification
```yaml
id: SQ-06
prompt: "What class of drug is lisinopril?"
has_image: false
image_type: null
expected_complexity: direct
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: ACE inhibitor - straightforward classification.
```

### SQ-07: Vital Signs
```yaml
id: SQ-07
prompt: "What heart rate defines bradycardia in adults?"
has_image: false
image_type: null
expected_complexity: direct
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: <60 bpm - basic clinical definition.
```

### SQ-08: Procedure Definition
```yaml
id: SQ-08
prompt: "What is a lumbar puncture?"
has_image: false
image_type: null
expected_complexity: direct
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Standard procedure description.
```

### SQ-09: Symptom Definition
```yaml
id: SQ-09
prompt: "Define dyspnea."
has_image: false
image_type: null
expected_complexity: direct
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Medical term definition.
```

### SQ-10: Scoring System
```yaml
id: SQ-10
prompt: "What are the components of the Glasgow Coma Scale?"
has_image: false
image_type: null
expected_complexity: direct
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Eye, verbal, motor - well-known scale.
```

---

## Category 2: Complex Questions - Thinking Required, No Tools

Questions requiring clinical reasoning, differential diagnosis, or multi-step analysis but answerable from model knowledge.

### CT-01: Differential Diagnosis Reasoning
```yaml
id: CT-01
prompt: "A 45-year-old male presents with sudden-onset severe headache described as 'the worst headache of my life.' What's your differential and reasoning?"
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Classic subarachnoid hemorrhage presentation. Requires structured DDx thinking.
```

### CT-02: Treatment Decision Framework
```yaml
id: CT-02
prompt: "Walk me through how you'd approach anticoagulation decision-making in a patient with new atrial fibrillation."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Should discuss CHA2DS2-VASc, HAS-BLED, patient factors. Reasoning-heavy.
```

### CT-03: Physiology Integration
```yaml
id: CT-03
prompt: "Explain why loop diuretics can cause hypokalemia while potassium-sparing diuretics don't. Include the nephron physiology."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Requires integration of nephron segments, ion channels, aldosterone effects.
```

### CT-04: Drug Selection Reasoning
```yaml
id: CT-04
prompt: "For a diabetic patient with CKD stage 3 and heart failure, how would you approach glucose-lowering medication selection? Think through the considerations."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Multi-organ consideration: renal dosing, cardioprotection, contraindications.
```

### CT-05: Diagnostic Approach
```yaml
id: CT-05
prompt: "A patient has microcytic anemia. Walk me through your systematic approach to determining the cause."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Iron studies, thalassemia, chronic disease, sideroblastic - reasoning tree.
```

### CT-06: Risk Stratification
```yaml
id: CT-06
prompt: "How do you risk-stratify a patient presenting with chest pain in the ED? What's your thought process?"
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: HEART score, troponins, ECG findings, history - structured approach.
```

### CT-07: Acid-Base Analysis
```yaml
id: CT-07
prompt: "pH 7.28, pCO2 24, HCO3 12, Na 140, Cl 105. Analyze this ABG and explain your reasoning step by step."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Metabolic acidosis with respiratory compensation, calculate anion gap.
```

### CT-08: Contraindication Analysis
```yaml
id: CT-08
prompt: "A patient needs an MRI but has a pacemaker placed in 2018. Think through the safety considerations."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: MRI-conditional vs legacy devices, magnetic field strength, monitoring needs.
```

### CT-09: Syndrome Recognition
```yaml
id: CT-09
prompt: "Patient presents with hypertension, hypokalemia, and metabolic alkalosis. What syndrome does this suggest and why?"
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: Primary hyperaldosteronism pattern - Conn's syndrome. Requires pathophys reasoning.
```

### CT-10: Perioperative Assessment
```yaml
id: CT-10
prompt: "How would you assess cardiac risk for a 70-year-old diabetic patient scheduled for hip replacement? Walk through your approach."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: []
expected_subtasks: 0
requires_clarification: false
notes: RCRI, functional capacity, need for testing - guidelines-based reasoning.
```

---

## Category 3: Complex Questions - Thinking + Single Tool

Questions requiring reasoning followed by a single tool call to retrieve specific information.

### CTT-01: Drug Safety Verification
```yaml
id: CTT-01
prompt: "I'm considering starting a patient on dofetilide for AFib. They have borderline QTc. Think through the risks and pull up the FDA warnings."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["check_drug_safety"]
expected_subtasks: 1
requires_clarification: false
notes: Reasoning about QT prolongation + FDA boxed warning lookup.
```

### CTT-02: Evidence-Based Treatment
```yaml
id: CTT-02
prompt: "I have a statin-intolerant patient who needs LDL lowering. What's the evidence for PCSK9 inhibitors? Search the latest literature."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["search_medical_literature"]
expected_subtasks: 1
requires_clarification: false
notes: Clinical reasoning about alternatives + literature search.
```

### CTT-03: Drug Interaction Analysis
```yaml
id: CTT-03
prompt: "My patient on warfarin needs antibiotics for pneumonia. I'm thinking azithromycin. Analyze the interaction risk."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["check_drug_interactions"]
expected_subtasks: 1
requires_clarification: false
notes: Reasoning about warfarin interactions + specific interaction check.
```

### CTT-04: Trial Eligibility Reasoning
```yaml
id: CTT-04
prompt: "I have a patient with refractory DLBCL who's failed two lines of therapy. Are there any CAR-T or bispecific trials recruiting?"
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["find_clinical_trials"]
expected_subtasks: 1
requires_clarification: false
notes: Oncology reasoning about treatment sequence + trial search.
```

### CTT-05: Patient History Integration
```yaml
id: CTT-05
prompt: "Patient 7892 is back with worsening dyspnea. Pull their record - I need to see their last echo results and medication list to figure out if this is HF progression."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["get_patient_record"]
expected_subtasks: 1
requires_clarification: false
notes: Clinical reasoning + EHR lookup.
```

### CTT-06: Guideline Verification
```yaml
id: CTT-06
prompt: "I'm debating whether to start aspirin for primary prevention in a 55-year-old diabetic. What do current guidelines say? Search for the latest recommendations."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["search_medical_literature"]
expected_subtasks: 1
requires_clarification: false
notes: Risk-benefit reasoning + guideline lookup.
```

### CTT-07: Safety in Special Population
```yaml
id: CTT-07
prompt: "Pregnant patient in first trimester needs antiepileptic adjustment. Walk me through the teratogenicity concerns with valproate and check current FDA pregnancy data."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["check_drug_safety"]
expected_subtasks: 1
requires_clarification: false
notes: Teratogenicity reasoning + FDA safety check.
```

### CTT-08: Dosing in Renal Impairment
```yaml
id: CTT-08
prompt: "Need to dose vancomycin for a patient with AKI - creatinine went from 1.0 to 3.5 today. Find current dosing recommendations for this degree of renal dysfunction."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["search_medical_literature"]
expected_subtasks: 1
requires_clarification: false
notes: Pharmacokinetic reasoning + literature search for dosing.
```

### CTT-09: New Therapy Evaluation
```yaml
id: CTT-09
prompt: "A rep was just here talking about tirzepatide for my diabetic patients. Before I prescribe it, what's the real-world evidence? Search recent publications."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["search_medical_literature"]
expected_subtasks: 1
requires_clarification: false
notes: Critical appraisal mindset + literature search.
```

### CTT-10: Contraindication Lookup
```yaml
id: CTT-10
prompt: "Patient with history of angioedema on lisinopril years ago - can they safely take sacubitril/valsartan for HFrEF? Check the safety data."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["check_drug_safety"]
expected_subtasks: 1
requires_clarification: false
notes: ARNI vs ACEi angioedema risk reasoning + safety check.
```

---

## Category 4: Tool Failure Handling

Test cases where tools return errors. Agent should gracefully handle failure and ask user for clarification or suggest alternatives.

### TF-01: Drug Not Found
```yaml
id: TF-01
prompt: "Check the interactions for 'Glipizidee' with metformin."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: ["check_drug_interactions"]
expected_subtasks: 1
simulate_tool_failure: "check_drug_interactions"
failure_type: "drug_not_found"
failure_message: "Drug 'Glipizidee' not found in database. Did you mean 'Glipizide'?"
requires_clarification: true
clarification_type: "drug_name_correction"
notes: Misspelled drug name. Agent should suggest correction.
```

### TF-02: Patient Record Not Found
```yaml
id: TF-02
prompt: "Pull up records for patient ID 99999."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: ["get_patient_record"]
expected_subtasks: 1
simulate_tool_failure: "get_patient_record"
failure_type: "patient_not_found"
failure_message: "No patient found with ID 99999."
requires_clarification: true
clarification_type: "patient_id"
notes: Invalid patient ID. Agent should ask for correct ID.
```

### TF-03: Literature Search No Results
```yaml
id: TF-03
prompt: "Find studies on 'xylomethazine' for chronic sinusitis treatment."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: ["search_medical_literature"]
expected_subtasks: 1
simulate_tool_failure: "search_medical_literature"
failure_type: "no_results"
failure_message: "No publications found matching query."
requires_clarification: true
clarification_type: "search_refinement"
notes: Made-up drug name. Agent should note no results and ask for clarification.
```

### TF-04: Clinical Trial Search Empty
```yaml
id: TF-04
prompt: "Find recruiting trials for 'metacarpal fibrodysplasia' in Montana."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: ["find_clinical_trials"]
expected_subtasks: 1
simulate_tool_failure: "find_clinical_trials"
failure_type: "no_trials"
failure_message: "No recruiting trials found for specified condition and location."
requires_clarification: true
clarification_type: "search_broadening"
notes: Very rare/made-up condition + limited location. Suggest broadening search.
```

### TF-05: Drug Safety API Timeout
```yaml
id: TF-05
prompt: "Get the FDA warnings for atorvastatin."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: ["check_drug_safety"]
expected_subtasks: 1
simulate_tool_failure: "check_drug_safety"
failure_type: "timeout"
failure_message: "OpenFDA API request timed out. Please try again."
requires_clarification: false
notes: Transient failure. Agent should acknowledge and offer to retry or provide general info.
```

### TF-06: EHR System Unavailable
```yaml
id: TF-06
prompt: "Update patient 4521's record with new diagnosis of hypertension."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: ["update_patient_record"]
expected_subtasks: 1
simulate_tool_failure: "update_patient_record"
failure_type: "system_unavailable"
failure_message: "EHR system is currently unavailable for write operations."
requires_clarification: false
notes: System outage. Agent should acknowledge and suggest trying later.
```

### TF-07: Interaction Check Partial Failure
```yaml
id: TF-07
prompt: "Check interactions between warfarin, aspirin, and 'Cardizem CD 360mg extended release'."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: ["check_drug_interactions"]
expected_subtasks: 1
simulate_tool_failure: "check_drug_interactions"
failure_type: "partial_match"
failure_message: "Found warfarin, aspirin. Could not identify 'Cardizem CD 360mg extended release' - please use generic name."
requires_clarification: true
clarification_type: "drug_name_simplification"
notes: Brand name with dose causing issues. Ask for generic (diltiazem).
```

### TF-08: Rate Limited
```yaml
id: TF-08
prompt: "Search PubMed for recent meta-analyses on SGLT2 inhibitors in heart failure."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: ["search_medical_literature"]
expected_subtasks: 1
simulate_tool_failure: "search_medical_literature"
failure_type: "rate_limited"
failure_message: "API rate limit exceeded. Please wait before making another request."
requires_clarification: false
notes: Rate limiting. Agent should acknowledge and suggest waiting.
```

### TF-09: Invalid Query Format
```yaml
id: TF-09
prompt: "Find trials for cancer treatment (all types, any phase, anywhere in the world, no date restriction)."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: ["find_clinical_trials"]
expected_subtasks: 1
simulate_tool_failure: "find_clinical_trials"
failure_type: "query_too_broad"
failure_message: "Query too broad - please specify cancer type for meaningful results."
requires_clarification: true
clarification_type: "query_narrowing"
notes: Overly broad search. Ask for specific cancer type.
```

### TF-10: Authentication Error
```yaml
id: TF-10
prompt: "Pull the complete medication history for patient 1234."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: ["get_patient_record"]
expected_subtasks: 1
simulate_tool_failure: "get_patient_record"
failure_type: "auth_error"
failure_message: "Session expired. Please re-authenticate to access patient records."
requires_clarification: false
notes: Auth failure. Agent should inform user of system issue.
```

---

## Category 5: Missing Information - Clarification Required

Queries lacking essential information. Agent should identify what's missing and ask specifically.

### MI-01: Missing Patient Identifier
```yaml
id: MI-01
prompt: "What were the patient's last potassium levels?"
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "patient_id"
expected_clarification: "Which patient are you asking about? Please provide the patient ID or name."
notes: No patient context. Must ask for identifier.
```

### MI-02: Missing Drug Name
```yaml
id: MI-02
prompt: "Check if there are any interactions with the blood pressure medication."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "drug_name"
expected_clarification: "Which blood pressure medication specifically? There are several classes - ACE inhibitors, ARBs, beta-blockers, calcium channel blockers, diuretics."
notes: Vague drug reference. Need specific medication name.
```

### MI-03: Missing Condition for Trial Search
```yaml
id: MI-03
prompt: "Find clinical trials for my patient."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "condition"
expected_clarification: "What condition or disease should I search clinical trials for?"
notes: No condition specified for trial search.
```

### MI-04: Ambiguous Drug Reference
```yaml
id: MI-04
prompt: "Is the statin safe to continue?"
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "drug_name"
expected_clarification: "Which statin is the patient taking? Different statins have different safety profiles and interactions."
notes: Statin is a class, not specific drug. Need exact medication.
```

### MI-05: Missing Second Drug for Interaction
```yaml
id: MI-05
prompt: "Check warfarin interactions."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "drug_name"
expected_clarification: "What medication are you considering adding to warfarin? I'll check the interaction."
notes: Interaction check needs at least two drugs.
```

### MI-06: Missing Clinical Context
```yaml
id: MI-06
prompt: "Should I increase the dose?"
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "context"
expected_clarification: "I need more context - which medication, for which patient, and what's the current clinical situation?"
notes: Completely decontextualized question.
```

### MI-07: Missing Update Details
```yaml
id: MI-07
prompt: "Update the patient's chart with the new information."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "update_details"
expected_clarification: "Please specify: 1) Which patient (ID or name), and 2) What information should I add to their chart?"
notes: Missing both patient and what to update.
```

### MI-08: Vague Literature Request
```yaml
id: MI-08
prompt: "Find me some recent papers."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "topic"
expected_clarification: "What topic or clinical question would you like me to search the literature for?"
notes: No topic specified for literature search.
```

### MI-09: Incomplete Dosing Question
```yaml
id: MI-09
prompt: "What's the correct dose for this patient?"
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "drug_and_patient"
expected_clarification: "Which medication are you dosing, and can you provide the patient ID or relevant clinical details (weight, renal function)?"
notes: Missing drug and patient context.
```

### MI-10: Ambiguous Allergy Check
```yaml
id: MI-10
prompt: "Is it safe to give given the allergy?"
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "drug_and_allergy"
expected_clarification: "Please specify: 1) What medication are you considering, and 2) What is the patient allergic to?"
notes: Missing both the proposed drug and the allergen.
```

---

## Category 6: Multi-Tool Complex Tasks (2-3 Subtasks)

Complex clinical scenarios requiring multiple tool calls in sequence.

### MT-01: Medication Reconciliation + Interaction Check
```yaml
id: MT-01
prompt: "Patient 2847 is being started on Paxlovid for COVID. Pull their current med list and check for interactions."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["get_patient_record", "check_drug_interactions"]
expected_subtasks: 2
requires_clarification: false
notes: Sequential - must get meds first, then check Paxlovid interactions with each.
```

### MT-02: Safety + Interaction + Literature
```yaml
id: MT-02
prompt: "Considering amiodarone for a patient already on metoprolol and warfarin. Check the safety warnings, drug interactions, and find recent monitoring guidelines."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["check_drug_safety", "check_drug_interactions", "search_medical_literature"]
expected_subtasks: 3
requires_clarification: false
notes: Comprehensive workup for high-risk antiarrhythmic initiation.
```

### MT-03: Record Review + Trial Search
```yaml
id: MT-03
prompt: "Patient 5521 has progressed on second-line therapy for metastatic colorectal cancer. Review their treatment history and find any relevant immunotherapy trials."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["get_patient_record", "find_clinical_trials"]
expected_subtasks: 2
requires_clarification: false
notes: Need treatment history to inform trial eligibility search.
```

### MT-04: Drug Evaluation Workflow
```yaml
id: MT-04
prompt: "New patient is a 65-year-old on both clopidogrel and omeprazole. Check if there's an interaction, and if so, search for alternative PPI options."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["check_drug_interactions", "search_medical_literature"]
expected_subtasks: 2
requires_clarification: false
notes: Known interaction - should find literature on alternative PPIs (pantoprazole).
```

### MT-05: Comprehensive New Drug Addition
```yaml
id: MT-05
prompt: "I want to start patient 3391 on apixaban. Check their current meds for interactions and look up the FDA safety info for this drug."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["get_patient_record", "check_drug_interactions", "check_drug_safety"]
expected_subtasks: 3
requires_clarification: false
notes: Full due diligence before anticoagulation initiation.
```

### MT-06: Record Update + Verification
```yaml
id: MT-06
prompt: "Add the new diagnosis of atrial fibrillation to patient 4420's record, then pull their updated problem list to confirm it was added."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: false
expected_tools: ["update_patient_record", "get_patient_record"]
expected_subtasks: 2
requires_clarification: false
notes: Write then read verification pattern.
```

### MT-07: Literature + Guidelines + Safety
```yaml
id: MT-07
prompt: "For refractory hypertension, I'm considering adding spironolactone. Find current evidence for this approach, check the safety profile, and any interactions with ACE inhibitors."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["search_medical_literature", "check_drug_safety", "check_drug_interactions"]
expected_subtasks: 3
requires_clarification: false
notes: Evidence-based prescribing workflow.
```

### MT-08: Patient Lookup + Multiple Interactions
```yaml
id: MT-08
prompt: "Patient 6612 needs to start rifampin for latent TB. They're on multiple chronic meds. Pull their list and check rifampin interactions - I'm especially worried about their anticoagulation and HIV meds."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["get_patient_record", "check_drug_interactions"]
expected_subtasks: 2
requires_clarification: false
notes: Rifampin is a CYP inducer with many interactions. Complex interaction check.
```

### MT-09: Allergy Documentation + Safety Check
```yaml
id: MT-09
prompt: "Patient 7788 reported a new sulfa allergy - anaphylaxis to Bactrim last week. Document this allergy and then check if their current furosemide is safe to continue."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["update_patient_record", "check_drug_safety"]
expected_subtasks: 2
requires_clarification: false
notes: Document allergy, then evaluate cross-reactivity (sulfa antibiotic vs sulfonamide diuretic).
```

### MT-10: Guideline Search + Trial Matching
```yaml
id: MT-10
prompt: "My patient with HER2+ breast cancer has completed standard therapy but has residual disease. Find current guidelines on extended adjuvant therapy and any relevant trials for this scenario."
has_image: false
image_type: null
expected_complexity: complex
expected_thinking: true
expected_tools: ["search_medical_literature", "find_clinical_trials"]
expected_subtasks: 2
requires_clarification: false
notes: Guidelines for extended neratinib/T-DM1 + trial search for residual disease.
```

---

## Category 7: Simple Questions + Image

Direct questions with image that can be answered with image analysis and model knowledge.

### SQI-01: Basic CXR Orientation
```yaml
id: SQI-01
prompt: "Is this a PA or AP chest X-ray?"
has_image: true
image_type: xray
expected_complexity: direct
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Simple orientation question - check scapulae position, heart size.
```

### SQI-02: Image Quality Check
```yaml
id: SQI-02
prompt: "Is this CT image of adequate quality for interpretation?"
has_image: true
image_type: ct
expected_complexity: direct
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Quality assessment - motion artifact, contrast timing, etc.
```

### SQI-03: Anatomical Identification
```yaml
id: SQI-03
prompt: "Which lobe of the lung is this nodule in?"
has_image: true
image_type: ct
expected_complexity: direct
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Basic anatomical localization.
```

### SQI-04: Counting Structures
```yaml
id: SQI-04
prompt: "How many rib fractures can you identify on this chest X-ray?"
has_image: true
image_type: xray
expected_complexity: direct
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Counting task with straightforward answer.
```

### SQI-05: Binary Finding
```yaml
id: SQI-05
prompt: "Is there a pleural effusion present?"
has_image: true
image_type: xray
expected_complexity: direct
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Yes/no finding with brief explanation.
```

### SQI-06: Dermoscopy Pattern
```yaml
id: SQI-06
prompt: "What dermoscopic pattern does this lesion show?"
has_image: true
image_type: dermatology
expected_complexity: direct
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Pattern recognition - reticular, globular, homogeneous, etc.
```

### SQI-07: ECG Rhythm
```yaml
id: SQI-07
prompt: "What's the underlying rhythm on this ECG?"
has_image: true
image_type: ecg
expected_complexity: direct
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Basic rhythm identification.
```

### SQI-08: Fracture Present
```yaml
id: SQI-08
prompt: "Is there a fracture visible on this wrist X-ray?"
has_image: true
image_type: xray
expected_complexity: direct
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Binary fracture identification.
```

### SQI-09: Pathology Stain
```yaml
id: SQI-09
prompt: "What stain was used on this pathology slide?"
has_image: true
image_type: pathology
expected_complexity: direct
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: H&E, immunostain identification.
```

### SQI-10: Device Identification
```yaml
id: SQI-10
prompt: "What type of cardiac device is visible on this chest X-ray?"
has_image: true
image_type: xray
expected_complexity: direct
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Pacemaker vs ICD vs CRT identification.
```

---

## Category 8: Complex Thinking + Image (No Other Tools)

Image analysis requiring clinical reasoning but no additional tool calls.

### CTI-01: CXR Differential
```yaml
id: CTI-01
prompt: "63-year-old smoker with chronic cough. Analyze this CXR and provide your differential for the findings."
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Image analysis + DDx reasoning based on clinical context.
```

### CTI-02: CT Abdomen Interpretation
```yaml
id: CTI-02
prompt: "Patient with RLQ pain, fever, elevated WBC. Interpret this CT and explain your reasoning for or against appendicitis."
has_image: true
image_type: ct
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: CT interpretation with clinical correlation.
```

### CTI-03: MRI Brain Analysis
```yaml
id: CTI-03
prompt: "New onset seizures in a 45-year-old. Analyze this brain MRI and discuss possible etiologies based on the imaging pattern."
has_image: true
image_type: mri
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Neuroimaging pattern recognition + differential reasoning.
```

### CTI-04: Pathology Grading
```yaml
id: CTI-04
prompt: "Prostate biopsy specimen. Analyze this H&E slide and provide Gleason grading with your reasoning."
has_image: true
image_type: pathology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Histopathology interpretation with grading system application.
```

### CTI-05: Skin Lesion Assessment
```yaml
id: CTI-05
prompt: "This pigmented lesion appeared 6 months ago and has been changing. Apply the ABCDE criteria and assess melanoma risk."
has_image: true
image_type: dermatology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Structured dermoscopy assessment with clinical reasoning.
```

### CTI-06: ECG Interpretation
```yaml
id: CTI-06
prompt: "Patient with chest pain and diaphoresis. Analyze this ECG systematically and identify any STEMI criteria."
has_image: true
image_type: ecg
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Systematic ECG analysis with clinical urgency assessment.
```

### CTI-07: Fundoscopy Analysis
```yaml
id: CTI-07
prompt: "Diabetic patient with new visual complaints. Analyze this fundoscopic image and stage the retinopathy if present."
has_image: true
image_type: fundoscopy
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Diabetic retinopathy staging with reasoning.
```

### CTI-08: Comparison Imaging
```yaml
id: CTI-08
prompt: "Follow-up CXR for patient with known lung nodule. Compare to prior and assess for interval change. Prior was 8mm, what about now?"
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Longitudinal comparison with growth assessment.
```

### CTI-09: Trauma Series
```yaml
id: CTI-09
prompt: "MVA patient, C-spine cleared clinically. Analyze this chest X-ray for traumatic injuries - specifically looking for pneumothorax, hemothorax, rib fractures."
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Systematic trauma imaging review.
```

### CTI-10: Post-Procedure Assessment
```yaml
id: CTI-10
prompt: "Post central line placement CXR. Verify line position and check for complications."
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: false
notes: Line tip position + pneumothorax assessment.
```

---

## Category 9: Image + Thinking + Single Tool

Image analysis combined with clinical reasoning and one additional tool call.

### ITT-01: CXR + Drug Safety
```yaml
id: ITT-01
prompt: "Patient on chronic amiodarone therapy. Analyze this CXR for pulmonary toxicity and pull up the monitoring guidelines."
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "check_drug_safety"]
expected_subtasks: 2
requires_clarification: false
notes: Drug-induced lung disease recognition + safety lookup.
```

### ITT-02: Derm + Literature
```yaml
id: ITT-02
prompt: "This looks like a basal cell carcinoma. Analyze the lesion and find current treatment guidelines for this size and location (nasal ala)."
has_image: true
image_type: dermatology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "search_medical_literature"]
expected_subtasks: 2
requires_clarification: false
notes: Skin cancer identification + treatment guideline lookup.
```

### ITT-03: Pathology + Trials
```yaml
id: ITT-03
prompt: "This breast biopsy looks like triple-negative invasive ductal carcinoma. Confirm the findings and search for neoadjuvant immunotherapy trials."
has_image: true
image_type: pathology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "find_clinical_trials"]
expected_subtasks: 2
requires_clarification: false
notes: Pathology interpretation + trial search for specific subtype.
```

### ITT-04: ECG + Patient Record
```yaml
id: ITT-04
prompt: "Analyze this ECG for patient 8891. I need to compare to their baseline - pull their prior ECG documentation."
has_image: true
image_type: ecg
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "get_patient_record"]
expected_subtasks: 2
requires_clarification: false
notes: ECG interpretation + prior record comparison.
```

### ITT-05: CT + Literature Search
```yaml
id: ITT-05
prompt: "This CT shows a 6mm pulmonary nodule. Analyze it and find the current Fleischner Society guidelines for follow-up."
has_image: true
image_type: ct
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "search_medical_literature"]
expected_subtasks: 2
requires_clarification: false
notes: Nodule characterization + management guideline lookup.
```

### ITT-06: Fundoscopy + Drug Safety
```yaml
id: ITT-06
prompt: "Patient on hydroxychloroquine for 7 years. Analyze this OCT/fundoscopy for toxicity and check the FDA warnings for long-term use."
has_image: true
image_type: fundoscopy
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "check_drug_safety"]
expected_subtasks: 2
requires_clarification: false
notes: Drug-induced maculopathy screening + safety profile.
```

### ITT-07: MRI + Clinical Trials
```yaml
id: ITT-07
prompt: "This brain MRI shows what appears to be a GBM. Analyze the imaging characteristics and find recruiting trials for newly diagnosed glioblastoma."
has_image: true
image_type: mri
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "find_clinical_trials"]
expected_subtasks: 2
requires_clarification: false
notes: Brain tumor imaging + trial search for specific diagnosis.
```

### ITT-08: CXR + Record Update
```yaml
id: ITT-08
prompt: "Interpret this CXR for patient 2234 and document your findings in their chart."
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "update_patient_record"]
expected_subtasks: 2
requires_clarification: false
notes: Image interpretation + EHR documentation.
```

### ITT-09: Dermoscopy + Patient History
```yaml
id: ITT-09
prompt: "New concerning mole on patient 5567. Analyze this dermoscopy image and pull their history - any prior skin cancers?"
has_image: true
image_type: dermatology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "get_patient_record"]
expected_subtasks: 2
requires_clarification: false
notes: Lesion analysis + risk factor assessment from history.
```

### ITT-10: Pathology + Literature
```yaml
id: ITT-10
prompt: "Liver biopsy from a patient with suspected autoimmune hepatitis. Analyze the histology and search for current diagnostic criteria and treatment protocols."
has_image: true
image_type: pathology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "search_medical_literature"]
expected_subtasks: 2
requires_clarification: false
notes: Histopathology interpretation + guideline lookup.
```

---

## Category 10: Image + Missing Information

Image provided but missing critical context. Agent should request clarification.

### IMI-01: No Clinical Context
```yaml
id: IMI-01
prompt: "What do you think?"
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: true
clarification_type: "clinical_context"
expected_clarification: "I can analyze this chest X-ray, but it would help to know: What's the clinical question? Any symptoms or relevant history?"
notes: Image present but no clinical question or context.
```

### IMI-02: Missing Comparison Request
```yaml
id: IMI-02
prompt: "Has the pneumonia improved?"
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "prior_imaging"
expected_clarification: "I can only see the current X-ray. To assess improvement, I'd need the prior study for comparison or a description of previous findings."
notes: Comparison requested but only one image provided.
```

### IMI-03: Unknown Patient for Record Update
```yaml
id: IMI-03
prompt: "Add these imaging findings to the chart."
has_image: true
image_type: ct
expected_complexity: complex
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: true
clarification_type: "patient_id"
expected_clarification: "I can analyze this CT, but which patient's chart should I update? Please provide the patient ID."
notes: Image can be analyzed but patient ID needed for documentation.
```

### IMI-04: Ambiguous Body Part
```yaml
id: IMI-04
prompt: "Is this normal?"
has_image: true
image_type: mri
expected_complexity: complex
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: true
clarification_type: "clinical_context"
expected_clarification: "I can see this is an MRI, but what specific finding are you concerned about? Any clinical symptoms guiding the question?"
notes: Very vague question even with image present.
```

### IMI-05: Missing Drug for Toxicity Check
```yaml
id: IMI-05
prompt: "Could the medication be causing this?"
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "drug_name"
expected_clarification: "Which medication are you concerned about? I can analyze the imaging and then check for known drug-induced effects."
notes: Drug-induced pathology question but drug not specified.
```

### IMI-06: Trial Search Without Confirmed Diagnosis
```yaml
id: IMI-06
prompt: "Find trials for whatever this turns out to be."
has_image: true
image_type: pathology
expected_complexity: complex
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: true
clarification_type: "confirmation_needed"
expected_clarification: "I'll analyze this pathology specimen. Once we confirm the diagnosis, I can search for relevant trials. Do you want me to proceed with the interpretation first?"
notes: Can analyze but trial search needs confirmed diagnosis.
```

### IMI-07: Missing Location for Lesion
```yaml
id: IMI-07
prompt: "Should I biopsy this?"
has_image: true
image_type: dermatology
expected_complexity: complex
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: true
clarification_type: "clinical_context"
expected_clarification: "I can analyze this skin lesion. Where on the body is it located? This affects both the differential diagnosis and biopsy approach."
notes: Anatomic location important for skin lesion assessment.
```

### IMI-08: Missing Prior for Size Comparison
```yaml
id: IMI-08
prompt: "Did the nodule grow?"
has_image: true
image_type: ct
expected_complexity: complex
expected_thinking: false
expected_tools: []
expected_subtasks: 0
requires_clarification: true
clarification_type: "prior_imaging"
expected_clarification: "I can measure the nodule on this current CT, but I need the prior imaging or the previous measurements to assess growth."
notes: Growth assessment requires comparison data.
```

### IMI-09: Missing Patient for History Correlation
```yaml
id: IMI-09
prompt: "Does this fit with their history?"
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: true
clarification_type: "patient_id"
expected_clarification: "I can analyze this X-ray. Which patient is this for? I'll pull their history to correlate the findings."
notes: History correlation requested but patient not identified.
```

### IMI-10: Incomplete Follow-up Request
```yaml
id: IMI-10
prompt: "What's the follow-up plan?"
has_image: true
image_type: ct
expected_complexity: complex
expected_thinking: false
expected_tools: ["analyze_medical_image"]
expected_subtasks: 1
requires_clarification: true
clarification_type: "clinical_context"
expected_clarification: "I'll interpret this CT. To recommend a follow-up plan, I need to know: What was the clinical indication? Any prior imaging? Patient's overall clinical situation?"
notes: Management planning needs clinical context beyond just image.
```

---

## Category 11: Image + Multi-Tool Complex (2-3 Tools)

Comprehensive image-based workflows requiring multiple tool calls.

### IMT-01: CXR + Record + Literature
```yaml
id: IMT-01
prompt: "CXR for patient 4432 shows a suspicious mass. Pull their smoking history and find current lung cancer screening and workup guidelines."
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "get_patient_record", "search_medical_literature"]
expected_subtasks: 3
requires_clarification: false
notes: Full lung mass workup - imaging + risk factors + guidelines.
```

### IMT-02: Pathology + Record + Trials
```yaml
id: IMT-02
prompt: "Breast biopsy for patient 6678. Analyze for receptor status, pull their staging workup results, and find trials for their specific subtype."
has_image: true
image_type: pathology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "get_patient_record", "find_clinical_trials"]
expected_subtasks: 3
requires_clarification: false
notes: Comprehensive breast cancer workup pathway.
```

### IMT-03: ECG + Safety + Interactions
```yaml
id: IMT-03
prompt: "Patient 7789 on multiple QT-prolonging drugs. Analyze this ECG for QTc, check the safety profiles, and interactions between their sotalol, ondansetron, and azithromycin."
has_image: true
image_type: ecg
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "check_drug_safety", "check_drug_interactions"]
expected_subtasks: 3
requires_clarification: false
notes: QT monitoring workflow with polypharmacy safety check.
```

### IMT-04: Derm + Record + Update
```yaml
id: IMT-04
prompt: "New melanocytic lesion on patient 3321. Analyze it, check their prior skin cancer history, and document this new finding in their chart."
has_image: true
image_type: dermatology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "get_patient_record", "update_patient_record"]
expected_subtasks: 3
requires_clarification: false
notes: Skin surveillance workflow with documentation.
```

### IMT-05: CT + Literature + Trials
```yaml
id: IMT-05
prompt: "New 2cm pancreatic mass on CT. Find current NCCN guidelines for workup and any recruiting trials for resectable pancreatic cancer."
has_image: true
image_type: ct
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "search_medical_literature", "find_clinical_trials"]
expected_subtasks: 3
requires_clarification: false
notes: Pancreatic mass workup - imaging + guidelines + trials.
```

### IMT-06: MRI + Record + Literature
```yaml
id: IMT-06
prompt: "Follow-up brain MRI for patient 8812 with known MS. Compare to their prior documented lesion count and find latest DMT efficacy data."
has_image: true
image_type: mri
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "get_patient_record", "search_medical_literature"]
expected_subtasks: 3
requires_clarification: false
notes: MS monitoring with treatment optimization.
```

### IMT-07: CXR + Drug Safety + Record
```yaml
id: IMT-07
prompt: "New infiltrate on CXR for patient 9923 who started methotrexate 3 months ago. Check for MTX pneumonitis, pull their immunosuppression history."
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "check_drug_safety", "get_patient_record"]
expected_subtasks: 3
requires_clarification: false
notes: Drug-induced lung disease workup.
```

### IMT-08: Path + Safety + Literature
```yaml
id: IMT-08
prompt: "Liver biopsy showing steatohepatitis. Check if their current statin could contribute, and find guidelines on NASH management with concurrent statin therapy."
has_image: true
image_type: pathology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "check_drug_safety", "search_medical_literature"]
expected_subtasks: 3
requires_clarification: false
notes: NAFLD/NASH assessment with medication consideration.
```

### IMT-09: Fundoscopy + Record + Update
```yaml
id: IMT-09
prompt: "Annual diabetic eye exam for patient 5543. Analyze the fundoscopy, compare to their last documented grade, and update their retinopathy staging in the chart."
has_image: true
image_type: fundoscopy
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "get_patient_record", "update_patient_record"]
expected_subtasks: 3
requires_clarification: false
notes: Diabetic retinopathy surveillance workflow.
```

### IMT-10: CT + Interactions + Record
```yaml
id: IMT-10
prompt: "New PE on CT for patient 4456. Before I anticoagulate, pull their med list and check for DOAC interactions. Also document the PE in their chart."
has_image: true
image_type: ct
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "get_patient_record", "check_drug_interactions", "update_patient_record"]
expected_subtasks: 4
requires_clarification: false
notes: PE diagnosis and anticoagulation workflow - most complex case.
```

---

## Category 12: Image + Tool Failure Scenarios

Image cases where subsequent tool calls fail.

### ITF-01: Image OK, Patient Not Found
```yaml
id: ITF-01
prompt: "Analyze this CXR for patient 99999 and update their record with findings."
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "update_patient_record"]
expected_subtasks: 2
simulate_tool_failure: "update_patient_record"
failure_type: "patient_not_found"
failure_message: "No patient found with ID 99999."
requires_clarification: true
clarification_type: "patient_id"
notes: Image analysis succeeds, but patient record update fails. Should provide imaging findings and ask for correct patient ID.
```

### ITF-02: Image OK, Literature Empty
```yaml
id: ITF-02
prompt: "Analyze this pathology slide - looks like a very rare sarcoma variant. Find any published case reports."
has_image: true
image_type: pathology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "search_medical_literature"]
expected_subtasks: 2
simulate_tool_failure: "search_medical_literature"
failure_type: "no_results"
failure_message: "No publications found matching query."
requires_clarification: false
notes: Image analyzed, literature search empty. Should provide imaging interpretation and note lack of literature.
```

### ITF-03: Image OK, Trial Search Empty
```yaml
id: ITF-03
prompt: "This bone marrow shows a rare leukemia subtype. Find any recruiting trials."
has_image: true
image_type: pathology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "find_clinical_trials"]
expected_subtasks: 2
simulate_tool_failure: "find_clinical_trials"
failure_type: "no_trials"
failure_message: "No recruiting trials found for specified condition."
requires_clarification: false
notes: Pathology interpreted but no trials available. Suggest alternatives.
```

### ITF-04: Image OK, Drug Check Fails
```yaml
id: ITF-04
prompt: "CXR shows new infiltrates. Patient is on 'Rheumatrex' - check if it could cause this."
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "check_drug_safety"]
expected_subtasks: 2
simulate_tool_failure: "check_drug_safety"
failure_type: "drug_not_found"
failure_message: "Drug 'Rheumatrex' not found. Did you mean 'methotrexate'?"
requires_clarification: true
clarification_type: "drug_name_correction"
notes: Image analyzed, drug lookup fails on brand name. Should provide imaging findings and suggest generic name.
```

### ITF-05: Image OK, Record System Down
```yaml
id: ITF-05
prompt: "Interpret this ECG and compare to patient 5555's prior baseline."
has_image: true
image_type: ecg
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "get_patient_record"]
expected_subtasks: 2
simulate_tool_failure: "get_patient_record"
failure_type: "system_unavailable"
failure_message: "EHR system is currently unavailable."
requires_clarification: false
notes: ECG interpreted but can't access prior. Should provide current interpretation and note system unavailable.
```

### ITF-06: Image OK, Interaction Check Timeout
```yaml
id: ITF-06
prompt: "CT shows new DVT. Check if patient's aspirin and fish oil will interact with the anticoagulant I want to start."
has_image: true
image_type: ct
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "check_drug_interactions"]
expected_subtasks: 2
simulate_tool_failure: "check_drug_interactions"
failure_type: "timeout"
failure_message: "Interaction database request timed out."
requires_clarification: false
notes: Imaging done, interaction check times out. Provide imaging findings, acknowledge timeout, offer retry.
```

### ITF-07: Image OK, Update Fails Auth
```yaml
id: ITF-07
prompt: "Document these chest CT findings in patient 3333's chart."
has_image: true
image_type: ct
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "update_patient_record"]
expected_subtasks: 2
simulate_tool_failure: "update_patient_record"
failure_type: "auth_error"
failure_message: "Session expired. Please re-authenticate."
requires_clarification: false
notes: Imaging interpreted, can't save to chart. Provide findings, note system issue.
```

### ITF-08: Image OK, Guideline Search Fails
```yaml
id: ITF-08
prompt: "6mm lung nodule on CT. Find Fleischner guidelines but the system might be slow today."
has_image: true
image_type: ct
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "search_medical_literature"]
expected_subtasks: 2
simulate_tool_failure: "search_medical_literature"
failure_type: "rate_limited"
failure_message: "API rate limit exceeded."
requires_clarification: false
notes: Nodule measured, guideline lookup rate limited. Provide measurements, suggest trying later.
```

### ITF-09: Image OK, Trial Query Too Broad
```yaml
id: ITF-09
prompt: "This looks like lung adenocarcinoma. Find any cancer trials."
has_image: true
image_type: pathology
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "find_clinical_trials"]
expected_subtasks: 2
simulate_tool_failure: "find_clinical_trials"
failure_type: "query_too_broad"
failure_message: "Query too broad - please specify cancer type and stage for meaningful results."
requires_clarification: true
clarification_type: "query_narrowing"
notes: Pathology shows adenocarcinoma, but "any cancer trials" too broad. Ask for stage, mutations.
```

### ITF-10: Partial Success on Multi-Tool
```yaml
id: ITF-10
prompt: "CXR for patient 7777. Document findings and check if their amiodarone could be causing this."
has_image: true
image_type: xray
expected_complexity: complex
expected_thinking: true
expected_tools: ["analyze_medical_image", "update_patient_record", "check_drug_safety"]
expected_subtasks: 3
simulate_tool_failure: "update_patient_record"
failure_type: "patient_not_found"
failure_message: "No patient found with ID 7777."
requires_clarification: true
clarification_type: "patient_id"
notes: Image analyzed, drug safety checked, but can't save to chart. Provide full analysis but note documentation failed.
```

---

## Summary Statistics

| Category | Count | Complexity | Thinking | Tools | Images | Clarification |
|----------|-------|------------|----------|-------|--------|---------------|
| 1. Simple Questions | 10 | direct | no | 0 | 0 | no |
| 2. Complex Thinking | 10 | complex | yes | 0 | 0 | no |
| 3. Thinking + Single Tool | 10 | complex | yes | 1 | 0 | no |
| 4. Tool Failure Handling | 10 | complex | varies | 1 | 0 | varies |
| 5. Missing Information | 10 | complex | no | 0 | 0 | yes |
| 6. Multi-Tool Complex | 10 | complex | yes | 2-3 | 0 | no |
| 7. Simple + Image | 10 | direct | no | 1 | 10 | no |
| 8. Complex Thinking + Image | 10 | complex | yes | 1 | 10 | no |
| 9. Image + Single Tool | 10 | complex | yes | 2 | 10 | no |
| 10. Image + Missing Info | 10 | complex | no | 0-1 | 10 | yes |
| 11. Image + Multi-Tool | 10 | complex | yes | 3-4 | 10 | no |
| 12. Image + Tool Failure | 10 | complex | yes | 2-3 | 10 | varies |
| **TOTAL** | **120** | | | | **60** | |

### Tool Usage Distribution

| Tool | # Direct Uses | # In Multi-Tool |
|------|---------------|-----------------|
| `analyze_medical_image` | 30 | 30 |
| `search_medical_literature` | 4 | 12 |
| `check_drug_safety` | 3 | 10 |
| `check_drug_interactions` | 3 | 8 |
| `get_patient_record` | 1 | 12 |
| `update_patient_record` | 0 | 8 |
| `find_clinical_trials` | 2 | 8 |

### Failure Type Coverage

| Failure Type | # Cases |
|--------------|---------|
| drug_not_found | 3 |
| patient_not_found | 4 |
| no_results | 3 |
| timeout | 2 |
| system_unavailable | 2 |
| rate_limited | 2 |
| query_too_broad | 2 |
| auth_error | 2 |
| partial_match | 1 |

### Clarification Type Coverage

| Clarification Type | # Cases |
|--------------------|---------|
| patient_id | 6 |
| drug_name | 5 |
| clinical_context | 5 |
| condition | 1 |
| topic | 1 |
| search_refinement | 3 |
| query_narrowing | 2 |
| prior_imaging | 2 |
| drug_name_correction | 2 |
| update_details | 1 |
| context | 1 |
| drug_and_patient | 1 |
| drug_and_allergy | 1 |
| confirmation_needed | 1 |
