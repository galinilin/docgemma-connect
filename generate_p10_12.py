#!/usr/bin/env python3
"""Generate FHIR R4-compliant JSON files for patients 10-12:
  - Marcus Williams (patient-marcus-williams)
  - Patricia Johnson (patient-patricia-johnson)
  - David Kim (patient-david-kim)
"""

import json
import base64
import os
from pathlib import Path

FHIR_DIR = Path(__file__).parent / "data" / "fhir"


def b64(text: str) -> str:
    """Base64-encode a string."""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def write_resource(resource_type: str, resource: dict):
    """Write a FHIR resource JSON file."""
    out_dir = FHIR_DIR / resource_type
    out_dir.mkdir(parents=True, exist_ok=True)
    filepath = out_dir / f"{resource['id']}.json"
    with open(filepath, "w") as f:
        json.dump(resource, f, indent=2)
    print(f"  Created {filepath.relative_to(FHIR_DIR)}")


# ============================================================================
# PATIENT 10: Marcus Williams
# ============================================================================
def generate_marcus_williams():
    pid = "patient-marcus-williams"
    display = "Marcus Williams"
    encounter_date = "2026-02-14"
    encounter_id = f"encounter-marcus-williams-{encounter_date}"
    print(f"\n=== Generating {display} ===")

    # --- Patient ---
    write_resource("Patient", {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "MW-2026-010"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Williams",
            "given": ["Marcus", "Dwayne"]
        }],
        "gender": "male",
        "birthDate": "2007-05-22",
        "address": [{
            "use": "home",
            "line": ["456 Campus Drive, Apt 12B"],
            "city": "Durham",
            "state": "NC",
            "postalCode": "27708"
        }],
        "maritalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                "code": "S",
                "display": "Never Married"
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
        "id": "condition-marcus-williams-hcm",
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
        },
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "45227007",
                "display": "Hypertrophic cardiomyopathy"
            }],
            "text": "Hypertrophic Cardiomyopathy (Obstructive)"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "onsetDateTime": "2026-01-28"
    })

    write_resource("Condition", {
        "resourceType": "Condition",
        "id": "condition-marcus-williams-fh-scd",
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
        },
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "134439009",
                "display": "Family history of sudden cardiac death"
            }],
            "text": "Family History of Sudden Cardiac Death"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "note": [{
            "text": "Maternal uncle died suddenly at age 35 while playing tennis."
        }]
    })

    # --- MedicationRequest ---
    write_resource("MedicationRequest", {
        "resourceType": "MedicationRequest",
        "id": "medrx-marcus-williams-metoprolol",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "866924",
                "display": "Metoprolol Tartrate 50 MG Oral Tablet"
            }],
            "text": "Metoprolol 50mg"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "authoredOn": "2026-02-14",
        "dosageInstruction": [{
            "text": "Take 1 tablet by mouth twice daily",
            "timing": {
                "repeat": {
                    "frequency": 2,
                    "period": 1,
                    "periodUnit": "d"
                }
            },
            "route": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "26643006",
                    "display": "Oral route"
                }]
            },
            "doseAndRate": [{
                "doseQuantity": {
                    "value": 50,
                    "unit": "mg"
                }
            }]
        }]
    })

    # --- No AllergyIntolerance for Marcus ---

    # --- Observations: Vitals ---
    # Blood Pressure
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-marcus-williams-bp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T10:00:00Z",
        "component": [
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8480-6",
                        "display": "Systolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": 118,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            },
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8462-4",
                        "display": "Diastolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": 72,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            }
        ]
    })

    # Heart Rate
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-marcus-williams-hr-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "8867-4",
                "display": "Heart rate"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T10:00:00Z",
        "valueQuantity": {
            "value": 58,
            "unit": "/min",
            "system": "http://unitsofmeasure.org",
            "code": "/min"
        }
    })

    # Temperature
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-marcus-williams-temp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "8310-5",
                "display": "Body temperature"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T10:00:00Z",
        "valueQuantity": {
            "value": 98.4,
            "unit": "degF",
            "system": "http://unitsofmeasure.org",
            "code": "[degF]"
        }
    })

    # --- Observations: Labs ---
    # BNP
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-marcus-williams-bnp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "30934-4",
                "display": "B-type natriuretic peptide [Mass/volume] in Serum or Plasma"
            }],
            "text": "BNP"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:30:00Z",
        "valueQuantity": {
            "value": 45,
            "unit": "pg/mL",
            "system": "http://unitsofmeasure.org",
            "code": "pg/mL"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "N",
                "display": "Normal"
            }]
        }],
        "referenceRange": [{
            "high": {"value": 100, "unit": "pg/mL"}
        }]
    })

    # Troponin
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-marcus-williams-troponin-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "10839-9",
                "display": "Troponin I.cardiac [Mass/volume] in Serum or Plasma"
            }],
            "text": "Troponin I"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:30:00Z",
        "valueQuantity": {
            "value": 0.01,
            "unit": "ng/mL",
            "system": "http://unitsofmeasure.org",
            "code": "ng/mL",
            "comparator": "<"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "N",
                "display": "Normal"
            }]
        }],
        "referenceRange": [{
            "high": {"value": 0.04, "unit": "ng/mL"}
        }]
    })

    # --- Encounter ---
    write_resource("Encounter", {
        "resourceType": "Encounter",
        "id": encounter_id,
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
        "subject": {
            "reference": f"Patient/{pid}"
        },
        "period": {
            "start": f"{encounter_date}T09:30:00Z",
            "end": f"{encounter_date}T10:30:00Z"
        },
        "reasonCode": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "45227007",
                "display": "Hypertrophic cardiomyopathy"
            }],
            "text": "Sports medicine evaluation - HCM in college athlete"
        }]
    })

    # --- DocumentReferences ---
    hpi_text = (
        "Marcus Williams is a 19-year-old African American male and Division I college basketball player "
        "who presents for sports medicine follow-up after a pre-participation physical examination revealed "
        "a systolic murmur that increased with Valsalva maneuver. Subsequent echocardiography demonstrated "
        "asymmetric septal hypertrophy measuring 25mm with systolic anterior motion of the mitral valve, "
        "consistent with hypertrophic obstructive cardiomyopathy. Cardiac MRI confirmed these findings and "
        "showed no evidence of late gadolinium enhancement, suggesting absence of myocardial fibrosis at "
        "this time. The patient reports no prior episodes of syncope, presyncope, or exertional chest pain. "
        "He denies palpitations and dyspnea disproportionate to exertion during practice. He has been "
        "playing competitive basketball since age 12 without any prior cardiac evaluation beyond routine "
        "physicals. Family history is significant for an uncle on his mother's side who died suddenly at "
        "age 35 while playing recreational tennis; an autopsy was reportedly performed but the family does "
        "not have records. Metoprolol 50mg twice daily was initiated two weeks ago and he reports good "
        "tolerance with mild fatigue during the first few days that has since resolved. He is understandably "
        "anxious about the implications for his athletic career and eligibility."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-marcus-williams-hpi",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "10164-2",
                "display": "History of Present illness"
            }]
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
        "author": [{"display": "Dr. Michael Torres, MD - Sports Cardiology"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(hpi_text)
            }
        }]
    })

    ros_text = (
        "Constitutional: No fever, no unintentional weight loss, mild fatigue resolving since starting metoprolol. "
        "Reports adequate energy for daily activities but has not returned to competitive play.\n"
        "HEENT: No vision changes, no hearing loss, no sore throat.\n"
        "Cardiovascular: No chest pain at rest or with exertion, no palpitations, no syncope or presyncope, "
        "no orthopnea, no PND, no lower extremity edema. Denies racing heartbeat or skipped beats.\n"
        "Respiratory: No cough, no dyspnea at rest, no wheezing. No exertional dyspnea beyond expected "
        "level for conditioning.\n"
        "GI: No nausea, no vomiting, no abdominal pain. Normal appetite.\n"
        "GU: No dysuria, no frequency, no hematuria.\n"
        "Musculoskeletal: No joint pain, no muscle weakness. Full range of motion all joints.\n"
        "Neurological: No headache, no dizziness, no numbness or tingling.\n"
        "Psychiatric: Reports anxiety regarding diagnosis and athletic career implications. "
        "Sleeping 6-7 hours nightly, decreased from baseline of 8 hours."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-marcus-williams-ros",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "10187-3",
                "display": "Review of systems"
            }]
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
        "author": [{"display": "Dr. Michael Torres, MD - Sports Cardiology"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(ros_text)
            }
        }]
    })

    pe_text = (
        "Vitals: BP 118/72 mmHg, HR 58 bpm regular, RR 14, Temp 98.4F, SpO2 99% on RA\n\n"
        "General: Well-developed, muscular 19-year-old male in no acute distress. Athletic build, "
        "appears well-nourished and well-hydrated. Height 6'4\", Weight 205 lbs.\n\n"
        "HEENT: Normocephalic, atraumatic. PERRLA. Oropharynx clear without erythema or exudate. "
        "Moist mucous membranes.\n\n"
        "Neck: Supple, no lymphadenopathy. No thyromegaly. JVP not elevated. Carotid upstroke brisk "
        "with bifid quality (spike-and-dome pattern). No carotid bruits.\n\n"
        "Cardiovascular: Regular rate and rhythm. Normal S1, physiologically split S2. Grade III/VI "
        "harsh crescendo-decrescendo systolic murmur best heard at the left lower sternal border, "
        "increasing with Valsalva maneuver and standing, decreasing with squatting and passive leg "
        "elevation. No diastolic murmur. PMI laterally displaced and sustained. No S3 or S4 gallop. "
        "No peripheral edema.\n\n"
        "Respiratory: Clear to auscultation bilaterally. No wheezes, rales, or rhonchi. Good air "
        "movement throughout.\n\n"
        "Abdomen: Soft, non-tender, non-distended. Normal bowel sounds. No hepatosplenomegaly.\n\n"
        "Extremities: Warm, well-perfused. No cyanosis, clubbing, or edema. Peripheral pulses 2+ and "
        "symmetric bilaterally.\n\n"
        "Musculoskeletal: Full range of motion all major joints. No joint effusions. Normal muscle "
        "bulk and tone.\n\n"
        "Neurological: Alert and oriented x4. CN II-XII intact. Motor strength 5/5 throughout. "
        "Reflexes 2+ and symmetric."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-marcus-williams-physical-exam",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "29545-1",
                "display": "Physical findings"
            }]
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
        "author": [{"display": "Dr. Michael Torres, MD - Sports Cardiology"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(pe_text)
            }
        }]
    })

    clinical_note_text = (
        "ASSESSMENT AND PLAN:\n\n"
        "19-year-old male Division I basketball player with newly diagnosed hypertrophic obstructive "
        "cardiomyopathy identified on pre-participation screening. Cardiac MRI demonstrates 25mm "
        "asymmetric septal hypertrophy with SAM of the mitral valve and no late gadolinium enhancement, "
        "which is a favorable prognostic indicator. Family history is concerning with uncle's sudden death "
        "at age 35 during physical activity. Current SCD risk assessment using the HCM Risk-SCD calculator "
        "is pending completion with exercise stress testing results. Metoprolol 50mg BID initiated two "
        "weeks ago with good tolerance and resting heart rate of 58 bpm.\n\n"
        "Plan:\n"
        "1. Continue metoprolol 50mg BID. Monitor for symptomatic bradycardia.\n"
        "2. Exercise restriction from competitive athletics per ACC/AHA guidelines pending further risk "
        "stratification. May engage in low-intensity recreational activities with heart rate monitoring.\n"
        "3. Order genetic testing for sarcomeric gene panel. Recommend first-degree relatives undergo "
        "screening echocardiography.\n"
        "4. Cardiopulmonary exercise testing to assess functional capacity and arrhythmia risk.\n"
        "5. 48-hour Holter monitor to evaluate for NSVT.\n"
        "6. Referral to genetic counselor for family counseling.\n"
        "7. Sports psychology referral for adjustment to diagnosis and career implications.\n"
        "8. Follow-up in 4 weeks with test results."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-marcus-williams-clinical-note",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "11506-3",
                "display": "Progress note"
            }]
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
        "author": [{"display": "Dr. Michael Torres, MD - Sports Cardiology"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(clinical_note_text)
            }
        }]
    })

    # --- Media: Cardiac MRI ---
    write_resource("Media", {
        "resourceType": "Media",
        "id": "media-marcus-williams-cardiac-mri",
        "status": "completed",
        "type": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/media-type",
                "code": "image",
                "display": "Image"
            }]
        },
        "modality": {
            "coding": [{
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "code": "MR",
                "display": "Magnetic Resonance"
            }]
        },
        "subject": {
            "reference": f"Patient/{pid}"
        },
        "createdDateTime": f"{encounter_date}T08:00:00Z",
        "bodySite": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "80891009",
                "display": "Heart structure"
            }]
        },
        "content": {
            "contentType": "image/dicom",
            "url": "file://data/images/marcus-williams-cardiac-mri.dcm",
            "title": "Cardiac MRI - Short axis and 4-chamber views"
        },
        "note": [{
            "text": "Cardiac MRI demonstrates asymmetric septal hypertrophy measuring 25mm at the basal septum. Systolic anterior motion (SAM) of the mitral valve leaflet is present with associated dynamic LVOT obstruction. No late gadolinium enhancement identified, suggesting absence of myocardial fibrosis. Left ventricular ejection fraction 68%. No pericardial effusion."
        }]
    })


