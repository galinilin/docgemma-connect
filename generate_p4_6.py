#!/usr/bin/env python3
"""Generate FHIR R4-compliant JSON files for patients 4-6:
  4. Robert Thompson (patient-robert-thompson)
  5. Doris Yamamoto (patient-doris-yamamoto)
  6. Baby Boy Torres (patient-baby-torres)
"""

import json
import base64
import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "data" / "fhir"


def write_resource(resource_type: str, resource: dict) -> str:
    """Write a FHIR resource to the appropriate directory."""
    dir_path = OUTPUT_DIR / resource_type
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f"{resource['id']}.json"
    with open(file_path, "w") as f:
        json.dump(resource, f, indent=2)
    print(f"  Written: {file_path}")
    return str(file_path)


def b64(text: str) -> str:
    """Base64-encode a string."""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


# ============================================================================
# PATIENT 4: Robert Thompson
# ============================================================================
def generate_robert_thompson():
    print("\n=== Generating Robert Thompson ===")
    pid = "patient-robert-thompson"
    encounter_date = "2026-02-15"

    # --- Patient ---
    write_resource("Patient", {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "RT-2024-004"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Thompson",
            "given": ["Robert", "James"]
        }],
        "gender": "male",
        "birthDate": "1981-06-22",
        "address": [{
            "use": "home",
            "line": ["456 Maple Avenue"],
            "city": "Oakland",
            "state": "CA",
            "postalCode": "94612"
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

    # --- Conditions ---
    write_resource("Condition", {
        "resourceType": "Condition",
        "id": f"condition-{pid.replace('patient-','')}-melanocytic-proliferation",
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
        },
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "provisional"}]
        },
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item"}]
        }],
        "code": {
            "coding": [{"system": "http://snomed.info/sct", "code": "307602007", "display": "Atypical melanocytic proliferation"}],
            "text": "Atypical melanocytic proliferation (biopsy pending final read)"
        },
        "subject": {"reference": f"Patient/{pid}", "display": "Robert Thompson"},
        "onsetDateTime": "2026-02-10"
    })

    write_resource("Condition", {
        "resourceType": "Condition",
        "id": f"condition-{pid.replace('patient-','')}-hypertension",
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
            "coding": [{"system": "http://snomed.info/sct", "code": "38341003", "display": "Hypertensive disorder"}],
            "text": "Hypertension"
        },
        "subject": {"reference": f"Patient/{pid}", "display": "Robert Thompson"},
        "onsetDateTime": "2022-03-01"
    })

    # --- MedicationRequest ---
    write_resource("MedicationRequest", {
        "resourceType": "MedicationRequest",
        "id": f"medrx-{pid.replace('patient-','')}-hydrochlorothiazide",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "310798",
                "display": "Hydrochlorothiazide 25 MG Oral Tablet"
            }],
            "text": "Hydrochlorothiazide 25mg"
        },
        "subject": {"reference": f"Patient/{pid}", "display": "Robert Thompson"},
        "authoredOn": "2022-03-15",
        "dosageInstruction": [{
            "text": "Take 1 tablet by mouth once daily in the morning",
            "timing": {
                "repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}
            },
            "route": {
                "coding": [{"system": "http://snomed.info/sct", "code": "26643006", "display": "Oral route"}]
            },
            "doseAndRate": [{"doseQuantity": {"value": 25, "unit": "mg"}}]
        }]
    })

    # --- No AllergyIntolerance for Robert Thompson ---

    # --- Observations: Vitals ---
    # Blood Pressure
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-bp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T10:00:00Z",
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": 132, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                "valueQuantity": {"value": 84, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            }
        ]
    })

    # Heart Rate
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-hr-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T10:00:00Z",
        "valueQuantity": {"value": 72, "unit": "/min", "system": "http://unitsofmeasure.org", "code": "/min"}
    })

    # Temperature
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-temp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T10:00:00Z",
        "valueQuantity": {"value": 98.2, "unit": "degF", "system": "http://unitsofmeasure.org", "code": "[degF]"}
    })

    # --- Observations: Labs ---
    # CBC (WBC)
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-wbc-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "6690-2", "display": "Leukocytes [#/volume] in Blood"}],
            "text": "WBC"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 7.2, "unit": "10*3/uL", "system": "http://unitsofmeasure.org", "code": "10*3/uL"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]
        }],
        "referenceRange": [{"low": {"value": 4.5, "unit": "10*3/uL"}, "high": {"value": 11.0, "unit": "10*3/uL"}}]
    })

    # Hemoglobin
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-hgb-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "718-7", "display": "Hemoglobin [Mass/volume] in Blood"}],
            "text": "Hemoglobin"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 14.8, "unit": "g/dL", "system": "http://unitsofmeasure.org", "code": "g/dL"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]
        }],
        "referenceRange": [{"low": {"value": 13.5, "unit": "g/dL"}, "high": {"value": 17.5, "unit": "g/dL"}}]
    })

    # Platelets
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-plt-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "777-3", "display": "Platelets [#/volume] in Blood"}],
            "text": "Platelets"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 245, "unit": "10*3/uL", "system": "http://unitsofmeasure.org", "code": "10*3/uL"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]
        }],
        "referenceRange": [{"low": {"value": 150, "unit": "10*3/uL"}, "high": {"value": 400, "unit": "10*3/uL"}}]
    })

    # Sodium
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-sodium-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2951-2", "display": "Sodium [Moles/volume] in Serum or Plasma"}],
            "text": "Sodium"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 140, "unit": "mmol/L", "system": "http://unitsofmeasure.org", "code": "mmol/L"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]
        }],
        "referenceRange": [{"low": {"value": 136, "unit": "mmol/L"}, "high": {"value": 145, "unit": "mmol/L"}}]
    })

    # Potassium
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-potassium-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2823-3", "display": "Potassium [Moles/volume] in Serum or Plasma"}],
            "text": "Potassium"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 4.1, "unit": "mmol/L", "system": "http://unitsofmeasure.org", "code": "mmol/L"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]
        }],
        "referenceRange": [{"low": {"value": 3.5, "unit": "mmol/L"}, "high": {"value": 5.0, "unit": "mmol/L"}}]
    })

    # Creatinine
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-creatinine-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma"}],
            "text": "Creatinine"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 1.0, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]
        }],
        "referenceRange": [{"low": {"value": 0.7, "unit": "mg/dL"}, "high": {"value": 1.3, "unit": "mg/dL"}}]
    })

    # Glucose
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-glucose-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2345-7", "display": "Glucose [Mass/volume] in Serum or Plasma"}],
            "text": "Glucose"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 95, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]
        }],
        "referenceRange": [{"low": {"value": 70, "unit": "mg/dL"}, "high": {"value": 100, "unit": "mg/dL"}}]
    })

    # LDH
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-ldh-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2532-0", "display": "Lactate dehydrogenase [Enzymatic activity/volume] in Serum or Plasma"}],
            "text": "LDH"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 180, "unit": "U/L", "system": "http://unitsofmeasure.org", "code": "U/L"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]
        }],
        "referenceRange": [{"low": {"value": 140, "unit": "U/L"}, "high": {"value": 280, "unit": "U/L"}}]
    })

    # --- Encounter ---
    write_resource("Encounter", {
        "resourceType": "Encounter",
        "id": f"encounter-{pid.replace('patient-','')}-{encounter_date}",
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory"
        },
        "type": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "185349003",
                "display": "Encounter for check up"
            }]
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "period": {
            "start": f"{encounter_date}T09:30:00Z",
            "end": f"{encounter_date}T10:15:00Z"
        },
        "reasonCode": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "307602007",
                "display": "Atypical melanocytic proliferation"
            }],
            "text": "Evaluation of pigmented lesion with biopsy results"
        }]
    })

    # --- DocumentReferences ---
    hpi_text = (
        "45-year-old African American male construction worker presents for follow-up evaluation of a pigmented lesion "
        "on his left forearm. The patient first noticed the lesion approximately six months ago and reports that it has "
        "undergone a noticeable change in color over the past two to three months, transitioning from a uniform brown to "
        "a darker, more variegated appearance with areas of blue-black pigmentation. He also noted the borders have become "
        "increasingly irregular and asymmetric. The lesion is not painful and does not itch, but he recalls a single episode "
        "of minor bleeding after accidentally bumping it at work approximately three weeks ago. A punch biopsy was performed "
        "one week ago and the preliminary pathology report describes atypical melanocytic proliferation with spitzoid features. "
        "The final pathology read is still pending. The patient has no personal history of skin cancer. He has a family history "
        "significant for his maternal uncle having been diagnosed with melanoma at age 55. The patient works outdoors daily "
        "and acknowledges inconsistent use of sunscreen. He has a history of multiple sunburns in his youth. He also has a "
        "history of well-controlled hypertension managed with hydrochlorothiazide. He denies any weight loss, fatigue, night "
        "sweats, or other constitutional symptoms. He is anxious about the biopsy results and inquires about next steps."
    )

    ros_text = (
        "Constitutional: No fever, no chills, no unintentional weight loss, no night sweats, no fatigue\n"
        "HEENT: No vision changes, no hearing loss, no oral lesions\n"
        "Cardiovascular: No chest pain, no palpitations, no dyspnea on exertion, no lower extremity edema\n"
        "Respiratory: No cough, no shortness of breath, no wheezing, no hemoptysis\n"
        "GI: No nausea, no vomiting, no abdominal pain, no change in bowel habits, no melena\n"
        "GU: No dysuria, no hematuria, no frequency\n"
        "Musculoskeletal: No joint pain, no muscle weakness, no back pain\n"
        "Neurological: No headache, no numbness, no tingling, no focal weakness\n"
        "Skin: Pigmented lesion on left forearm with recent color change and irregular borders. "
        "No other new or changing moles noted. No pruritus elsewhere. Single episode of bleeding from the lesion.\n"
        "Psychiatric: Reports anxiety regarding biopsy results but denies depressed mood, insomnia, or suicidal ideation\n"
        "Hematologic/Lymphatic: No easy bruising, no palpable lymphadenopathy noted by patient"
    )

    pe_text = (
        "Vitals: BP 132/84 mmHg, HR 72 bpm regular, RR 14, Temp 98.2 F, SpO2 99% RA\n\n"
        "General: Well-developed, well-nourished male in no acute distress. Alert and oriented, appears mildly anxious.\n\n"
        "HEENT: Normocephalic, atraumatic. Pupils equal, round, reactive to light and accommodation. "
        "Oropharynx clear, moist mucous membranes. No oral lesions.\n\n"
        "Neck: Supple. No cervical, supraclavicular, or axillary lymphadenopathy. No thyromegaly.\n\n"
        "Cardiovascular: Regular rate and rhythm. Normal S1 and S2. No murmurs, rubs, or gallops. "
        "No peripheral edema. Capillary refill less than 2 seconds.\n\n"
        "Respiratory: Clear to auscultation bilaterally. No wheezes, rales, or rhonchi. Symmetric chest expansion.\n\n"
        "Abdomen: Soft, non-tender, non-distended. Normal bowel sounds in all four quadrants. "
        "No hepatosplenomegaly. No masses palpable.\n\n"
        "Extremities: Left forearm demonstrates a 7mm asymmetric, irregularly bordered pigmented lesion with "
        "variegated coloration including shades of tan, dark brown, and blue-black. The biopsy site shows a "
        "well-healing punch biopsy wound with intact sutures, no signs of infection, minimal surrounding erythema. "
        "No satellite lesions. Right forearm and bilateral lower extremities without concerning lesions.\n\n"
        "Lymph Nodes: No palpable epitrochlear, axillary, cervical, supraclavicular, or inguinal lymphadenopathy.\n\n"
        "Full skin examination: Multiple scattered benign-appearing nevi on trunk and upper extremities, none with "
        "features concerning for dysplasia. No other suspicious pigmented lesions identified. No ulcerations or "
        "non-healing wounds.\n\n"
        "Neurological: Alert and oriented x3. Cranial nerves II-XII grossly intact. Strength 5/5 in all extremities. "
        "Sensation intact to light touch."
    )

    clinical_note_text = (
        "Assessment and Plan:\n\n"
        "45-year-old male with a 7mm pigmented lesion on the left forearm showing atypical melanocytic proliferation "
        "with spitzoid features on preliminary pathology. The lesion demonstrates concerning clinical features including "
        "asymmetry, irregular borders, color variegation, and recent change in appearance. LDH is within normal limits "
        "at 180 U/L and CBC and CMP are unremarkable, which is reassuring. No palpable lymphadenopathy detected on "
        "examination.\n\n"
        "1. Atypical melanocytic proliferation, left forearm: Awaiting final pathology with immunohistochemistry. "
        "If the final read confirms atypical Spitz tumor or melanoma, will need wide local excision with appropriate "
        "margins. Dermatopathology second opinion has been requested. If melanoma is confirmed with Breslow depth "
        "greater than 0.8 mm, sentinel lymph node biopsy will be indicated. Patient counseled on the importance of "
        "awaiting final pathology before definitive management.\n\n"
        "2. Hypertension, controlled: Continue hydrochlorothiazide 25mg daily. BP at goal today at 132/84.\n\n"
        "3. Sun protection counseling: Emphasized daily broad-spectrum SPF 50+ sunscreen use, protective clothing, "
        "and avoidance of peak UV hours given outdoor occupation. Discussed workplace sun safety strategies.\n\n"
        "Follow-up in 1 week for final pathology results. Sooner if results available earlier. "
        "Patient advised to contact clinic immediately if lesion changes or new symptoms develop."
    )

    for doc_type, loinc_code, loinc_display, suffix, text in [
        ("hpi", "10164-2", "History of Present illness", "hpi", hpi_text),
        ("ros", "10187-3", "Review of systems", "ros", ros_text),
        ("physical-exam", "29545-1", "Physical findings", "physical-exam", pe_text),
        ("clinical-note", "11506-3", "Progress note", "clinical-note", clinical_note_text),
    ]:
        write_resource("DocumentReference", {
            "resourceType": "DocumentReference",
            "id": f"doc-{pid.replace('patient-','')}-{suffix}",
            "status": "current",
            "type": {
                "coding": [{"system": "http://loinc.org", "code": loinc_code, "display": loinc_display}]
            },
            "category": [{
                "coding": [{
                    "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                    "code": "clinical-note",
                    "display": "Clinical Note"
                }]
            }],
            "subject": {"reference": f"Patient/{pid}"},
            "date": f"{encounter_date}T10:00:00Z",
            "author": [{"display": "Dr. Michelle Park, MD - Dermatology"}],
            "content": [{
                "attachment": {
                    "contentType": "text/plain",
                    "data": b64(text)
                }
            }]
        })

    # --- Media: Histopathology ---
    write_resource("Media", {
        "resourceType": "Media",
        "id": f"media-{pid.replace('patient-','')}-histopathology",
        "status": "completed",
        "type": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/media-type", "code": "image", "display": "Image"}]
        },
        "modality": {
            "coding": [{
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "code": "SM",
                "display": "Slide Microscopy"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "createdDateTime": f"{encounter_date}T11:00:00Z",
        "bodySite": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "66480008",
                "display": "Structure of left forearm"
            }]
        },
        "content": {
            "contentType": "image/png",
            "url": "file://data/images/robert-thompson-histopath.png",
            "title": "H&E skin punch biopsy - left forearm pigmented lesion"
        },
        "note": [{
            "text": "Skin punch biopsy, left forearm: Atypical melanocytic proliferation with spitzoid features. "
                    "7mm lesion showing irregular nests of melanocytes with pagetoid spread. Cytologic atypia present. "
                    "Immunohistochemistry pending for definitive classification. Final pathology report to follow."
        }]
    })


