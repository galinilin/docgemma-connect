#!/usr/bin/env python3
"""Generate FHIR R4-compliant JSON files for patients 1-3:
  1. Margaret Chen
  2. James Wilson
  3. Linda Martinez
"""

import json
import base64
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent / "data" / "fhir"

# Ensure all resource directories exist
RESOURCE_DIRS = [
    "Patient", "Condition", "MedicationRequest", "AllergyIntolerance",
    "Observation", "Encounter", "DocumentReference", "Media"
]
for d in RESOURCE_DIRS:
    (BASE_DIR / d).mkdir(parents=True, exist_ok=True)


def b64(text: str) -> str:
    """Base64 encode a string."""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def write_resource(resource_type: str, resource_id: str, data: dict):
    """Write a FHIR resource to the appropriate directory."""
    path = BASE_DIR / resource_type / f"{resource_id}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Created {resource_type}/{resource_id}.json")


# ============================================================================
# CLINICAL NOTES
# ============================================================================

# --- Margaret Chen (from spec exactly) ---
MARGARET_HPI = """68-year-old woman with a 10-year history of type 2 diabetes mellitus presents for routine follow-up. She reports good compliance with her current regimen of metformin 1000mg twice daily. She denies polyuria, polydipsia, or recent infections. She has noted some mild fatigue over the past month. No chest pain, shortness of breath, or lower extremity edema. Last ophthalmology exam 8 months ago was normal. Last podiatry visit 6 months ago showed no concerning findings.

Her most recent HbA1c was 7.8%, up from 7.2% six months ago. Of note, her renal function has declined with current GFR of 38 mL/min/1.73m2 (previously 52). She is also on lisinopril and spironolactone for hypertension and CHF prevention.

She asks about her diabetes medications given her declining kidney function."""

MARGARET_ROS = """Constitutional: Mild fatigue, no fever, no weight change
HEENT: No vision changes, no hearing loss
Cardiovascular: No chest pain, no palpitations, no orthopnea, no PND, no lower extremity edema
Respiratory: No cough, no dyspnea, no wheezing
GI: No nausea, no vomiting, no abdominal pain, no diarrhea, no constipation
GU: No dysuria, no frequency, no hematuria
Neurological: No headache, no numbness, no tingling in extremities
Endocrine: No heat/cold intolerance, no excessive thirst
Skin: No rashes, no wounds"""

MARGARET_PE = """Vitals: BP 142/88 mmHg, HR 76 bpm regular, RR 16, Temp 98.4\u00b0F, SpO2 98% RA, Weight 72 kg

General: Alert, oriented, no acute distress, well-nourished

HEENT: Normocephalic, atraumatic. PERRLA. Oropharynx clear. Moist mucous membranes.

Neck: Supple, no lymphadenopathy, no thyromegaly, no JVD

Cardiovascular: Regular rate and rhythm, normal S1/S2, no murmurs, rubs, or gallops. No peripheral edema.

Respiratory: Clear to auscultation bilaterally. No wheezes, rales, or rhonchi.

Abdomen: Soft, non-tender, non-distended. Normal bowel sounds. No hepatosplenomegaly.

Extremities: Warm, well-perfused. No cyanosis, clubbing, or edema. Dorsalis pedis pulses 2+ bilaterally.

Neurological: CN II-XII intact. Sensation intact to monofilament bilateral feet. Reflexes 2+ throughout.

Skin: No rashes, no ulcers, no concerning lesions."""

MARGARET_CLINICAL_NOTE = """Assessment and Plan:

68-year-old woman with type 2 diabetes mellitus, CKD stage 3b, hypertension, and hyperlipidemia presents for routine follow-up. HbA1c has risen to 7.8% from 7.2% six months ago despite reported compliance with metformin 1000mg BID. GFR has declined from 52 to 38 mL/min/1.73m2, now meeting criteria for CKD stage 3b. Potassium is 4.9 mEq/L on concurrent spironolactone and lisinopril.

1. Type 2 Diabetes: HbA1c trending up. With GFR of 38, metformin should be dose-reduced to 500mg BID per FDA labeling. Consider adding a GLP-1 receptor agonist (semaglutide) which offers renal protection. Refer to endocrinology for co-management.

2. CKD Stage 3b: Progressive decline in renal function. Continue ACE inhibitor for nephroprotection. Repeat BMP in 4 weeks to monitor potassium and creatinine. Nephrology referral placed.

3. Hypertension: BP 142/88, above target of 130/80 for diabetic nephropathy. Continue current regimen but may need adjustment at follow-up based on renal function trends.

4. Hyperlipidemia: Continue atorvastatin 40mg. Lipid panel due at next visit.

Follow-up in 4 weeks with repeat BMP and urinalysis. Patient educated on signs of hyperkalemia and when to seek emergent care."""

# --- James Wilson ---
JAMES_HPI = """58-year-old man presents to the emergency department with a three-day history of productive cough, fever, and progressive dyspnea. He reports initially developing a mild dry cough which rapidly became productive of yellow-green sputum. Fevers began the following day, measured at home up to 102.4\u00b0F. He endorses chills, night sweats, and pleuritic right-sided chest pain that worsens with deep inspiration. Over the past 24 hours, he has noted increasing shortness of breath at rest and decreased exercise tolerance, unable to walk to the bathroom without stopping to catch his breath.

His past medical history is significant for mechanical mitral valve replacement in 2019 for severe mitral regurgitation secondary to myxomatous degeneration, atrial fibrillation, and hypertension. He is on chronic anticoagulation with warfarin 5mg daily with a target INR of 2.5-3.5. He also takes metoprolol 50mg BID and lisinopril 10mg daily. He has a documented severe penicillin allergy with prior anaphylaxis in 1995, precluding use of beta-lactam antibiotics.

He denies recent travel, sick contacts, or prior hospitalizations for pneumonia. He is a non-smoker and denies alcohol or illicit drug use. He works as an accountant and has no occupational exposures."""