# ============================================================================
# PATIENT 11: Patricia Johnson
# ============================================================================
def generate_patricia_johnson():
    pid = "patient-patricia-johnson"
    display = "Patricia Johnson"
    encounter_date = "2026-02-16"
    encounter_id = f"encounter-patricia-johnson-{encounter_date}"
    print(f"\n=== Generating {display} ===")

    # --- Patient ---
    write_resource("Patient", {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "PJ-2026-011"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Johnson",
            "given": ["Patricia", "Ann"]
        }],
        "gender": "female",
        "birthDate": "1959-08-11",
        "address": [{
            "use": "home",
            "line": ["892 Maple Lane"],
            "city": "Richmond",
            "state": "VA",
            "postalCode": "23220"
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
        "id": "condition-patricia-johnson-pe",
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
        },
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "encounter-diagnosis"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "59282003",
                "display": "Pulmonary embolism"
            }],
            "text": "Saddle Pulmonary Embolism (Acute, Massive)"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "onsetDateTime": "2026-02-16"
    })

    write_resource("Condition", {
        "resourceType": "Condition",
        "id": "condition-patricia-johnson-postop",
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
        },
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "encounter-diagnosis"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "397945004",
                "display": "Post-operative state"
            }],
            "text": "Post-operative Day 2 - Right Hemicolectomy"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "onsetDateTime": "2026-02-14",
        "note": [{
            "text": "Right hemicolectomy performed 2026-02-14 for stage II colon adenocarcinoma. POD2 complicated by massive PE."
        }]
    })

    write_resource("Condition", {
        "resourceType": "Condition",
        "id": "condition-patricia-johnson-colon-ca",
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
        },
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "363406005",
                "display": "Malignant tumor of colon"
            }],
            "text": "Colon Adenocarcinoma, Stage II"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "onsetDateTime": "2026-01-10"
    })

    # --- MedicationRequests ---
    write_resource("MedicationRequest", {
        "resourceType": "MedicationRequest",
        "id": "medrx-patricia-johnson-heparin",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "235473",
                "display": "Heparin"
            }],
            "text": "Heparin Drip (Unfractionated)"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "authoredOn": "2026-02-16",
        "dosageInstruction": [{
            "text": "Continuous IV infusion per PE protocol, titrate to aPTT 60-80 seconds",
            "route": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "47625008",
                    "display": "Intravenous route"
                }]
            }
        }]
    })

    write_resource("MedicationRequest", {
        "resourceType": "MedicationRequest",
        "id": "medrx-patricia-johnson-norepinephrine",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "7512",
                "display": "Norepinephrine"
            }],
            "text": "Norepinephrine 8 mcg/min"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "authoredOn": "2026-02-16",
        "dosageInstruction": [{
            "text": "8 mcg/min continuous IV infusion, titrate to MAP > 65 mmHg",
            "route": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "47625008",
                    "display": "Intravenous route"
                }]
            },
            "doseAndRate": [{
                "doseQuantity": {
                    "value": 8,
                    "unit": "mcg/min"
                }
            }]
        }]
    })

    # --- AllergyIntolerance ---
    write_resource("AllergyIntolerance", {
        "resourceType": "AllergyIntolerance",
        "id": "allergy-patricia-johnson-morphine",
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                "code": "active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                "code": "confirmed"
            }]
        },
        "type": "intolerance",
        "category": ["medication"],
        "criticality": "low",
        "code": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "7052",
                "display": "Morphine"
            }],
            "text": "Morphine"
        },
        "patient": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "recordedDate": "2020-03-15",
        "reaction": [{
            "manifestation": [{
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "40917007",
                    "display": "Confusion"
                }],
                "text": "Confusion and agitation"
            }],
            "severity": "moderate"
        }]
    })

    # --- Observations: Vitals ---
    # Blood Pressure
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-patricia-johnson-bp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:15:00Z",
        "component": [
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8480-6",
                        "display": "Systolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": 88,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            },
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8462-4",
                        "display": "Diastolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": 54,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            }
        ],
        "note": [{"text": "On norepinephrine 8 mcg/min"}]
    })

    # Heart Rate
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-patricia-johnson-hr-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "8867-4",
                "display": "Heart rate"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:15:00Z",
        "valueQuantity": {
            "value": 122,
            "unit": "/min",
            "system": "http://unitsofmeasure.org",
            "code": "/min"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "H",
                "display": "High"
            }]
        }]
    })

    # Respiratory Rate
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-patricia-johnson-rr-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "9279-1",
                "display": "Respiratory rate"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:15:00Z",
        "valueQuantity": {
            "value": 28,
            "unit": "/min",
            "system": "http://unitsofmeasure.org",
            "code": "/min"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "H",
                "display": "High"
            }]
        }]
    })

    # SpO2
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-patricia-johnson-spo2-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "2708-6",
                "display": "Oxygen saturation in Arterial blood"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:15:00Z",
        "valueQuantity": {
            "value": 88,
            "unit": "%",
            "system": "http://unitsofmeasure.org",
            "code": "%"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "L",
                "display": "Low"
            }]
        }],
        "note": [{"text": "On 15L non-rebreather mask"}]
    })

    # Temperature
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-patricia-johnson-temp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "8310-5",
                "display": "Body temperature"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:15:00Z",
        "valueQuantity": {
            "value": 98.8,
            "unit": "degF",
            "system": "http://unitsofmeasure.org",
            "code": "[degF]"
        }
    })

    # --- Observations: Labs ---
    # Troponin
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-patricia-johnson-troponin-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "10839-9",
                "display": "Troponin I.cardiac [Mass/volume] in Serum or Plasma"
            }],
            "text": "Troponin I"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:00:00Z",
        "valueQuantity": {
            "value": 0.48,
            "unit": "ng/mL",
            "system": "http://unitsofmeasure.org",
            "code": "ng/mL"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "H",
                "display": "High"
            }]
        }],
        "referenceRange": [{
            "high": {"value": 0.04, "unit": "ng/mL"}
        }]
    })

    # BNP
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-patricia-johnson-bnp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "30934-4",
                "display": "B-type natriuretic peptide [Mass/volume] in Serum or Plasma"
            }],
            "text": "BNP"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:00:00Z",
        "valueQuantity": {
            "value": 1240,
            "unit": "pg/mL",
            "system": "http://unitsofmeasure.org",
            "code": "pg/mL"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "HH",
                "display": "Critical high"
            }]
        }],
        "referenceRange": [{
            "high": {"value": 100, "unit": "pg/mL"}
        }]
    })

    # D-dimer
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-patricia-johnson-ddimer-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "48066-5",
                "display": "Fibrin D-dimer DDU [Mass/volume] in Platelet poor plasma"
            }],
            "text": "D-dimer"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:00:00Z",
        "valueQuantity": {
            "value": 5000,
            "unit": "ng/mL",
            "system": "http://unitsofmeasure.org",
            "code": "ng/mL",
            "comparator": ">"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "HH",
                "display": "Critical high"
            }]
        }],
        "referenceRange": [{
            "high": {"value": 500, "unit": "ng/mL"}
        }]
    })

    # Lactate
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-patricia-johnson-lactate-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "2524-7",
                "display": "Lactate [Moles/volume] in Serum or Plasma"
            }],
            "text": "Lactate"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T06:00:00Z",
        "valueQuantity": {
            "value": 3.8,
            "unit": "mmol/L",
            "system": "http://unitsofmeasure.org",
            "code": "mmol/L"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "H",
                "display": "High"
            }]
        }],
        "referenceRange": [{
            "high": {"value": 2.0, "unit": "mmol/L"}
        }]
    })

    # --- Encounter ---
    write_resource("Encounter", {
        "resourceType": "Encounter",
        "id": encounter_id,
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
        "subject": {
            "reference": f"Patient/{pid}"
        },
        "period": {
            "start": f"{encounter_date}T05:45:00Z"
        },
        "reasonCode": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "59282003",
                "display": "Pulmonary embolism"
            }],
            "text": "Rapid response - acute dyspnea and hypotension, POD2 from right hemicolectomy"
        }],
        "location": [{
            "location": {
                "display": "Medical ICU, Bed 4"
            },
            "status": "active"
        }]
    })

    # --- DocumentReferences ---
    hpi_text = (
        "Patricia Johnson is a 67-year-old Caucasian woman who is post-operative day 2 from an open right "
        "hemicolectomy performed for stage II colon adenocarcinoma. She was found in acute respiratory distress "
        "by the nursing staff at approximately 0530 this morning during routine vital sign assessment. The "
        "patient was noted to be tachypneic, hypotensive, and desaturating. A rapid response was called "
        "immediately. On initial assessment, the patient was alert but appeared anxious and diaphoretic with "
        "labored breathing. Blood pressure was 82/48 mmHg, heart rate 128 bpm, respiratory rate 32, and SpO2 "
        "84% on 2L nasal cannula. She was rapidly placed on 15L non-rebreather mask with improvement to 88%. "
        "She reported acute onset of severe dyspnea and right-sided pleuritic chest pain that began approximately "
        "30 minutes prior. She denied calf pain but had been largely immobile since surgery. Her surgical course "
        "had been uncomplicated until this event with good pain control, tolerating clear liquids, and appropriate "
        "surgical drain output. DVT prophylaxis with subcutaneous heparin 5000 units q8h had been ordered but "
        "the evening dose was held per surgical team due to concern for post-operative bleeding. CT angiography "
        "of the chest was obtained emergently and demonstrated a saddle pulmonary embolism extending into bilateral "
        "main pulmonary arteries with significant right ventricular dilation and interventricular septal bowing, "
        "consistent with massive PE with right heart strain."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-patricia-johnson-hpi",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "10164-2",
                "display": "History of Present illness"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                "code": "clinical-note",
                "display": "Clinical Note"
            }]
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "date": f"{encounter_date}T06:30:00Z",
        "author": [{"display": "Dr. Rachel Kim, MD - Pulmonary/Critical Care"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(hpi_text)
            }
        }]
    })

    ros_text = (
        "Constitutional: Acute onset diaphoresis, no fever, no rigors. Feels weak and lightheaded.\n"
        "HEENT: No vision changes, no hearing loss.\n"
        "Cardiovascular: Acute pleuritic right-sided chest pain. Palpitations present. No prior history of "
        "DVT or PE. No lower extremity swelling noted. No prior cardiac history.\n"
        "Respiratory: Severe acute dyspnea at rest. No cough. No hemoptysis. No wheezing. "
        "Unable to speak in full sentences.\n"
        "GI: Mild nausea, no vomiting. Tolerating sips of clear liquids. Surgical drain output "
        "serosanguineous 120mL over last 12 hours. No abdominal distension.\n"
        "GU: Foley catheter in place, urine output 15mL/hr for last 2 hours (decreased from 40mL/hr).\n"
        "Musculoskeletal: No calf pain or swelling. Limited mobility since surgery.\n"
        "Neurological: Alert but anxious. No focal deficits. No confusion (baseline orientation intact).\n"
        "Skin: Diaphoretic. Surgical incision clean, dry, intact. No signs of wound infection."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-patricia-johnson-ros",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "10187-3",
                "display": "Review of systems"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                "code": "clinical-note",
                "display": "Clinical Note"
            }]
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "date": f"{encounter_date}T06:30:00Z",
        "author": [{"display": "Dr. Rachel Kim, MD - Pulmonary/Critical Care"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(ros_text)
            }
        }]
    })

    pe_text = (
        "Vitals: BP 88/54 mmHg (on norepinephrine 8 mcg/min), HR 122 bpm sinus tachycardia, "
        "RR 28, Temp 98.8F, SpO2 88% on 15L NRB\n\n"
        "General: 67-year-old woman in acute respiratory distress. Diaphoretic, anxious, speaking in "
        "short phrases only. Appears acutely ill.\n\n"
        "HEENT: Normocephalic, atraumatic. Pupils equal and reactive. Mucous membranes dry. "
        "No cyanosis of lips noted.\n\n"
        "Neck: Supple. Jugular venous distension to the angle of the jaw with patient at 45 degrees. "
        "No lymphadenopathy.\n\n"
        "Cardiovascular: Tachycardic, regular rhythm. Loud P2 component. Right ventricular heave palpable "
        "at left parasternal border. No murmurs appreciated. No pericardial rub. Peripheral pulses thready "
        "but palpable. Cool extremities with delayed capillary refill (4 seconds). No pedal edema.\n\n"
        "Respiratory: Tachypneic with accessory muscle use. Clear to auscultation bilaterally without "
        "wheezes, rales, or rhonchi. No focal consolidation. Equal breath sounds. No pleural rub.\n\n"
        "Abdomen: Right-sided surgical incision with staples, clean, dry, and intact. JP drain in place "
        "with serosanguineous output. Soft, mildly tender along incision. Non-distended. Bowel sounds "
        "present but hypoactive.\n\n"
        "Extremities: No calf tenderness. No Homans sign. No lower extremity edema or erythema. "
        "Cool and mottled distally.\n\n"
        "Neurological: Alert and oriented x4. Anxious but appropriate. No focal deficits. "
        "GCS 15. Moving all extremities.\n\n"
        "Skin: Diaphoretic. Pale. Mottled distal extremities. No rash. Surgical site without "
        "erythema or drainage."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-patricia-johnson-physical-exam",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "29545-1",
                "display": "Physical findings"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                "code": "clinical-note",
                "display": "Clinical Note"
            }]
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "date": f"{encounter_date}T06:30:00Z",
        "author": [{"display": "Dr. Rachel Kim, MD - Pulmonary/Critical Care"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(pe_text)
            }
        }]
    })

    clinical_note_text = (
        "ASSESSMENT AND PLAN:\n\n"
        "67-year-old woman POD2 from right hemicolectomy for stage II colon adenocarcinoma now presenting "
        "with massive saddle pulmonary embolism with hemodynamic compromise and right ventricular strain. "
        "This is a life-threatening emergency requiring aggressive resuscitation.\n\n"
        "1. MASSIVE PULMONARY EMBOLISM WITH OBSTRUCTIVE SHOCK:\n"
        "   - Initiated systemic anticoagulation with unfractionated heparin drip per PE protocol\n"
        "   - Hemodynamic support with norepinephrine, currently at 8 mcg/min targeting MAP > 65\n"
        "   - Strongly considering systemic thrombolysis vs catheter-directed therapy given hemodynamic "
        "instability; however, POD2 status significantly increases surgical bleeding risk\n"
        "   - Emergent consultation to interventional radiology for catheter-directed therapy as preferred "
        "approach given recent surgery\n"
        "   - Cardiothoracic surgery aware for potential surgical embolectomy if catheter approach fails\n"
        "   - Serial troponin and BNP monitoring q6h\n"
        "   - Bedside echocardiography to assess RV function trending\n\n"
        "2. RESPIRATORY FAILURE:\n"
        "   - Currently on 15L NRB with SpO2 88%\n"
        "   - Prepare for intubation if continued deterioration\n"
        "   - Avoid excessive PEEP given RV failure\n\n"
        "3. POST-OPERATIVE STATUS:\n"
        "   - Surgical team aware. All home medications held.\n"
        "   - Monitor surgical site for bleeding given anticoagulation\n"
        "   - Morphine allergy documented - use hydromorphone for pain management\n"
        "   - NPO given hemodynamic instability and potential for procedural intervention\n\n"
        "4. CODE STATUS: Full code, confirmed with patient."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-patricia-johnson-clinical-note",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "11506-3",
                "display": "Progress note"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                "code": "clinical-note",
                "display": "Clinical Note"
            }]
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "date": f"{encounter_date}T06:30:00Z",
        "author": [{"display": "Dr. Rachel Kim, MD - Pulmonary/Critical Care"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(clinical_note_text)
            }
        }]
    })

    # --- Media: CXR ---
    write_resource("Media", {
        "resourceType": "Media",
        "id": "media-patricia-johnson-cxr",
        "status": "completed",
        "type": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/media-type",
                "code": "image",
                "display": "Image"
            }]
        },
        "modality": {
            "coding": [{
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "code": "CR",
                "display": "Computed Radiography"
            }]
        },
        "subject": {
            "reference": f"Patient/{pid}"
        },
        "createdDateTime": f"{encounter_date}T06:00:00Z",
        "bodySite": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "51185008",
                "display": "Thoracic structure"
            }]
        },
        "content": {
            "contentType": "image/png",
            "url": "file://data/images/patricia-johnson-cxr.png",
            "title": "Chest X-ray AP portable"
        },
        "note": [{
            "text": "Portable AP chest radiograph. Lungs are clear bilaterally without focal consolidation, effusion, or pneumothorax. Heart size is at the upper limits of normal. Median sternotomy wires are not present. Right-sided surgical drain in appropriate position. No free air under diaphragm."
        }]
    })

    # --- Media: CT Chest ---
    write_resource("Media", {
        "resourceType": "Media",
        "id": "media-patricia-johnson-ct-chest",
        "status": "completed",
        "type": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/media-type",
                "code": "image",
                "display": "Image"
            }]
        },
        "modality": {
            "coding": [{
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "code": "CT",
                "display": "Computed Tomography"
            }]
        },
        "subject": {
            "reference": f"Patient/{pid}"
        },
        "createdDateTime": f"{encounter_date}T06:10:00Z",
        "bodySite": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "51185008",
                "display": "Thoracic structure"
            }]
        },
        "content": {
            "contentType": "image/dicom",
            "url": "file://data/images/patricia-johnson-ct-chest.dcm",
            "title": "CT Chest with contrast - PE protocol"
        },
        "note": [{
            "text": "CT pulmonary angiography demonstrates a large saddle embolus at the main pulmonary artery bifurcation with extension into bilateral main, lobar, and segmental pulmonary arteries. Significant right ventricular dilation with RV/LV ratio of 1.6 (normal <1.0). Interventricular septum bows toward the left ventricle consistent with right heart strain. Bilateral reflux of contrast into hepatic veins indicating elevated right atrial pressure. No pneumothorax. No pleural effusion. No parenchymal consolidation. Post-surgical changes in the right abdomen with surgical drain in place."
        }]
    })