# ============================================================================
# PATIENT 5: Doris Yamamoto
# ============================================================================
def generate_doris_yamamoto():
    print("\n=== Generating Doris Yamamoto ===")
    pid = "patient-doris-yamamoto"
    encounter_date = "2026-02-18"

    # --- Patient ---
    write_resource("Patient", {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "DY-2024-005"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Yamamoto",
            "given": ["Doris", "Keiko"]
        }],
        "gender": "female",
        "birthDate": "1953-09-08",
        "address": [{
            "use": "home",
            "line": ["789 Cherry Blossom Lane"],
            "city": "San Jose",
            "state": "CA",
            "postalCode": "95112"
        }],
        "maritalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                "code": "W",
                "display": "Widowed"
            }]
        },
        "communication": [{
            "language": {
                "coding": [{"system": "urn:ietf:bcp:47", "code": "en", "display": "English"}]
            },
            "preferred": True
        }]
    })

    # --- Conditions ---
    conditions = [
        ("stroke", "422504002", "Cerebral infarction", "Acute left MCA territory infarct", "2026-02-18", "active", "confirmed"),
        ("afib", "49436004", "Atrial fibrillation", "Atrial fibrillation", "2020-05-01", "active", "confirmed"),
        ("hypertension", "38341003", "Hypertensive disorder", "Hypertension", "2015-03-01", "active", "confirmed"),
        ("hyperlipidemia", "55822004", "Hyperlipidemia", "Hyperlipidemia", "2016-08-01", "active", "confirmed"),
        ("dvt", "128053003", "Deep venous thrombosis", "Prior DVT (resolved)", "2024-02-01", "resolved", "confirmed"),
    ]
    for suffix, snomed, display, text, onset, clinical, verification in conditions:
        cond = {
            "resourceType": "Condition",
            "id": f"condition-{pid.replace('patient-','')}-{suffix}",
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
            },
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": clinical}]
            },
            "verificationStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": verification}]
            },
            "category": [{
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item"}]
            }],
            "code": {
                "coding": [{"system": "http://snomed.info/sct", "code": snomed, "display": display}],
                "text": text
            },
            "subject": {"reference": f"Patient/{pid}", "display": "Doris Yamamoto"},
            "onsetDateTime": onset
        }
        write_resource("Condition", cond)

    # --- MedicationRequests ---
    meds = [
        ("apixaban", "1364435", "Apixaban 5 MG Oral Tablet", "Apixaban 5mg", "Take 1 tablet by mouth twice daily", 2, 5, "2020-06-01"),
        ("atorvastatin", "617312", "Atorvastatin 80 MG Oral Tablet", "Atorvastatin 80mg", "Take 1 tablet by mouth once daily at bedtime", 1, 80, "2016-09-01"),
        ("amlodipine", "308135", "Amlodipine 10 MG Oral Tablet", "Amlodipine 10mg", "Take 1 tablet by mouth once daily", 1, 10, "2015-04-01"),
    ]
    for suffix, rxnorm, rx_display, text, instruction, freq, dose, authored in meds:
        write_resource("MedicationRequest", {
            "resourceType": "MedicationRequest",
            "id": f"medrx-{pid.replace('patient-','')}-{suffix}",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": rxnorm,
                    "display": rx_display
                }],
                "text": text
            },
            "subject": {"reference": f"Patient/{pid}", "display": "Doris Yamamoto"},
            "authoredOn": authored,
            "dosageInstruction": [{
                "text": instruction,
                "timing": {"repeat": {"frequency": freq, "period": 1, "periodUnit": "d"}},
                "route": {
                    "coding": [{"system": "http://snomed.info/sct", "code": "26643006", "display": "Oral route"}]
                },
                "doseAndRate": [{"doseQuantity": {"value": dose, "unit": "mg"}}]
            }]
        })

    # --- AllergyIntolerance: Iodinated contrast ---
    write_resource("AllergyIntolerance", {
        "resourceType": "AllergyIntolerance",
        "id": f"allergy-{pid.replace('patient-','')}-iodinated-contrast",
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
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "39065001",
                "display": "Iodinated contrast media"
            }],
            "text": "Iodinated contrast"
        },
        "patient": {"reference": f"Patient/{pid}", "display": "Doris Yamamoto"},
        "recordedDate": "2018-11-20",
        "reaction": [{
            "manifestation": [{
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "41291007",
                    "display": "Angioedema"
                }],
                "text": "Anaphylactoid reaction with facial angioedema"
            }],
            "severity": "severe",
            "description": "Anaphylactoid reaction with facial angioedema during CT scan with iodinated contrast in 2018. Required epinephrine and overnight observation."
        }]
    })

    # --- Observations: Vitals ---
    # Blood Pressure
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-bp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]
        }],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:30:00Z",
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": 168, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                "valueQuantity": {"value": 94, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            }
        ]
    })

    # Heart Rate
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-hr-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]
        }],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:30:00Z",
        "valueQuantity": {"value": 88, "unit": "/min", "system": "http://unitsofmeasure.org", "code": "/min"},
        "note": [{"text": "Irregular rhythm"}]
    })

    # Temperature
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-temp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]
        }],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:30:00Z",
        "valueQuantity": {"value": 98.4, "unit": "degF", "system": "http://unitsofmeasure.org", "code": "[degF]"}
    })

    # --- Observations: Labs ---
    # Anti-Xa (pending)
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-anti-xa-{encounter_date}",
        "status": "registered",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "3173-2", "display": "Anti-Xa activity in Platelet poor plasma"}],
            "text": "Anti-Xa level"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:00:00Z",
        "note": [{"text": "Result pending"}]
    })

    # Glucose
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-glucose-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2345-7", "display": "Glucose [Mass/volume] in Serum or Plasma"}],
            "text": "Glucose"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:00:00Z",
        "valueQuantity": {"value": 142, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]
        }],
        "referenceRange": [{"low": {"value": 70, "unit": "mg/dL"}, "high": {"value": 100, "unit": "mg/dL"}}]
    })

    # Creatinine
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-creatinine-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma"}],
            "text": "Creatinine"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:00:00Z",
        "valueQuantity": {"value": 0.9, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]
        }],
        "referenceRange": [{"low": {"value": 0.6, "unit": "mg/dL"}, "high": {"value": 1.1, "unit": "mg/dL"}}]
    })

    # --- Encounter (EMER for stroke) ---
    write_resource("Encounter", {
        "resourceType": "Encounter",
        "id": f"encounter-{pid.replace('patient-','')}-{encounter_date}",
        "status": "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "EMER",
            "display": "emergency"
        },
        "type": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "50849002",
                "display": "Emergency room admission"
            }]
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "period": {
            "start": f"{encounter_date}T06:15:00Z"
        },
        "reasonCode": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "422504002",
                "display": "Cerebral infarction"
            }],
            "text": "Acute onset expressive aphasia and right hemiparesis"
        }]
    })

    # --- DocumentReferences ---
    hpi_text = (
        "72-year-old Japanese American retired professor brought to the emergency department by EMS after acute onset "
        "of speech difficulty and right-sided weakness approximately three hours prior to arrival. Per her daughter who "
        "was present at the time of onset, the patient was having breakfast when she suddenly began slurring her words "
        "and was unable to form coherent sentences. She then dropped her coffee cup with her right hand and was unable "
        "to lift her right arm. EMS activated stroke code upon arrival to the home. The patient has a significant history "
        "of atrial fibrillation diagnosed in 2020 for which she has been maintained on apixaban 5mg twice daily. Her "
        "daughter confirms the patient has been compliant with her anticoagulation medication, with the last dose taken "
        "at approximately 10 PM the prior evening. The patient also has a history of hypertension managed with amlodipine "
        "10mg daily and hyperlipidemia treated with atorvastatin 80mg daily. Of note, she had a documented deep venous "
        "thrombosis two years ago which was treated and has since resolved. She has a known allergy to iodinated contrast "
        "media with a prior anaphylactoid reaction involving facial angioedema in 2018, which is critically important for "
        "imaging planning. NIHSS on arrival is 14, with points for gaze deviation, facial palsy, right arm and leg weakness, "
        "limb ataxia, sensory loss, and expressive aphasia. The patient appears to understand simple commands but cannot "
        "verbalize responses. Last known well time was approximately 6:00 AM today."
    )

    ros_text = (
        "Constitutional: Unable to fully assess due to aphasia; no apparent fever or diaphoresis\n"
        "HEENT: Left gaze preference noted; unable to assess visual fields reliably; no apparent facial pain\n"
        "Cardiovascular: Irregular heart rate noted; no chest pain per daughter; no lower extremity edema\n"
        "Respiratory: No respiratory distress observed, no cough, breathing appears non-labored\n"
        "GI: Daughter reports no recent nausea, vomiting, abdominal pain, or change in bowel habits\n"
        "GU: No reported urinary complaints prior to event; Foley catheter placed on arrival\n"
        "Musculoskeletal: Right-sided hemiparesis noted; no prior joint complaints per daughter\n"
        "Neurological: Acute expressive aphasia, right hemiparesis (arm greater than leg), right facial droop, "
        "left gaze preference, right-sided sensory loss. No seizure activity witnessed.\n"
        "Skin: No rashes, no pressure injuries, skin warm and dry\n"
        "Psychiatric: Patient appears frustrated with inability to communicate; no prior psychiatric history per daughter"
    )

    pe_text = (
        "Vitals: BP 168/94 mmHg, HR 88 bpm irregular, RR 16, Temp 98.4 F, SpO2 97% RA\n\n"
        "General: Elderly woman lying in stretcher, alert but unable to speak fluently. Appears frustrated. "
        "No acute respiratory distress.\n\n"
        "HEENT: Normocephalic, atraumatic. Pupils 3mm bilaterally, equal and reactive. Left conjugate gaze "
        "deviation present. Right nasolabial fold flattened. Oropharynx difficult to assess due to limited "
        "cooperation, but appears moist without blood.\n\n"
        "Neck: Supple. No carotid bruits appreciated bilaterally. No meningismus. JVP not elevated.\n\n"
        "Cardiovascular: Irregularly irregular rhythm consistent with atrial fibrillation. Rate controlled. "
        "Normal S1 and S2. No murmurs, rubs, or gallops. No peripheral edema.\n\n"
        "Respiratory: Clear to auscultation bilaterally. No wheezes, crackles, or rhonchi. "
        "Equal air entry bilaterally.\n\n"
        "Abdomen: Soft, non-tender on palpation. Non-distended. Bowel sounds present.\n\n"
        "Neurological Examination (NIHSS 14):\n"
        "  - Level of consciousness: Alert, follows simple commands inconsistently (1)\n"
        "  - LOC questions: Unable to answer (2)\n"
        "  - LOC commands: Performs one of two (1)\n"
        "  - Best gaze: Forced left gaze deviation, partially overcome by oculocephalic (1)\n"
        "  - Visual fields: Right homonymous hemianopia (2)\n"
        "  - Facial palsy: Right lower facial droop, partial (1)\n"
        "  - Motor arm right: Drifts down within 5 seconds, some effort against gravity (2)\n"
        "  - Motor arm left: No drift (0)\n"
        "  - Motor leg right: Drifts down within 5 seconds (1)\n"
        "  - Motor leg left: No drift (0)\n"
        "  - Limb ataxia: Unable to assess right side due to weakness (0)\n"
        "  - Sensory: Right-sided decreased sensation to pinprick (1)\n"
        "  - Best language: Severe expressive aphasia, nonfluent, few recognizable words (2)\n"
        "  - Dysarthria: Severe (present but not scorable separately given aphasia)\n"
        "  - Extinction/inattention: Extinction to double simultaneous stimulation (0)\n\n"
        "Skin: No rashes, no bruising. Warm and well-perfused."
    )

    clinical_note_text = (
        "Assessment and Plan:\n\n"
        "72-year-old woman with atrial fibrillation on apixaban presenting with acute left MCA syndrome "
        "with NIHSS 14 approximately 3 hours from last known well. Symptoms include expressive aphasia, "
        "right hemiparesis, right facial droop, and gaze deviation.\n\n"
        "1. Acute ischemic stroke, left MCA territory: Brain MRI with DWI obtained urgently (non-contrast, given "
        "documented iodinated contrast allergy with prior anaphylactoid reaction) confirms restricted diffusion in "
        "the left MCA territory. Given the patient is on therapeutic apixaban with last dose approximately 8 hours "
        "ago, IV tPA is contraindicated. Anti-Xa level has been sent to quantify anticoagulation level. Neurology "
        "and neurointerventional radiology consulted for potential mechanical thrombectomy given large vessel "
        "occlusion on MRA. Continuous telemetry monitoring. Permissive hypertension with target BP less than "
        "220/120 per acute stroke protocol. Aspirin held pending intervention decision.\n\n"
        "2. Atrial fibrillation: Hold apixaban in acute setting pending procedural decisions. Resume anticoagulation "
        "per neurology recommendation, typically 24-48 hours post-event if no hemorrhagic conversion.\n\n"
        "3. Hypertension: Hold amlodipine per stroke protocol. IV labetalol available if BP exceeds 220/120.\n\n"
        "4. Iodinated contrast allergy: CRITICAL - if CT angiography or catheter angiography required, must "
        "premedicate with corticosteroids and diphenhydramine per protocol. MRI/MRA preferred when feasible.\n\n"
        "5. Admit to Neuro ICU for close monitoring. Swallow evaluation before any PO intake. DVT prophylaxis "
        "with pneumatic compression devices."
    )

    for doc_type, loinc_code, loinc_display, suffix, text in [
        ("hpi", "10164-2", "History of Present illness", "hpi", hpi_text),
        ("ros", "10187-3", "Review of systems", "ros", ros_text),
        ("physical-exam", "29545-1", "Physical findings", "physical-exam", pe_text),
        ("clinical-note", "11506-3", "Progress note", "clinical-note", clinical_note_text),
    ]:
        write_resource("DocumentReference", {
            "resourceType": "DocumentReference",
            "id": f"doc-{pid.replace('patient-','')}-{suffix}",
            "status": "current",
            "type": {
                "coding": [{"system": "http://loinc.org", "code": loinc_code, "display": loinc_display}]
            },
            "category": [{
                "coding": [{
                    "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                    "code": "clinical-note",
                    "display": "Clinical Note"
                }]
            }],
            "subject": {"reference": f"Patient/{pid}"},
            "date": f"{encounter_date}T07:00:00Z",
            "author": [{"display": "Dr. Kevin Liu, MD - Neurology"}],
            "content": [{
                "attachment": {
                    "contentType": "text/plain",
                    "data": b64(text)
                }
            }]
        })

    # --- Media: Brain MRI ---
    write_resource("Media", {
        "resourceType": "Media",
        "id": f"media-{pid.replace('patient-','')}-brain-mri",
        "status": "completed",
        "type": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/media-type", "code": "image", "display": "Image"}]
        },
        "modality": {
            "coding": [{
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "code": "MR",
                "display": "Magnetic Resonance"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "createdDateTime": f"{encounter_date}T07:15:00Z",
        "bodySite": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "12738006",
                "display": "Brain structure"
            }]
        },
        "content": {
            "contentType": "image/png",
            "url": "file://data/images/doris-yamamoto-brain-mri.png",
            "title": "Brain MRI DWI sequence"
        },
        "note": [{
            "text": "Brain MRI with DWI: Restricted diffusion involving the left middle cerebral artery territory, "
                    "including the left frontal operculum, insular cortex, and portions of the left temporal and parietal lobes. "
                    "Corresponding ADC map confirms acute infarction. MRA of the circle of Willis demonstrates occlusion of the "
                    "left M1 segment of the middle cerebral artery. No hemorrhagic transformation. No midline shift."
        }]
    })