JAMES_ROS = """Constitutional: Fever to 102.6\u00b0F, chills, night sweats, fatigue, decreased appetite for 2 days
HEENT: No sore throat, no rhinorrhea, no ear pain, no sinus pressure
Cardiovascular: No chest tightness at rest, no palpitations beyond baseline atrial fibrillation, no lower extremity edema or swelling
Respiratory: Productive cough with yellow-green sputum, dyspnea at rest, pleuritic right-sided chest pain, no hemoptysis, no wheezing
GI: Decreased appetite, no nausea, no vomiting, no diarrhea, no abdominal pain
GU: No dysuria, no urgency, no hematuria
Musculoskeletal: Generalized myalgias, no joint swelling
Neurological: No headache, no confusion, no focal weakness, no dizziness
Skin: No rashes, no bruising"""

JAMES_PE = """Vitals: BP 128/82 mmHg, HR 102 bpm irregularly irregular, RR 22, Temp 102.6\u00b0F (39.2\u00b0C), SpO2 91% on room air, Weight 84 kg

General: Alert, oriented, appears acutely ill and diaphoretic. Mildly tachypneic at rest. Speaking in short sentences.

HEENT: Normocephalic, atraumatic. Conjunctivae clear. Oropharynx erythematous without exudates. Mucous membranes dry.

Neck: Supple, no lymphadenopathy, no JVD. No meningismus.

Cardiovascular: Irregularly irregular rhythm consistent with atrial fibrillation. Mechanical S1 click audible, consistent with prosthetic mitral valve. No S3 or S4. No rubs. No peripheral edema.

Respiratory: Tachypneic. Decreased breath sounds and dullness to percussion at right base. Bronchial breath sounds and egophony over right lower lobe. Scattered crackles right lower and middle fields. Left lung clear to auscultation.

Abdomen: Soft, non-tender, non-distended. Normal bowel sounds. No hepatosplenomegaly.

Extremities: Warm, well-perfused. No cyanosis or clubbing. No edema. No calf tenderness bilaterally.

Neurological: Alert and oriented x3. CN II-XII intact. No focal deficits. Gait not assessed due to dyspnea.

Skin: Diaphoretic. No petechiae, purpura, or rash. Well-healed median sternotomy scar."""

JAMES_CLINICAL_NOTE = """Assessment and Plan:

58-year-old man with mechanical mitral valve on warfarin, atrial fibrillation, and hypertension presenting with 3-day history of fever, productive cough, and dyspnea. Clinical examination and chest X-ray confirm right lower lobe community-acquired pneumonia. He is hypoxic with SpO2 91% on room air, febrile, and tachycardic. CURB-65 score is 1 (respiratory rate 22, borderline). INR is 2.4, within therapeutic range. WBC 14.2 with left shift and procalcitonin 1.8 support bacterial etiology.

1. Community-Acquired Pneumonia: Due to severe penicillin allergy (anaphylaxis), beta-lactams are contraindicated. Initiate levofloxacin 750mg IV daily as empiric coverage. Obtain blood cultures x2 and sputum culture prior to first dose. Supplemental oxygen via nasal cannula to target SpO2 >94%. IV fluids for hydration.

2. Anticoagulation Management: Continue warfarin. Monitor INR daily given potential for fluoroquinolone interaction with warfarin (may increase INR). Hold warfarin if INR exceeds 3.5. Mechanical valve requires uninterrupted anticoagulation; consult cardiology if bridging needed.

3. Atrial Fibrillation: Rate currently 102, likely driven by fever and infection. Continue metoprolol 50mg BID. Reassess rate control as infection resolves.

4. Disposition: Admit to medicine service for IV antibiotics, oxygen support, and anticoagulation monitoring. Reassess for step-down to oral therapy in 48-72 hours if clinically improving."""

# --- Linda Martinez ---
LINDA_HPI = """67-year-old retired nurse presents for oncology evaluation following recent diagnosis of pancreatic head adenocarcinoma. Her symptoms began approximately four months ago with insidious onset of vague epigastric pain that she initially attributed to gastritis. Over the subsequent weeks, she noticed progressive loss of appetite and unintentional weight loss totaling 8 kilograms. Three weeks ago, her family noted yellowing of her eyes and skin, prompting her to seek medical evaluation.

Initial workup by her primary care physician revealed elevated bilirubin and transaminases. CT abdomen with contrast demonstrated a 3.2 cm mass in the head of the pancreas with upstream bile duct dilation to 12mm and possible abutment of the superior mesenteric artery. CA 19-9 was markedly elevated at 842 U/mL. Endoscopic ultrasound with fine needle aspiration confirmed adenocarcinoma, moderately differentiated.

Her past medical history includes type 2 diabetes mellitus managed with metformin 500mg BID and hypertension controlled with amlodipine 5mg daily. She also takes omeprazole 20mg daily for GERD. She has no known drug allergies. She is a never-smoker, drinks alcohol socially, and has no family history of pancreatic or gastrointestinal malignancies. She retired from nursing five years ago and lives with her husband. She reports that her functional status remains good, though she has less energy than usual."""