# ============================================================================
# PATIENT 12: David Kim
# ============================================================================
def generate_david_kim():
    pid = "patient-david-kim"
    display = "David Kim"
    encounter_date = "2026-02-17"
    encounter_id = f"encounter-david-kim-{encounter_date}"
    print(f"\n=== Generating {display} ===")

    # --- Patient ---
    write_resource("Patient", {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "DK-2026-012"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Kim",
            "given": ["David", "Sung-Ho"]
        }],
        "gender": "male",
        "birthDate": "1970-01-15",
        "address": [{
            "use": "home",
            "line": ["2100 Pacific Heights Blvd, Suite 1402"],
            "city": "San Jose",
            "state": "CA",
            "postalCode": "95134"
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
        "id": "condition-david-kim-nsclc",
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
        },
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "254637007",
                "display": "Non-small cell lung cancer"
            }],
            "text": "Stage IIIA Non-Small Cell Lung Cancer (Adenocarcinoma, EGFR Exon 19 Deletion, PD-L1 80%)"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "onsetDateTime": "2026-01-20",
        "note": [{
            "text": "Right upper lobe adenocarcinoma, 4.2cm mass with mediastinal lymphadenopathy. EGFR exon 19 deletion positive. PD-L1 TPS 80%. Former 30 pack-year smoker, quit 5 years ago. ECOG performance status 1."
        }]
    })

    write_resource("Condition", {
        "resourceType": "Condition",
        "id": "condition-david-kim-diabetes",
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
        },
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "44054006",
                "display": "Type 2 diabetes mellitus"
            }],
            "text": "Type 2 Diabetes Mellitus"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "onsetDateTime": "2018-06-01"
    })

    write_resource("Condition", {
        "resourceType": "Condition",
        "id": "condition-david-kim-ckd",
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
        },
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "731000119105",
                "display": "Chronic kidney disease stage 3"
            }],
            "text": "Chronic Kidney Disease Stage 3a"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "onsetDateTime": "2022-03-15"
    })

    write_resource("Condition", {
        "resourceType": "Condition",
        "id": "condition-david-kim-dvt",
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"]
        },
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "resolved"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "128053003",
                "display": "Deep venous thrombosis"
            }],
            "text": "Prior Deep Venous Thrombosis (Resolved)"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "onsetDateTime": "2024-02-01",
        "abatementDateTime": "2024-08-01",
        "note": [{
            "text": "Left lower extremity DVT diagnosed February 2024. Completed 6 months of anticoagulation therapy. Resolved with no residual symptoms."
        }]
    })

    # --- MedicationRequests ---
    write_resource("MedicationRequest", {
        "resourceType": "MedicationRequest",
        "id": "medrx-david-kim-metformin",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "861007",
                "display": "Metformin 1000 MG Oral Tablet"
            }],
            "text": "Metformin 1000mg"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "authoredOn": "2024-06-01",
        "dosageInstruction": [{
            "text": "Take 1 tablet by mouth twice daily with meals",
            "timing": {
                "repeat": {
                    "frequency": 2,
                    "period": 1,
                    "periodUnit": "d"
                }
            },
            "route": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "26643006",
                    "display": "Oral route"
                }]
            },
            "doseAndRate": [{
                "doseQuantity": {
                    "value": 1000,
                    "unit": "mg"
                }
            }]
        }]
    })

    write_resource("MedicationRequest", {
        "resourceType": "MedicationRequest",
        "id": "medrx-david-kim-lisinopril",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "314076",
                "display": "Lisinopril 20 MG Oral Tablet"
            }],
            "text": "Lisinopril 20mg"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "authoredOn": "2022-04-01",
        "dosageInstruction": [{
            "text": "Take 1 tablet by mouth once daily",
            "timing": {
                "repeat": {
                    "frequency": 1,
                    "period": 1,
                    "periodUnit": "d"
                }
            },
            "route": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "26643006",
                    "display": "Oral route"
                }]
            },
            "doseAndRate": [{
                "doseQuantity": {
                    "value": 20,
                    "unit": "mg"
                }
            }]
        }]
    })

    write_resource("MedicationRequest", {
        "resourceType": "MedicationRequest",
        "id": "medrx-david-kim-atorvastatin",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "617312",
                "display": "Atorvastatin 40 MG Oral Tablet"
            }],
            "text": "Atorvastatin 40mg"
        },
        "subject": {
            "reference": f"Patient/{pid}",
            "display": display
        },
        "authoredOn": "2022-04-01",
        "dosageInstruction": [{
            "text": "Take 1 tablet by mouth once daily at bedtime",
            "timing": {
                "repeat": {
                    "frequency": 1,
                    "period": 1,
                    "periodUnit": "d"
                }
            },
            "route": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "26643006",
                    "display": "Oral route"
                }]
            },
            "doseAndRate": [{
                "doseQuantity": {
                    "value": 40,
                    "unit": "mg"
                }
            }]
        }]
    })

    # --- No AllergyIntolerance for David ---

    # --- Observations: Vitals ---
    # Blood Pressure
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-david-kim-bp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T14:00:00Z",
        "component": [
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8480-6",
                        "display": "Systolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": 134,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            },
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8462-4",
                        "display": "Diastolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": 82,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            }
        ]
    })

    # Heart Rate
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-david-kim-hr-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "8867-4",
                "display": "Heart rate"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T14:00:00Z",
        "valueQuantity": {
            "value": 78,
            "unit": "/min",
            "system": "http://unitsofmeasure.org",
            "code": "/min"
        }
    })

    # Temperature
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-david-kim-temp-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "8310-5",
                "display": "Body temperature"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T14:00:00Z",
        "valueQuantity": {
            "value": 98.4,
            "unit": "degF",
            "system": "http://unitsofmeasure.org",
            "code": "[degF]"
        }
    })

    # --- Observations: Labs ---
    # GFR
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-david-kim-gfr-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "33914-3",
                "display": "Glomerular filtration rate/1.73 sq M.predicted"
            }],
            "text": "eGFR"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {
            "value": 48,
            "unit": "mL/min/1.73m2",
            "system": "http://unitsofmeasure.org"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "L",
                "display": "Low"
            }]
        }],
        "referenceRange": [{
            "low": {"value": 60, "unit": "mL/min/1.73m2"},
            "high": {"value": 120, "unit": "mL/min/1.73m2"}
        }]
    })

    # HbA1c
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-david-kim-hba1c-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "4548-4",
                "display": "Hemoglobin A1c/Hemoglobin.total in Blood"
            }],
            "text": "HbA1c"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {
            "value": 6.8,
            "unit": "%",
            "system": "http://unitsofmeasure.org",
            "code": "%"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "N",
                "display": "Normal"
            }]
        }],
        "referenceRange": [{
            "high": {"value": 5.7, "unit": "%"},
            "text": "<5.7% normal, 5.7-6.4% prediabetes, >=6.5% diabetes"
        }]
    })

    # WBC
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-david-kim-wbc-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "6690-2",
                "display": "Leukocytes [#/volume] in Blood by Automated count"
            }],
            "text": "WBC"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {
            "value": 7.2,
            "unit": "10*3/uL",
            "system": "http://unitsofmeasure.org",
            "code": "10*3/uL"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "N",
                "display": "Normal"
            }]
        }],
        "referenceRange": [{
            "low": {"value": 4.5, "unit": "10*3/uL"},
            "high": {"value": 11.0, "unit": "10*3/uL"}
        }]
    })

    # Hemoglobin
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-david-kim-hgb-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "718-7",
                "display": "Hemoglobin [Mass/volume] in Blood"
            }],
            "text": "Hemoglobin"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {
            "value": 14.2,
            "unit": "g/dL",
            "system": "http://unitsofmeasure.org",
            "code": "g/dL"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "N",
                "display": "Normal"
            }]
        }],
        "referenceRange": [{
            "low": {"value": 13.5, "unit": "g/dL"},
            "high": {"value": 17.5, "unit": "g/dL"}
        }]
    })

    # Platelets
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-david-kim-plt-{encounter_date}",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "777-3",
                "display": "Platelets [#/volume] in Blood by Automated count"
            }],
            "text": "Platelets"
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T08:00:00Z",
        "valueQuantity": {
            "value": 245,
            "unit": "10*3/uL",
            "system": "http://unitsofmeasure.org",
            "code": "10*3/uL"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "N",
                "display": "Normal"
            }]
        }],
        "referenceRange": [{
            "low": {"value": 150, "unit": "10*3/uL"},
            "high": {"value": 400, "unit": "10*3/uL"}
        }]
    })

    # --- Encounter ---
    write_resource("Encounter", {
        "resourceType": "Encounter",
        "id": encounter_id,
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
        "subject": {
            "reference": f"Patient/{pid}"
        },
        "period": {
            "start": f"{encounter_date}T13:30:00Z",
            "end": f"{encounter_date}T14:45:00Z"
        },
        "reasonCode": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "254637007",
                "display": "Non-small cell lung cancer"
            }],
            "text": "Oncology consultation - newly diagnosed NSCLC, treatment planning"
        }]
    })

    # --- DocumentReferences ---
    hpi_text = (
        "David Kim is a 56-year-old Korean American male and business executive who presents for oncology "
        "consultation following a recent diagnosis of stage IIIA non-small cell lung cancer (adenocarcinoma). "
        "The patient initially presented to his primary care physician approximately four weeks ago with a "
        "persistent dry cough that had been present for approximately three months, along with mild unintentional "
        "weight loss of 4 kg over the preceding two months. He denied hemoptysis, chest pain, or significant "
        "dyspnea. A chest radiograph revealed a suspicious right upper lobe opacity, prompting CT imaging. "
        "CT of the chest demonstrated a 4.2 cm spiculated mass in the right upper lobe with ipsilateral "
        "mediastinal lymphadenopathy involving stations 4R and 7. PET-CT confirmed FDG avidity of the primary "
        "mass (SUV max 12.4) and mediastinal nodes (SUV max 6.8) without distant metastatic disease. "
        "CT-guided biopsy of the lung mass confirmed adenocarcinoma. Molecular profiling revealed an EGFR "
        "exon 19 deletion mutation, and PD-L1 tumor proportion score was 80%. Brain MRI was negative for "
        "intracranial metastases. His past medical history includes type 2 diabetes managed with metformin, "
        "CKD stage 3a with GFR 48, and a prior left lower extremity DVT two years ago that was treated with "
        "six months of anticoagulation and has fully resolved. He is a former smoker with a 30 pack-year "
        "history who quit five years ago. His ECOG performance status is 1."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-david-kim-hpi",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "10164-2",
                "display": "History of Present illness"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                "code": "clinical-note",
                "display": "Clinical Note"
            }]
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "date": f"{encounter_date}T14:00:00Z",
        "author": [{"display": "Dr. Angela Martinez, MD - Medical Oncology"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(hpi_text)
            }
        }]
    })

    ros_text = (
        "Constitutional: Mild fatigue. Unintentional weight loss of 4 kg over past 2 months. No fever, "
        "no night sweats, no chills.\n"
        "HEENT: No vision changes, no hearing loss, no sore throat, no dysphagia.\n"
        "Cardiovascular: No chest pain, no palpitations, no orthopnea, no PND, no lower extremity edema. "
        "No prior history of coronary artery disease.\n"
        "Respiratory: Persistent dry cough for 3 months, non-productive. No hemoptysis. Mild exertional "
        "dyspnea with two flights of stairs, stable. No wheezing. No pleuritic pain.\n"
        "GI: Mildly decreased appetite. No nausea, no vomiting, no abdominal pain, no change in bowel "
        "habits. No melena or hematochezia.\n"
        "GU: No dysuria, no hematuria, no frequency changes.\n"
        "Musculoskeletal: No bone pain, no joint swelling, no new back pain.\n"
        "Neurological: No headaches, no seizures, no focal weakness, no numbness or tingling. "
        "No cognitive changes.\n"
        "Skin: No new skin lesions, no rashes, no bruising.\n"
        "Endocrine: Well-controlled diabetes on current regimen. No polyuria or polydipsia.\n"
        "Hematologic: No prior DVT symptoms since completion of anticoagulation. No bruising or bleeding."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-david-kim-ros",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "10187-3",
                "display": "Review of systems"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                "code": "clinical-note",
                "display": "Clinical Note"
            }]
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "date": f"{encounter_date}T14:00:00Z",
        "author": [{"display": "Dr. Angela Martinez, MD - Medical Oncology"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(ros_text)
            }
        }]
    })

    pe_text = (
        "Vitals: BP 134/82 mmHg, HR 78 bpm regular, RR 16, Temp 98.4F, SpO2 97% on RA, "
        "Weight 78 kg, Height 175 cm, BMI 25.5\n\n"
        "General: Well-appearing 56-year-old male in no acute distress. Alert, cooperative, and "
        "appropriate. Appears mildly thin compared to reported baseline weight.\n\n"
        "HEENT: Normocephalic, atraumatic. PERRLA. Oropharynx clear without lesions. Moist mucous "
        "membranes. No cervical or supraclavicular lymphadenopathy.\n\n"
        "Neck: Supple. No thyromegaly. No jugular venous distension. No lymphadenopathy in anterior "
        "or posterior cervical chains, supraclavicular fossae, or axillae bilaterally.\n\n"
        "Cardiovascular: Regular rate and rhythm. Normal S1, S2. No murmurs, rubs, or gallops. "
        "No peripheral edema. Dorsalis pedis pulses 2+ bilaterally.\n\n"
        "Respiratory: Mild decreased breath sounds over the right upper lobe posteriorly. "
        "No wheezes. No rales or rhonchi in remaining lung fields. No dullness to percussion. "
        "No accessory muscle use.\n\n"
        "Abdomen: Soft, non-tender, non-distended. Normal bowel sounds in all four quadrants. "
        "No hepatomegaly. No splenomegaly. No palpable masses.\n\n"
        "Extremities: Warm, well-perfused. No cyanosis, clubbing, or edema. No calf tenderness "
        "or swelling bilaterally. No signs of post-thrombotic syndrome in left lower extremity.\n\n"
        "Neurological: Alert and oriented x4. Cranial nerves II-XII intact. Motor strength 5/5 "
        "in all extremities. Sensation intact to light touch. Gait normal. No cerebellar signs.\n\n"
        "Skin: No suspicious skin lesions. Nicotine staining absent from fingers. "
        "No jaundice or pallor."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-david-kim-physical-exam",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "29545-1",
                "display": "Physical findings"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                "code": "clinical-note",
                "display": "Clinical Note"
            }]
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "date": f"{encounter_date}T14:00:00Z",
        "author": [{"display": "Dr. Angela Martinez, MD - Medical Oncology"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(pe_text)
            }
        }]
    })

    clinical_note_text = (
        "ASSESSMENT AND PLAN:\n\n"
        "56-year-old male former smoker with newly diagnosed stage IIIA non-small cell lung cancer "
        "(adenocarcinoma) harboring an EGFR exon 19 deletion with PD-L1 TPS 80%, significant comorbidities "
        "including CKD stage 3a and history of DVT. ECOG performance status 1.\n\n"
        "1. STAGE IIIA NSCLC - ADENOCARCINOMA, EGFR EXON 19 DEL+, PD-L1 80%:\n"
        "   - This is a potentially curable stage IIIA disease with a targetable EGFR mutation\n"
        "   - Presented to multidisciplinary tumor board: consensus is concurrent chemoradiation "
        "followed by consolidation osimertinib (LAURA trial data)\n"
        "   - Alternative approach: neoadjuvant osimertinib (NeoADAURA) given the strong EGFR driver\n"
        "   - Discussed both options extensively with patient; patient prefers to proceed with "
        "chemoradiation + consolidation targeted therapy approach\n"
        "   - Radiation oncology consultation scheduled\n"
        "   - PFTs ordered to confirm adequate pulmonary reserve\n\n"
        "2. CKD STAGE 3a (GFR 48):\n"
        "   - Renal function is a critical consideration for chemotherapy dosing\n"
        "   - Cisplatin may need dose adjustment or substitution with carboplatin (AUC-based dosing)\n"
        "   - Coordinate with nephrology for renal optimization\n"
        "   - Aggressive hydration protocols with cisplatin if used\n\n"
        "3. TYPE 2 DIABETES:\n"
        "   - HbA1c 6.8% on current metformin regimen - well controlled\n"
        "   - Metformin continuation appropriate given current GFR\n"
        "   - Monitor closely during chemotherapy; may need adjustment with corticosteroid use\n\n"
        "4. PRIOR DVT HISTORY:\n"
        "   - Resolved DVT 2 years ago after completing anticoagulation\n"
        "   - Active cancer significantly increases VTE recurrence risk\n"
        "   - Discuss prophylactic anticoagulation; AVERT/CASSINI data supports DOAC prophylaxis\n"
        "   - Risk-benefit discussion with patient given CKD considerations\n\n"
        "5. Follow-up in 1 week to finalize treatment plan after tumor board and radiation oncology input."
    )
    write_resource("DocumentReference", {
        "resourceType": "DocumentReference",
        "id": "doc-david-kim-clinical-note",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "11506-3",
                "display": "Progress note"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                "code": "clinical-note",
                "display": "Clinical Note"
            }]
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "date": f"{encounter_date}T14:00:00Z",
        "author": [{"display": "Dr. Angela Martinez, MD - Medical Oncology"}],
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64(clinical_note_text)
            }
        }]
    })

    # --- Media: CT Chest ---
    write_resource("Media", {
        "resourceType": "Media",
        "id": "media-david-kim-ct-chest",
        "status": "completed",
        "type": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/media-type",
                "code": "image",
                "display": "Image"
            }]
        },
        "modality": {
            "coding": [{
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "code": "CT",
                "display": "Computed Tomography"
            }]
        },
        "subject": {
            "reference": f"Patient/{pid}"
        },
        "createdDateTime": f"2026-02-03T09:00:00Z",
        "bodySite": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "51185008",
                "display": "Thoracic structure"
            }]
        },
        "content": {
            "contentType": "image/dicom",
            "url": "file://data/images/david-kim-ct-chest.dcm",
            "title": "CT Chest with contrast"
        },
        "note": [{
            "text": "CT chest with IV contrast demonstrates a 4.2 cm spiculated mass in the right upper lobe with broad pleural contact but no chest wall invasion. Ipsilateral mediastinal lymphadenopathy is present with enlarged lymph nodes at station 4R (2.8 cm short axis) and station 7 (2.1 cm short axis). No contralateral mediastinal or hilar lymphadenopathy. No pleural effusion. No pericardial effusion. No suspicious osseous lesions. Liver and adrenal glands are unremarkable on this examination. Findings consistent with stage IIIA non-small cell lung cancer (T2aN2M0)."
        }]
    })


# ============================================================================
# MAIN
# ============================================================================
def main():
    print(f"FHIR output directory: {FHIR_DIR}")

    # Ensure all subdirectories exist
    for resource_type in ["Patient", "Condition", "MedicationRequest",
                          "AllergyIntolerance", "Observation", "Encounter",
                          "DocumentReference", "Media"]:
        (FHIR_DIR / resource_type).mkdir(parents=True, exist_ok=True)

    generate_marcus_williams()
    generate_patricia_johnson()
    generate_david_kim()

    # Print summary
    print("\n=== Generation Complete ===")
    total = 0
    for resource_type in ["Patient", "Condition", "MedicationRequest",
                          "AllergyIntolerance", "Observation", "Encounter",
                          "DocumentReference", "Media"]:
        rd = FHIR_DIR / resource_type
        count = len(list(rd.glob("*.json")))
        total += count
        print(f"  {resource_type}: {count} files")
    print(f"  TOTAL: {total} files")


if __name__ == "__main__":
    main()