# ============================================================================
# PATIENT 6: Baby Boy Torres
# ============================================================================
def generate_baby_torres():
    print("\n=== Generating Baby Boy Torres ===")
    pid = "patient-baby-torres"
    encounter_date = "2026-02-17"

    # --- Patient ---
    write_resource("Patient", {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "BT-2025-006"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Torres",
            "given": ["Baby Boy"]
        }],
        "gender": "male",
        "birthDate": "2025-11-19",
        "address": [{
            "use": "home",
            "line": ["321 Sunset Boulevard"],
            "city": "San Francisco",
            "state": "CA",
            "postalCode": "94110"
        }],
        "communication": [{
            "language": {
                "coding": [{"system": "urn:ietf:bcp:47", "code": "es", "display": "Spanish"}]
            },
            "preferred": True
        }, {
            "language": {
                "coding": [{"system": "urn:ietf:bcp:47", "code": "en", "display": "English"}]
            },
            "preferred": False
        }]
    })

    # --- Conditions ---
    conditions = [
        ("vsd", "30288003", "Ventricular septal defect", "Large perimembranous ventricular septal defect", "2025-11-19", "active", "confirmed"),
        ("chf", "42343007", "Congestive heart failure", "Congestive heart failure", "2026-01-10", "active", "confirmed"),
        ("ftt", "36813001", "Failure to thrive", "Failure to thrive", "2026-01-15", "active", "confirmed"),
    ]
    for suffix, snomed, display, text, onset, clinical, verification in conditions:
        write_resource("Condition", {
            "resourceType": "Condition",
            "id": f"condition-{pid.replace('patient-','')}-{suffix}",
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
            },
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": clinical}]
            },
            "verificationStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": verification}]
            },
            "category": [{
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item"}]
            }],
            "code": {
                "coding": [{"system": "http://snomed.info/sct", "code": snomed, "display": display}],
                "text": text
            },
            "subject": {"reference": f"Patient/{pid}", "display": "Baby Boy Torres"},
            "onsetDateTime": onset
        })

    # --- MedicationRequests ---
    # Furosemide 1mg/kg BID => baby is 4.8kg, so ~5mg (round to nearest available)
    write_resource("MedicationRequest", {
        "resourceType": "MedicationRequest",
        "id": f"medrx-{pid.replace('patient-','')}-furosemide",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "310429",
                "display": "Furosemide 10 MG/ML Oral Solution"
            }],
            "text": "Furosemide oral solution"
        },
        "subject": {"reference": f"Patient/{pid}", "display": "Baby Boy Torres"},
        "authoredOn": "2026-01-15",
        "dosageInstruction": [{
            "text": "Give 1 mg/kg (4.8 mg) by mouth twice daily",
            "timing": {"repeat": {"frequency": 2, "period": 1, "periodUnit": "d"}},
            "route": {
                "coding": [{"system": "http://snomed.info/sct", "code": "26643006", "display": "Oral route"}]
            },
            "doseAndRate": [{
                "doseQuantity": {"value": 4.8, "unit": "mg"},
                "rateRatio": {
                    "numerator": {"value": 1, "unit": "mg"},
                    "denominator": {"value": 1, "unit": "kg"}
                }
            }]
        }]
    })

    # Captopril 0.3mg/kg TID => 4.8 * 0.3 = 1.44 mg ~ 1.4 mg
    write_resource("MedicationRequest", {
        "resourceType": "MedicationRequest",
        "id": f"medrx-{pid.replace('patient-','')}-captopril",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "317571",
                "display": "Captopril 12.5 MG Oral Tablet"
            }],
            "text": "Captopril oral solution (compounded)"
        },
        "subject": {"reference": f"Patient/{pid}", "display": "Baby Boy Torres"},
        "authoredOn": "2026-01-15",
        "dosageInstruction": [{
            "text": "Give 0.3 mg/kg (1.4 mg) by mouth three times daily",
            "timing": {"repeat": {"frequency": 3, "period": 1, "periodUnit": "d"}},
            "route": {
                "coding": [{"system": "http://snomed.info/sct", "code": "26643006", "display": "Oral route"}]
            },
            "doseAndRate": [{
                "doseQuantity": {"value": 1.4, "unit": "mg"},
                "rateRatio": {
                    "numerator": {"value": 0.3, "unit": "mg"},
                    "denominator": {"value": 1, "unit": "kg"}
                }
            }]
        }]
    })

    # --- No AllergyIntolerance for Baby Torres ---

    # --- Observations: Vitals ---
    # Blood Pressure
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-bp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]
        }],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": 75, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                "valueQuantity": {"value": 50, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            }
        ]
    })

    # Heart Rate
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-hr-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]
        }],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 148, "unit": "/min", "system": "http://unitsofmeasure.org", "code": "/min"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]
        }],
        "referenceRange": [{"low": {"value": 100, "unit": "/min"}, "high": {"value": 160, "unit": "/min"}, "text": "Normal for 3-month-old infant"}]
    })

    # Respiratory Rate
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-rr-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]
        }],
        "code": {"coding": [{"system": "http://loinc.org", "code": "9279-1", "display": "Respiratory rate"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 52, "unit": "/min", "system": "http://unitsofmeasure.org", "code": "/min"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]
        }],
        "referenceRange": [{"low": {"value": 30, "unit": "/min"}, "high": {"value": 60, "unit": "/min"}, "text": "Normal for 3-month-old infant"}]
    })

    # Temperature
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-temp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]
        }],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 98.0, "unit": "degF", "system": "http://unitsofmeasure.org", "code": "[degF]"}
    })

    # Weight
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-weight-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]
        }],
        "code": {"coding": [{"system": "http://loinc.org", "code": "29463-7", "display": "Body weight"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {"value": 4.8, "unit": "kg", "system": "http://unitsofmeasure.org", "code": "kg"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "L", "display": "Low"}]
        }],
        "note": [{"text": "5th percentile for age. Expected weight for 3-month-old male is approximately 6.0-6.4 kg (50th percentile)."}]
    })

    # --- Observations: Labs ---
    # Creatinine
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-creatinine-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma"}],
            "text": "Creatinine"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T07:00:00Z",
        "valueQuantity": {"value": 0.4, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "H", "display": "High"}]
        }],
        "referenceRange": [{"low": {"value": 0.1, "unit": "mg/dL"}, "high": {"value": 0.3, "unit": "mg/dL"}, "text": "Normal for 3-month-old infant"}],
        "note": [{"text": "Elevated for age, likely reflecting reduced renal perfusion in setting of heart failure."}]
    })

    # Sodium
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-sodium-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2951-2", "display": "Sodium [Moles/volume] in Serum or Plasma"}],
            "text": "Sodium"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T07:00:00Z",
        "valueQuantity": {"value": 134, "unit": "mmol/L", "system": "http://unitsofmeasure.org", "code": "mmol/L"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "L", "display": "Low"}]
        }],
        "referenceRange": [{"low": {"value": 136, "unit": "mmol/L"}, "high": {"value": 145, "unit": "mmol/L"}}]
    })

    # Potassium
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-potassium-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2823-3", "display": "Potassium [Moles/volume] in Serum or Plasma"}],
            "text": "Potassium"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T07:00:00Z",
        "valueQuantity": {"value": 4.2, "unit": "mmol/L", "system": "http://unitsofmeasure.org", "code": "mmol/L"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]
        }],
        "referenceRange": [{"low": {"value": 3.5, "unit": "mmol/L"}, "high": {"value": 5.5, "unit": "mmol/L"}}]
    })

    # BNP
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-{pid.replace('patient-','')}-bnp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "30934-4", "display": "B-type natriuretic peptide [Mass/volume] in Serum or Plasma"}],
            "text": "BNP"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T07:00:00Z",
        "valueQuantity": {"value": 890, "unit": "pg/mL", "system": "http://unitsofmeasure.org", "code": "pg/mL"},
        "interpretation": [{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "HH", "display": "Critical high"}]
        }],
        "referenceRange": [{"high": {"value": 100, "unit": "pg/mL"}, "text": "Normal < 100 pg/mL"}],
        "note": [{"text": "Markedly elevated, consistent with significant volume overload and heart failure in setting of large VSD."}]
    })

    # --- Encounter (IMP for inpatient cardiology) ---
    write_resource("Encounter", {
        "resourceType": "Encounter",
        "id": f"encounter-{pid.replace('patient-','')}-{encounter_date}",
        "status": "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "IMP",
            "display": "inpatient encounter"
        },
        "type": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "183452005",
                "display": "Emergency hospital admission"
            }]
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "period": {
            "start": f"{encounter_date}T07:30:00Z"
        },
        "reasonCode": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "42343007",
                "display": "Congestive heart failure"
            }],
            "text": "Poor feeding, diaphoresis with feeds, poor weight gain in infant with known large VSD"
        }]
    })

    # --- DocumentReferences ---
    hpi_text = (
        "3-month-old Hispanic male infant, born at term via uncomplicated vaginal delivery with birth weight of 3.2 kg, "
        "presents to the pediatric cardiology service with worsening symptoms of congestive heart failure. The infant was "
        "diagnosed with a large perimembranous ventricular septal defect on echocardiogram performed at two weeks of life "
        "after a loud holosystolic murmur was detected during the newborn examination. Initially, the infant was monitored "
        "as an outpatient with the expectation that the VSD might decrease in size. However, over the past six weeks, the "
        "parents have reported progressively worsening feeding difficulty. The infant takes approximately 30 to 45 minutes "
        "to complete a 3-ounce bottle feeding and frequently stops to rest and catch his breath during feeds. The parents "
        "describe noticeable diaphoresis of the forehead and scalp during each feeding attempt. He has been increasingly "
        "irritable and fatigued, sleeping more during the day but waking frequently at night. His weight gain has been "
        "severely poor, currently at 4.8 kg, which places him at the 5th percentile for age, having crossed down from "
        "the 25th percentile at his one-month visit. The parents deny any cyanotic episodes, but note that he occasionally "
        "appears pale. Medical treatment was initiated at six weeks of life with furosemide 1 mg/kg twice daily and captopril "
        "0.3 mg/kg three times daily. Despite these medications, the parents report no significant improvement in symptoms "
        "over the past two weeks. The family is Spanish-speaking with an English-speaking older sibling assisting with "
        "interpretation. There are no known drug allergies. Family history is negative for congenital heart disease."
    )

    ros_text = (
        "Constitutional: Poor weight gain, increased somnolence, intermittent irritability, no fever per parents\n"
        "HEENT: No apparent eye discharge, no nasal congestion, no oral thrush noted by parents\n"
        "Cardiovascular: Known VSD with loud murmur; no reported cyanotic episodes; no reported edema of face "
        "or extremities; diaphoresis with feeds is prominent\n"
        "Respiratory: Tachypnea observed by parents especially during and after feeds; occasional subcostal "
        "retractions noted; no wheezing reported; no cough; no apneic episodes\n"
        "GI: Poor feeding with prolonged feeding times (30-45 minutes per 3 oz), frequent pauses during feeds, "
        "occasional spit-up but no projectile vomiting, stool pattern normal (3-4 soft stools per day)\n"
        "GU: Adequate wet diapers (5-6 per day, slightly decreased from prior), no blood in urine\n"
        "Skin: Parents report occasional pallor; no rashes; no jaundice; diaphoresis prominent during feeds\n"
        "Neurological: Age-appropriate social smile present, tracks faces, head control improving but behind "
        "expected milestones; no seizure activity observed"
    )

    pe_text = (
        "Vitals: BP 75/50 mmHg (right arm, appropriate cuff), HR 148 bpm, RR 52/min, Temp 98.0 F (axillary), "
        "SpO2 96% RA, Weight 4.8 kg (5th percentile), Length 58 cm (15th percentile), Head circumference 39 cm (25th percentile)\n\n"
        "General: Small-for-age infant, alert but appears thin and mildly fatigued. Mild subcostal retractions visible "
        "at rest. No cyanosis. Active and responsive to stimulation.\n\n"
        "HEENT: Anterior fontanelle open, flat, soft, approximately 2 x 2 cm. No bulging. Normocephalic. "
        "Red reflex present bilaterally. Tympanic membranes clear bilaterally. Nares patent. Oropharynx clear, "
        "palate intact, moist mucous membranes.\n\n"
        "Neck: Supple, no masses, no lymphadenopathy.\n\n"
        "Cardiovascular: Precordium hyperactive with visible and palpable left parasternal heave. Heart rate 148 bpm, "
        "regular rhythm. Grade IV/VI harsh holosystolic murmur heard best at the left lower sternal border, radiating "
        "across the precordium. S1 normal, S2 with narrowly split components. Diastolic rumble at the apex suggests "
        "significant left-to-right shunt with increased mitral valve flow. Capillary refill 3 seconds in all extremities. "
        "Femoral pulses 2+ bilaterally. No hepatomegaly suggesting right heart failure is not predominant.\n\n"
        "Respiratory: Tachypneic at rest with respiratory rate 52/min. Mild subcostal and intercostal retractions. "
        "Lungs clear to auscultation bilaterally with good air entry. No wheezes, crackles, or rhonchi. "
        "No grunting or nasal flaring.\n\n"
        "Abdomen: Soft, non-distended. Liver edge palpable 2 cm below the right costal margin, consistent with "
        "hepatomegaly from volume overload. Spleen not palpable. No masses. Active bowel sounds.\n\n"
        "Extremities: Warm but slightly mottled in the lower extremities. No clubbing. No peripheral edema. "
        "Capillary refill 3 seconds.\n\n"
        "Skin: Mildly pale. No rashes, birthmarks, or hemangiomas. Skin turgor normal. "
        "Diaphoresis noted during examination when infant became agitated.\n\n"
        "Neurological: Alert and interactive. Social smile present. Tracks faces across midline. Head control "
        "developing but slightly behind expected for age. Moro reflex present and symmetric. Grasp reflexes intact. "
        "Tone is mildly reduced but symmetric."
    )

    clinical_note_text = (
        "Assessment and Plan:\n\n"
        "3-month-old male infant with large perimembranous VSD presenting with worsening congestive heart failure "
        "manifested by failure to thrive (weight 4.8 kg, 5th percentile, crossing growth curves), tachypnea, "
        "diaphoresis with feeds, prolonged feeding times, and hepatomegaly. BNP markedly elevated at 890 pg/mL. "
        "Creatinine mildly elevated at 0.4 mg/dL for age, suggesting reduced renal perfusion.\n\n"
        "1. Large perimembranous VSD with hemodynamically significant left-to-right shunt: Echocardiogram performed "
        "today confirms a large perimembranous VSD measuring approximately 8mm with predominantly left-to-right "
        "shunting. Moderate left ventricular dilation is present with preserved systolic function. Given failure of "
        "medical management with persistent symptoms and failure to thrive, surgical consultation for VSD repair "
        "is recommended. Cardiac surgery team consulted and anticipates surgical repair within the next 1-2 weeks "
        "pending optimization.\n\n"
        "2. Congestive heart failure: Continue furosemide 1 mg/kg BID and captopril 0.3 mg/kg TID. Consider "
        "increasing furosemide to 1.5 mg/kg BID if no clinical improvement in 48 hours. Monitor strict intake "
        "and output. Daily weights. Fluid restrict to 130 mL/kg/day. Fortify feeds to 24 kcal/oz to maximize "
        "caloric intake per volume.\n\n"
        "3. Failure to thrive: Nutrition consult ordered. Consider nasogastric tube feeds if oral intake remains "
        "inadequate to support weight gain. Goal caloric intake 120-150 kcal/kg/day.\n\n"
        "4. Elevated creatinine: Monitor renal function daily while on diuretics and ACE inhibitor. Hold captopril "
        "if creatinine rises above 0.5 mg/dL. Monitor electrolytes twice daily.\n\n"
        "5. Admit to pediatric cardiology service for close monitoring and preoperative optimization. "
        "Parents counseled through interpreter regarding diagnosis, treatment plan, and surgical options. "
        "Social work consulted for family support."
    )

    for doc_type, loinc_code, loinc_display, suffix, text in [
        ("hpi", "10164-2", "History of Present illness", "hpi", hpi_text),
        ("ros", "10187-3", "Review of systems", "ros", ros_text),
        ("physical-exam", "29545-1", "Physical findings", "physical-exam", pe_text),
        ("clinical-note", "11506-3", "Progress note", "clinical-note", clinical_note_text),
    ]:
        write_resource("DocumentReference", {
            "resourceType": "DocumentReference",
            "id": f"doc-{pid.replace('patient-','')}-{suffix}",
            "status": "current",
            "type": {
                "coding": [{"system": "http://loinc.org", "code": loinc_code, "display": loinc_display}]
            },
            "category": [{
                "coding": [{
                    "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                    "code": "clinical-note",
                    "display": "Clinical Note"
                }]
            }],
            "subject": {"reference": f"Patient/{pid}"},
            "date": f"{encounter_date}T09:00:00Z",
            "author": [{"display": "Dr. Ana Gutierrez, MD - Pediatric Cardiology"}],
            "content": [{
                "attachment": {
                    "contentType": "text/plain",
                    "data": b64(text)
                }
            }]
        })

    # --- Media: Echocardiogram ---
    write_resource("Media", {
        "resourceType": "Media",
        "id": f"media-{pid.replace('patient-','')}-echo",
        "status": "completed",
        "type": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/media-type", "code": "image", "display": "Image"}]
        },
        "modality": {
            "coding": [{
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "code": "US",
                "display": "Ultrasound"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "createdDateTime": f"{encounter_date}T08:30:00Z",
        "bodySite": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "80891009",
                "display": "Heart structure"
            }]
        },
        "content": {
            "contentType": "image/png",
            "url": "file://data/images/baby-torres-echo.png",
            "title": "Transthoracic echocardiogram - parasternal long axis"
        },
        "note": [{
            "text": "Transthoracic echocardiogram: Large perimembranous ventricular septal defect measuring "
                    "approximately 8mm in diameter with predominantly left-to-right shunting on color Doppler. "
                    "Left ventricular internal dimension in diastole is moderately dilated at 28mm (z-score +3.2). "
                    "Left ventricular systolic function is preserved with shortening fraction 35%. Left atrium mildly "
                    "dilated. Mitral valve inflow velocity increased suggesting high flow state. No aortic valve "
                    "prolapse. No evidence of pulmonary hypertension; estimated PA systolic pressure 30 mmHg by "
                    "tricuspid regurgitation jet. Normal aortic arch anatomy, no coarctation."
        }]
    })


# ============================================================================
# Main
# ============================================================================
def main():
    print(f"Output directory: {OUTPUT_DIR}")
    for subdir in ["Patient", "Condition", "MedicationRequest", "AllergyIntolerance",
                    "Observation", "Encounter", "DocumentReference", "Media"]:
        (OUTPUT_DIR / subdir).mkdir(parents=True, exist_ok=True)

    generate_robert_thompson()
    generate_doris_yamamoto()
    generate_baby_torres()

    # Summary
    print("\n=== Summary ===")
    total = 0
    for subdir in sorted(os.listdir(OUTPUT_DIR)):
        subdir_path = OUTPUT_DIR / subdir
        if subdir_path.is_dir():
            count = len([f for f in os.listdir(subdir_path) if f.endswith(".json")])
            if count > 0:
                print(f"  {subdir}/: {count} files")
                total += count
    print(f"\n  Total files generated: {total}")


if __name__ == "__main__":
    main()