LINDA_ROS = """Constitutional: Unintentional weight loss of 8 kg over 4 months, fatigue, decreased appetite, no fevers or night sweats
HEENT: Scleral icterus noted by family, no vision changes, no hearing loss, no oral lesions
Cardiovascular: No chest pain, no palpitations, no dyspnea on exertion, no lower extremity edema
Respiratory: No cough, no shortness of breath, no hemoptysis
GI: Epigastric pain (dull, constant, 4/10, radiating to back), decreased appetite, mild nausea without vomiting, clay-colored stools for past 2 weeks, dark urine, no hematemesis, no melena
GU: Dark urine as noted above, no dysuria, no hematuria, no frequency
Musculoskeletal: No back pain apart from epigastric radiation, no joint pain, no muscle weakness
Neurological: No headache, no confusion, no peripheral neuropathy symptoms
Skin: Generalized pruritus for past 2 weeks, jaundice noted, no new rashes or lesions
Psychiatric: Appropriate anxiety regarding new diagnosis, sleeping adequately, good family support"""

LINDA_PE = """Vitals: BP 138/78 mmHg, HR 88 bpm regular, RR 16, Temp 98.6\u00b0F, SpO2 97% RA, Weight 58 kg (baseline 66 kg)

General: Alert, oriented, appears thin but not cachectic. Jaundiced. No acute distress. Appropriate affect with understandable concern regarding diagnosis.

HEENT: Normocephalic, atraumatic. Scleral icterus present bilaterally. PERRLA. Oropharynx clear. Mucous membranes moist, icteric sublingual mucosa.

Neck: Supple, no lymphadenopathy, no thyromegaly, no JVD. No supraclavicular lymphadenopathy (Virchow node absent).

Cardiovascular: Regular rate and rhythm, normal S1/S2, no murmurs, rubs, or gallops. No peripheral edema.

Respiratory: Clear to auscultation bilaterally. No wheezes, rales, or rhonchi. Good air movement throughout.

Abdomen: Soft, mild tenderness to deep palpation in epigastrium. No rebound or guarding. Liver palpable 2 cm below right costal margin, smooth, mildly tender. Spleen not palpable. No ascites by examination. Positive Courvoisier sign - palpable, non-tender gallbladder in right upper quadrant. Normal bowel sounds.

Extremities: Warm, well-perfused. No cyanosis or clubbing. No edema. No evidence of DVT.

Neurological: Alert and oriented x3. CN II-XII intact. No asterixis. No focal deficits.

Skin: Generalized jaundice. Excoriations on arms and trunk consistent with pruritus. No spider angiomata. No palmar erythema. No ecchymoses."""

LINDA_CLINICAL_NOTE = """Assessment and Plan:

67-year-old woman with newly diagnosed pancreatic head adenocarcinoma presenting for oncology staging evaluation and treatment planning. CT demonstrates a 3.2 cm mass with bile duct dilation and SMA abutment, raising concern for borderline resectable disease. EUS-FNA confirms moderately differentiated adenocarcinoma. CA 19-9 markedly elevated at 842 U/mL. Patient is jaundiced with bilirubin 3.2, elevated transaminases consistent with biliary obstruction.

1. Pancreatic Adenocarcinoma Staging: SMA abutment on CT requires further characterization. Order pancreas protocol MRI for vascular mapping. Refer to hepatobiliary surgery for resectability assessment. Discuss case at multidisciplinary tumor board. Consider ERCP with biliary stent placement for symptomatic jaundice relief prior to any neoadjuvant therapy.

2. Biliary Obstruction: Bilirubin 3.2, clay-colored stools, pruritus consistent with extrahepatic obstruction from pancreatic head mass. ERCP with biliary stent to be scheduled within the week for symptom relief and to allow bilirubin normalization prior to potential chemotherapy.

3. Nutritional Status: 8 kg weight loss over 4 months, BMI trending down. Initiate pancreatic enzyme supplementation (Creon) to aid fat absorption. Nutrition consult for caloric optimization and dietary counseling.

4. Type 2 Diabetes: Continue metformin 500mg BID. Monitor glucose closely as pancreatic exocrine and endocrine function may be affected by tumor. Adjust regimen as needed.

5. Goals of Care: Patient is well-informed and demonstrates good understanding of her diagnosis. Discussed general prognosis and treatment options including potential for neoadjuvant FOLFIRINOX if borderline resectable. Patient wishes to pursue aggressive treatment. Will finalize plan after tumor board and surgical consultation.

Follow-up in 1 week with MRI results and tumor board recommendations."""


# ============================================================================
# PATIENT 1: MARGARET CHEN
# ============================================================================
def generate_margaret_chen():
    print("\n=== Patient 1: Margaret Chen ===")
    pid = "patient-margaret-chen"
    display = "Margaret Chen"

    # Patient
    write_resource("Patient", pid, {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "MC-2024-001"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Chen",
            "given": ["Margaret", "Li"]
        }],
        "gender": "female",
        "birthDate": "1958-03-14",
        "address": [{
            "use": "home",
            "line": ["123 Oak Street"],
            "city": "San Francisco",
            "state": "CA",
            "postalCode": "94102"
        }],
        "maritalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                "code": "M",
                "display": "Married"
            }]
        },
        "communication": [{
            "language": {
                "coding": [{
                    "system": "urn:ietf:bcp:47",
                    "code": "en",
                    "display": "English"
                }]
            },
            "preferred": True
        }]
    })

    # Conditions
    conditions = [
        ("condition-margaret-chen-diabetes", "44054006", "Type 2 diabetes mellitus", "Type 2 Diabetes Mellitus", "2016-05-01"),
        ("condition-margaret-chen-ckd", "731000119105", "Chronic kidney disease stage 3", "Chronic Kidney Disease Stage 3b", "2024-08-15"),
        ("condition-margaret-chen-hypertension", "38341003", "Hypertensive disorder", "Hypertension", "2014-03-20"),
        ("condition-margaret-chen-hyperlipidemia", "55822004", "Hyperlipidemia", "Hyperlipidemia", "2015-11-10"),
    ]
    for cid, code, code_display, text, onset in conditions:
        write_resource("Condition", cid, {
            "resourceType": "Condition",
            "id": cid,
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
            },
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
            },
            "verificationStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]
            },
            "category": [{
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item"}]
            }],
            "code": {
                "coding": [{"system": "http://snomed.info/sct", "code": code, "display": code_display}],
                "text": text
            },
            "subject": {"reference": f"Patient/{pid}", "display": display},
            "onsetDateTime": onset
        })

    # Medications
    meds = [
        ("medrx-margaret-chen-metformin", "861007", "Metformin 1000 MG Oral Tablet", "Metformin 1000mg",
         "Take 1 tablet by mouth twice daily with meals", 2, 1000, "mg", "2024-01-15"),
        ("medrx-margaret-chen-lisinopril", "314076", "Lisinopril 20 MG Oral Tablet", "Lisinopril 20mg",
         "Take 1 tablet by mouth once daily", 1, 20, "mg", "2014-06-01"),
        ("medrx-margaret-chen-spironolactone", "313096", "Spironolactone 25 MG Oral Tablet", "Spironolactone 25mg",
         "Take 1 tablet by mouth once daily", 1, 25, "mg", "2024-09-01"),
        ("medrx-margaret-chen-atorvastatin", "617312", "Atorvastatin 40 MG Oral Tablet", "Atorvastatin 40mg",
         "Take 1 tablet by mouth once daily at bedtime", 1, 40, "mg", "2015-12-01"),
    ]
    for mid, rxcode, rxdisplay, text, dosage_text, freq, dose_val, dose_unit, authored in meds:
        write_resource("MedicationRequest", mid, {
            "resourceType": "MedicationRequest",
            "id": mid,
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": rxcode, "display": rxdisplay}],
                "text": text
            },
            "subject": {"reference": f"Patient/{pid}", "display": display},
            "authoredOn": authored,
            "dosageInstruction": [{
                "text": dosage_text,
                "timing": {"repeat": {"frequency": freq, "period": 1, "periodUnit": "d"}},
                "route": {"coding": [{"system": "http://snomed.info/sct", "code": "26643006", "display": "Oral route"}]},
                "doseAndRate": [{"doseQuantity": {"value": dose_val, "unit": dose_unit}}]
            }]
        })

    # Allergy - Sulfa drugs
    write_resource("AllergyIntolerance", "allergy-margaret-chen-sulfa", {
        "resourceType": "AllergyIntolerance",
        "id": "allergy-margaret-chen-sulfa",
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]
        },
        "type": "allergy",
        "category": ["medication"],
        "criticality": "low",
        "code": {
            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "10831", "display": "Sulfamethoxazole"}],
            "text": "Sulfa drugs"
        },
        "patient": {"reference": f"Patient/{pid}", "display": display},
        "recordedDate": "2010-04-15",
        "reaction": [{
            "manifestation": [{
                "coding": [{"system": "http://snomed.info/sct", "code": "271807003", "display": "Skin rash"}],
                "text": "Rash"
            }],
            "severity": "mild"
        }]
    })

    # Vitals
    visit_date = "2026-02-01"
    vitals_time = f"{visit_date}T09:30:00Z"

    # BP
    write_resource("Observation", f"obs-margaret-chen-bp-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-margaret-chen-bp-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": vitals_time,
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": 142, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                "valueQuantity": {"value": 88, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            }
        ]
    })

    # HR
    write_resource("Observation", f"obs-margaret-chen-hr-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-margaret-chen-hr-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": vitals_time,
        "valueQuantity": {"value": 76, "unit": "beats/minute", "system": "http://unitsofmeasure.org", "code": "/min"}
    })

    # Temp
    write_resource("Observation", f"obs-margaret-chen-temp-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-margaret-chen-temp-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": vitals_time,
        "valueQuantity": {"value": 98.4, "unit": "degF", "system": "http://unitsofmeasure.org", "code": "[degF]"}
    })

    # Labs
    lab_time = f"{visit_date}T08:00:00Z"

    # GFR
    write_resource("Observation", f"obs-margaret-chen-gfr-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-margaret-chen-gfr-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "33914-3", "display": "Glomerular filtration rate/1.73 sq M.predicted"}], "text": "eGFR"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 38, "unit": "mL/min/1.73m2", "system": "http://unitsofmeasure.org"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "L", "display": "Low"}]}],
        "referenceRange": [{"low": {"value": 60, "unit": "mL/min/1.73m2"}, "high": {"value": 120, "unit": "mL/min/1.73m2"}}]
    })

    # HbA1c
    write_resource("Observation", f"obs-margaret-chen-hba1c-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-margaret-chen-hba1c-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood"}], "text": "HbA1c"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 7.8, "unit": "%", "system": "http://unitsofmeasure.org", "code": "%"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]}],
        "referenceRange": [{"low": {"value": 4.0, "unit": "%"}, "high": {"value": 5.6, "unit": "%"}, "text": "Normal: <5.7%, Pre-diabetes: 5.7-6.4%, Diabetes: >=6.5%"}]
    })

    # Potassium
    write_resource("Observation", f"obs-margaret-chen-potassium-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-margaret-chen-potassium-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "2823-3", "display": "Potassium [Moles/volume] in Serum or Plasma"}], "text": "Potassium"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 4.9, "unit": "mEq/L", "system": "http://unitsofmeasure.org", "code": "meq/L"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]}],
        "referenceRange": [{"low": {"value": 3.5, "unit": "mEq/L"}, "high": {"value": 5.0, "unit": "mEq/L"}}]
    })

    # Creatinine
    write_resource("Observation", f"obs-margaret-chen-creatinine-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-margaret-chen-creatinine-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma"}], "text": "Creatinine"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 1.6, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]}],
        "referenceRange": [{"low": {"value": 0.6, "unit": "mg/dL"}, "high": {"value": 1.2, "unit": "mg/dL"}}]
    })

    # Encounter
    write_resource("Encounter", f"encounter-margaret-chen-{visit_date}", {
        "resourceType": "Encounter",
        "id": f"encounter-margaret-chen-{visit_date}",
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB", "display": "ambulatory"},
        "type": [{"coding": [{"system": "http://snomed.info/sct", "code": "185349003", "display": "Encounter for check up"}]}],
        "subject": {"reference": f"Patient/{pid}"},
        "period": {"start": f"{visit_date}T09:00:00Z", "end": f"{visit_date}T09:45:00Z"},
        "reasonCode": [{
            "coding": [{"system": "http://snomed.info/sct", "code": "44054006", "display": "Diabetes mellitus type 2"}],
            "text": "Routine diabetes follow-up"
        }]
    })

    # DocumentReferences
    doc_author = [{"display": "Dr. Sarah Johnson, MD"}]
    docs = [
        ("doc-margaret-chen-hpi", "10164-2", "History of Present illness", MARGARET_HPI),
        ("doc-margaret-chen-ros", "10187-3", "Review of systems", MARGARET_ROS),
        ("doc-margaret-chen-physical-exam", "29545-1", "Physical findings", MARGARET_PE),
        ("doc-margaret-chen-clinical-note", "11506-3", "Progress note", MARGARET_CLINICAL_NOTE),
    ]
    for did, loinc, loinc_display, content_text in docs:
        write_resource("DocumentReference", did, {
            "resourceType": "DocumentReference",
            "id": did,
            "status": "current",
            "type": {"coding": [{"system": "http://loinc.org", "code": loinc, "display": loinc_display}]},
            "category": [{"coding": [{"system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category", "code": "clinical-note", "display": "Clinical Note"}]}],
            "subject": {"reference": f"Patient/{pid}"},
            "date": f"{visit_date}T09:30:00Z",
            "author": doc_author,
            "content": [{"attachment": {"contentType": "text/plain", "data": b64(content_text)}}]
        })


# ============================================================================
# PATIENT 2: JAMES WILSON
# ============================================================================
def generate_james_wilson():
    print("\n=== Patient 2: James Wilson ===")
    pid = "patient-james-wilson"
    display = "James Wilson"

    # Patient
    write_resource("Patient", pid, {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "JW-2024-002"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Wilson",
            "given": ["James", "Robert"]
        }],
        "gender": "male",
        "birthDate": "1968-07-22",
        "address": [{
            "use": "home",
            "line": ["456 Maple Avenue"],
            "city": "San Francisco",
            "state": "CA",
            "postalCode": "94110"
        }],
        "maritalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                "code": "M",
                "display": "Married"
            }]
        },
        "communication": [{
            "language": {
                "coding": [{
                    "system": "urn:ietf:bcp:47",
                    "code": "en",
                    "display": "English"
                }]
            },
            "preferred": True
        }]
    })

    # Conditions
    conditions = [
        ("condition-james-wilson-pneumonia", "233604007", "Community-acquired pneumonia", "Community-Acquired Pneumonia", "2026-02-07"),
        ("condition-james-wilson-mvr", "80891009", "Mitral valve replacement", "Mechanical Mitral Valve Replacement (2019)", "2019-04-15"),
        ("condition-james-wilson-afib", "49436004", "Atrial fibrillation", "Atrial Fibrillation", "2018-09-01"),
        ("condition-james-wilson-hypertension", "38341003", "Hypertensive disorder", "Hypertension", "2012-06-15"),
    ]
    for cid, code, code_display, text, onset in conditions:
        write_resource("Condition", cid, {
            "resourceType": "Condition",
            "id": cid,
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
            },
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
            },
            "verificationStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]
            },
            "category": [{
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item"}]
            }],
            "code": {
                "coding": [{"system": "http://snomed.info/sct", "code": code, "display": code_display}],
                "text": text
            },
            "subject": {"reference": f"Patient/{pid}", "display": display},
            "onsetDateTime": onset
        })

    # Medications
    meds = [
        ("medrx-james-wilson-warfarin", "855332", "Warfarin 5 MG Oral Tablet", "Warfarin 5mg",
         "Take 1 tablet by mouth once daily", 1, 5, "mg", "2019-05-01"),
        ("medrx-james-wilson-metoprolol", "866924", "Metoprolol Tartrate 50 MG Oral Tablet", "Metoprolol 50mg",
         "Take 1 tablet by mouth twice daily", 2, 50, "mg", "2018-10-01"),
        ("medrx-james-wilson-lisinopril", "314076", "Lisinopril 10 MG Oral Tablet", "Lisinopril 10mg",
         "Take 1 tablet by mouth once daily", 1, 10, "mg", "2012-07-01"),
    ]
    for mid, rxcode, rxdisplay, text, dosage_text, freq, dose_val, dose_unit, authored in meds:
        write_resource("MedicationRequest", mid, {
            "resourceType": "MedicationRequest",
            "id": mid,
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": rxcode, "display": rxdisplay}],
                "text": text
            },
            "subject": {"reference": f"Patient/{pid}", "display": display},
            "authoredOn": authored,
            "dosageInstruction": [{
                "text": dosage_text,
                "timing": {"repeat": {"frequency": freq, "period": 1, "periodUnit": "d"}},
                "route": {"coding": [{"system": "http://snomed.info/sct", "code": "26643006", "display": "Oral route"}]},
                "doseAndRate": [{"doseQuantity": {"value": dose_val, "unit": dose_unit}}]
            }]
        })

    # Allergy - Penicillin
    write_resource("AllergyIntolerance", "allergy-james-wilson-penicillin", {
        "resourceType": "AllergyIntolerance",
        "id": "allergy-james-wilson-penicillin",
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]
        },
        "type": "allergy",
        "category": ["medication"],
        "criticality": "high",
        "code": {
            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "70618", "display": "Penicillin"}],
            "text": "Penicillin"
        },
        "patient": {"reference": f"Patient/{pid}", "display": display},
        "recordedDate": "1995-06-15",
        "reaction": [{
            "manifestation": [{
                "coding": [{"system": "http://snomed.info/sct", "code": "39579001", "display": "Anaphylaxis"}],
                "text": "Anaphylaxis"
            }],
            "severity": "severe"
        }]
    })

    # Vitals
    visit_date = "2026-02-10"
    vitals_time = f"{visit_date}T14:30:00Z"

    # BP
    write_resource("Observation", f"obs-james-wilson-bp-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-james-wilson-bp-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": vitals_time,
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": 128, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                "valueQuantity": {"value": 82, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            }
        ]
    })

    # HR
    write_resource("Observation", f"obs-james-wilson-hr-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-james-wilson-hr-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": vitals_time,
        "valueQuantity": {"value": 102, "unit": "beats/minute", "system": "http://unitsofmeasure.org", "code": "/min"}
    })

    # Temp
    write_resource("Observation", f"obs-james-wilson-temp-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-james-wilson-temp-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": vitals_time,
        "valueQuantity": {"value": 102.6, "unit": "degF", "system": "http://unitsofmeasure.org", "code": "[degF]"}
    })

    # SpO2
    write_resource("Observation", f"obs-james-wilson-spo2-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-james-wilson-spo2-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "2708-6", "display": "Oxygen saturation in Arterial blood"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": vitals_time,
        "valueQuantity": {"value": 91, "unit": "%", "system": "http://unitsofmeasure.org", "code": "%"}
    })

    # RR
    write_resource("Observation", f"obs-james-wilson-rr-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-james-wilson-rr-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "9279-1", "display": "Respiratory rate"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": vitals_time,
        "valueQuantity": {"value": 22, "unit": "breaths/minute", "system": "http://unitsofmeasure.org", "code": "/min"}
    })

    # Labs
    lab_time = f"{visit_date}T14:00:00Z"

    # INR
    write_resource("Observation", f"obs-james-wilson-inr-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-james-wilson-inr-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "5902-2", "display": "Prothrombin time (PT) in Platelet poor plasma by Coagulation assay"}], "text": "INR"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 2.4, "unit": "INR", "system": "http://unitsofmeasure.org", "code": "{INR}"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]}],
        "referenceRange": [{"low": {"value": 2.5, "unit": "INR"}, "high": {"value": 3.5, "unit": "INR"}, "text": "Therapeutic range for mechanical mitral valve: 2.5-3.5"}]
    })

    # WBC
    write_resource("Observation", f"obs-james-wilson-wbc-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-james-wilson-wbc-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "6690-2", "display": "Leukocytes [#/volume] in Blood by Automated count"}], "text": "WBC"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 14.2, "unit": "10*3/uL", "system": "http://unitsofmeasure.org", "code": "10*3/uL"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]}],
        "referenceRange": [{"low": {"value": 4.5, "unit": "10*3/uL"}, "high": {"value": 11.0, "unit": "10*3/uL"}}]
    })

    # Procalcitonin
    write_resource("Observation", f"obs-james-wilson-procalcitonin-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-james-wilson-procalcitonin-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "33959-8", "display": "Procalcitonin [Mass/volume] in Serum or Plasma"}], "text": "Procalcitonin"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 1.8, "unit": "ng/mL", "system": "http://unitsofmeasure.org", "code": "ng/mL"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]}],
        "referenceRange": [{"low": {"value": 0.0, "unit": "ng/mL"}, "high": {"value": 0.1, "unit": "ng/mL"}, "text": "<0.1 ng/mL normal, >0.5 suggests bacterial infection"}]
    })

    # Encounter - EMER for ED visit
    write_resource("Encounter", f"encounter-james-wilson-{visit_date}", {
        "resourceType": "Encounter",
        "id": f"encounter-james-wilson-{visit_date}",
        "status": "in-progress",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "EMER", "display": "emergency"},
        "type": [{"coding": [{"system": "http://snomed.info/sct", "code": "50849002", "display": "Emergency room admission"}]}],
        "subject": {"reference": f"Patient/{pid}"},
        "period": {"start": f"{visit_date}T14:00:00Z"},
        "reasonCode": [{
            "coding": [{"system": "http://snomed.info/sct", "code": "233604007", "display": "Community-acquired pneumonia"}],
            "text": "Productive cough, fever, dyspnea x3 days"
        }]
    })

    # DocumentReferences
    doc_author = [{"display": "Dr. Michael Torres, MD"}]
    docs = [
        ("doc-james-wilson-hpi", "10164-2", "History of Present illness", JAMES_HPI),
        ("doc-james-wilson-ros", "10187-3", "Review of systems", JAMES_ROS),
        ("doc-james-wilson-physical-exam", "29545-1", "Physical findings", JAMES_PE),
        ("doc-james-wilson-clinical-note", "11506-3", "Progress note", JAMES_CLINICAL_NOTE),
    ]
    for did, loinc, loinc_display, content_text in docs:
        write_resource("DocumentReference", did, {
            "resourceType": "DocumentReference",
            "id": did,
            "status": "current",
            "type": {"coding": [{"system": "http://loinc.org", "code": loinc, "display": loinc_display}]},
            "category": [{"coding": [{"system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category", "code": "clinical-note", "display": "Clinical Note"}]}],
            "subject": {"reference": f"Patient/{pid}"},
            "date": f"{visit_date}T14:30:00Z",
            "author": doc_author,
            "content": [{"attachment": {"contentType": "text/plain", "data": b64(content_text)}}]
        })

    # Media - CXR
    write_resource("Media", "media-james-wilson-cxr", {
        "resourceType": "Media",
        "id": "media-james-wilson-cxr",
        "status": "completed",
        "type": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/media-type", "code": "image", "display": "Image"}]
        },
        "modality": {
            "coding": [{"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CR", "display": "Computed Radiography"}]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "createdDateTime": f"{visit_date}T14:30:00Z",
        "bodySite": {
            "coding": [{"system": "http://snomed.info/sct", "code": "51185008", "display": "Thoracic structure"}]
        },
        "content": {
            "contentType": "image/png",
            "url": "file://data/images/james-wilson-cxr.png",
            "title": "Chest X-ray PA view"
        },
        "note": [{
            "text": "Right lower lobe consolidation consistent with pneumonia. No pleural effusion. No pneumothorax."
        }]
    })


# ============================================================================
# PATIENT 3: LINDA MARTINEZ
# ============================================================================
def generate_linda_martinez():
    print("\n=== Patient 3: Linda Martinez ===")
    pid = "patient-linda-martinez"
    display = "Linda Martinez"

    # Patient
    write_resource("Patient", pid, {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "LM-2024-003"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Martinez",
            "given": ["Linda", "Maria"]
        }],
        "gender": "female",
        "birthDate": "1959-09-05",
        "address": [{
            "use": "home",
            "line": ["789 Elm Drive"],
            "city": "San Jose",
            "state": "CA",
            "postalCode": "95112"
        }],
        "maritalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                "code": "M",
                "display": "Married"
            }]
        },
        "communication": [{
            "language": {
                "coding": [{
                    "system": "urn:ietf:bcp:47",
                    "code": "en",
                    "display": "English"
                }]
            },
            "preferred": True
        }]
    })

    # Conditions
    conditions = [
        ("condition-linda-martinez-pancreatic-cancer", "363418001", "Malignant neoplasm of pancreas", "Pancreatic Head Adenocarcinoma", "2026-01-20"),
        ("condition-linda-martinez-diabetes", "44054006", "Type 2 diabetes mellitus", "Type 2 Diabetes Mellitus", "2018-04-10"),
        ("condition-linda-martinez-hypertension", "38341003", "Hypertensive disorder", "Hypertension", "2015-08-20"),
    ]
    for cid, code, code_display, text, onset in conditions:
        write_resource("Condition", cid, {
            "resourceType": "Condition",
            "id": cid,
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
            },
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
            },
            "verificationStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]
            },
            "category": [{
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item"}]
            }],
            "code": {
                "coding": [{"system": "http://snomed.info/sct", "code": code, "display": code_display}],
                "text": text
            },
            "subject": {"reference": f"Patient/{pid}", "display": display},
            "onsetDateTime": onset
        })

    # Medications
    meds = [
        ("medrx-linda-martinez-metformin", "861004", "Metformin 500 MG Oral Tablet", "Metformin 500mg",
         "Take 1 tablet by mouth twice daily with meals", 2, 500, "mg", "2018-05-01"),
        ("medrx-linda-martinez-amlodipine", "197361", "Amlodipine 5 MG Oral Tablet", "Amlodipine 5mg",
         "Take 1 tablet by mouth once daily", 1, 5, "mg", "2015-09-01"),
        ("medrx-linda-martinez-omeprazole", "198053", "Omeprazole 20 MG Delayed Release Oral Capsule", "Omeprazole 20mg",
         "Take 1 capsule by mouth once daily before breakfast", 1, 20, "mg", "2023-03-15"),
    ]
    for mid, rxcode, rxdisplay, text, dosage_text, freq, dose_val, dose_unit, authored in meds:
        write_resource("MedicationRequest", mid, {
            "resourceType": "MedicationRequest",
            "id": mid,
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": rxcode, "display": rxdisplay}],
                "text": text
            },
            "subject": {"reference": f"Patient/{pid}", "display": display},
            "authoredOn": authored,
            "dosageInstruction": [{
                "text": dosage_text,
                "timing": {"repeat": {"frequency": freq, "period": 1, "periodUnit": "d"}},
                "route": {"coding": [{"system": "http://snomed.info/sct", "code": "26643006", "display": "Oral route"}]},
                "doseAndRate": [{"doseQuantity": {"value": dose_val, "unit": dose_unit}}]
            }]
        })

    # No allergies for Linda Martinez (none known)
    # We can skip AllergyIntolerance or create a "no known allergies" resource
    # Per spec: "AllergyIntolerance/{id}.json (if patient has allergies)" - skip

    # Vitals
    visit_date = "2026-02-05"
    vitals_time = f"{visit_date}T10:00:00Z"

    # BP
    write_resource("Observation", f"obs-linda-martinez-bp-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-linda-martinez-bp-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": vitals_time,
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": 138, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                "valueQuantity": {"value": 78, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            }
        ]
    })

    # HR
    write_resource("Observation", f"obs-linda-martinez-hr-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-linda-martinez-hr-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": vitals_time,
        "valueQuantity": {"value": 88, "unit": "beats/minute", "system": "http://unitsofmeasure.org", "code": "/min"}
    })

    # Temp
    write_resource("Observation", f"obs-linda-martinez-temp-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-linda-martinez-temp-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": vitals_time,
        "valueQuantity": {"value": 98.6, "unit": "degF", "system": "http://unitsofmeasure.org", "code": "[degF]"}
    })

    # Labs
    lab_time = f"{visit_date}T08:00:00Z"

    # CA 19-9
    write_resource("Observation", f"obs-linda-martinez-ca19-9-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-linda-martinez-ca19-9-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "24108-3", "display": "CA 19-9 [Units/volume] in Serum or Plasma"}], "text": "CA 19-9"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 842, "unit": "U/mL", "system": "http://unitsofmeasure.org", "code": "U/mL"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]}],
        "referenceRange": [{"low": {"value": 0, "unit": "U/mL"}, "high": {"value": 37, "unit": "U/mL"}}]
    })

    # Bilirubin
    write_resource("Observation", f"obs-linda-martinez-bilirubin-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-linda-martinez-bilirubin-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "1975-2", "display": "Bilirubin.total [Mass/volume] in Serum or Plasma"}], "text": "Total Bilirubin"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 3.2, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]}],
        "referenceRange": [{"low": {"value": 0.1, "unit": "mg/dL"}, "high": {"value": 1.2, "unit": "mg/dL"}}]
    })

    # ALT
    write_resource("Observation", f"obs-linda-martinez-alt-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-linda-martinez-alt-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "1742-6", "display": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma"}], "text": "ALT"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 98, "unit": "U/L", "system": "http://unitsofmeasure.org", "code": "U/L"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]}],
        "referenceRange": [{"low": {"value": 7, "unit": "U/L"}, "high": {"value": 56, "unit": "U/L"}}]
    })

    # AST
    write_resource("Observation", f"obs-linda-martinez-ast-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-linda-martinez-ast-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "1920-8", "display": "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma"}], "text": "AST"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 87, "unit": "U/L", "system": "http://unitsofmeasure.org", "code": "U/L"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]}],
        "referenceRange": [{"low": {"value": 10, "unit": "U/L"}, "high": {"value": 40, "unit": "U/L"}}]
    })

    # Lipase
    write_resource("Observation", f"obs-linda-martinez-lipase-{visit_date}", {
        "resourceType": "Observation",
        "id": f"obs-linda-martinez-lipase-{visit_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "3040-3", "display": "Lipase [Enzymatic activity/volume] in Serum or Plasma"}], "text": "Lipase"},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": lab_time,
        "valueQuantity": {"value": 45, "unit": "U/L", "system": "http://unitsofmeasure.org", "code": "U/L"},
        "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]}],
        "referenceRange": [{"low": {"value": 0, "unit": "U/L"}, "high": {"value": 160, "unit": "U/L"}}]
    })

    # Encounter - AMB for oncology visit
    write_resource("Encounter", f"encounter-linda-martinez-{visit_date}", {
        "resourceType": "Encounter",
        "id": f"encounter-linda-martinez-{visit_date}",
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB", "display": "ambulatory"},
        "type": [{"coding": [{"system": "http://snomed.info/sct", "code": "185349003", "display": "Encounter for check up"}]}],
        "subject": {"reference": f"Patient/{pid}"},
        "period": {"start": f"{visit_date}T09:30:00Z", "end": f"{visit_date}T10:30:00Z"},
        "reasonCode": [{
            "coding": [{"system": "http://snomed.info/sct", "code": "363418001", "display": "Malignant neoplasm of pancreas"}],
            "text": "Oncology evaluation - pancreatic cancer staging"
        }]
    })

    # DocumentReferences
    doc_author = [{"display": "Dr. Rebecca Liu, MD"}]
    docs = [
        ("doc-linda-martinez-hpi", "10164-2", "History of Present illness", LINDA_HPI),
        ("doc-linda-martinez-ros", "10187-3", "Review of systems", LINDA_ROS),
        ("doc-linda-martinez-physical-exam", "29545-1", "Physical findings", LINDA_PE),
        ("doc-linda-martinez-clinical-note", "11506-3", "Progress note", LINDA_CLINICAL_NOTE),
    ]
    for did, loinc, loinc_display, content_text in docs:
        write_resource("DocumentReference", did, {
            "resourceType": "DocumentReference",
            "id": did,
            "status": "current",
            "type": {"coding": [{"system": "http://loinc.org", "code": loinc, "display": loinc_display}]},
            "category": [{"coding": [{"system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category", "code": "clinical-note", "display": "Clinical Note"}]}],
            "subject": {"reference": f"Patient/{pid}"},
            "date": f"{visit_date}T10:00:00Z",
            "author": doc_author,
            "content": [{"attachment": {"contentType": "text/plain", "data": b64(content_text)}}]
        })

    # Media - CT Abdomen
    write_resource("Media", "media-linda-martinez-ct-abdomen", {
        "resourceType": "Media",
        "id": "media-linda-martinez-ct-abdomen",
        "status": "completed",
        "type": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/media-type", "code": "image", "display": "Image"}]
        },
        "modality": {
            "coding": [{"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CT", "display": "Computed Tomography"}]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "createdDateTime": f"{visit_date}T08:30:00Z",
        "bodySite": {
            "coding": [{"system": "http://snomed.info/sct", "code": "818983003", "display": "Abdomen"}]
        },
        "content": {
            "contentType": "image/png",
            "url": "file://data/images/linda-martinez-ct-abdomen.png",
            "title": "CT Abdomen with contrast"
        },
        "note": [{
            "text": "3.2 cm mass in the head of the pancreas with upstream bile duct dilation to 12mm. Possible abutment of the superior mesenteric artery. No liver metastases identified. No ascites. No peritoneal implants seen."
        }]
    })


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print("Generating FHIR R4 resources for patients 1-3...")
    generate_margaret_chen()
    generate_james_wilson()
    generate_linda_martinez()
    print("\nDone! All FHIR resources generated successfully.")
