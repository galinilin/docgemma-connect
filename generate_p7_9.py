#!/usr/bin/env python3
"""
Generate FHIR R4-compliant JSON files for patients 7-9:
  7. Sarah O'Brien (patient-sarah-obrien)
  8. Thomas Reeves (patient-thomas-reeves)
  9. George Nakamura (patient-george-nakamura)
"""

import json
import base64
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent / "data" / "fhir"

# Ensure all directories exist
for resource_type in [
    "Patient", "Condition", "MedicationRequest", "AllergyIntolerance",
    "Observation", "Encounter", "DocumentReference", "Media"
]:
    (BASE_DIR / resource_type).mkdir(parents=True, exist_ok=True)


def write_resource(resource_type: str, resource: dict):
    """Write a FHIR resource to its corresponding directory."""
    rid = resource["id"]
    path = BASE_DIR / resource_type / f"{rid}.json"
    with open(path, "w") as f:
        json.dump(resource, f, indent=2)
    print(f"  Created {resource_type}/{rid}.json")


def b64(text: str) -> str:
    """Base64-encode a string."""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


# ===========================================================================
# PATIENT 7: Sarah O'Brien
# ===========================================================================
def generate_sarah_obrien():
    print("\n=== Patient 7: Sarah O'Brien ===")
    pid = "patient-sarah-obrien"
    display = "Sarah O'Brien"
    encounter_date = "2026-02-15"
    encounter_id = f"encounter-sarah-obrien-{encounter_date}"

    # --- Patient ---
    write_resource("Patient", {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "SOB-2026-007"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "O'Brien",
            "given": ["Sarah", "Marie"]
        }],
        "gender": "female",
        "birthDate": "1996-09-22",
        "address": [{
            "use": "home",
            "line": ["487 Willow Lane"],
            "city": "Portland",
            "state": "OR",
            "postalCode": "97201"
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
    conditions = [
        ("condition-sarah-obrien-preeclampsia", "398254007", "Severe preeclampsia", "Severe Preeclampsia", "2026-02-15"),
        ("condition-sarah-obrien-gdm", "11687002", "Gestational diabetes mellitus", "Gestational Diabetes (diet-controlled)", "2025-10-01"),
        ("condition-sarah-obrien-pregnancy", "77386006", "Pregnancy", "Pregnancy 34+2 weeks", "2025-06-15"),
    ]
    for cid, code, code_display, text, onset in conditions:
        write_resource("Condition", {
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

    # --- Medications ---
    meds = [
        {
            "id": "medrx-sarah-obrien-labetalol",
            "rxnorm": "197361", "rxdisplay": "Labetalol 200 MG Oral Tablet",
            "text": "Labetalol 200mg",
            "sig": "Take 1 tablet by mouth three times daily",
            "freq": 3, "period": 1, "periodUnit": "d",
            "route_code": "26643006", "route_display": "Oral route",
            "dose_value": 200, "dose_unit": "mg",
            "authored": "2026-02-15"
        },
        {
            "id": "medrx-sarah-obrien-magnesium-sulfate",
            "rxnorm": "235742", "rxdisplay": "Magnesium Sulfate Injectable Solution",
            "text": "Magnesium sulfate 2g/hr IV",
            "sig": "2 grams per hour continuous intravenous infusion",
            "freq": 1, "period": 1, "periodUnit": "h",
            "route_code": "47625008", "route_display": "Intravenous route",
            "dose_value": 2, "dose_unit": "g",
            "authored": "2026-02-15"
        },
        {
            "id": "medrx-sarah-obrien-betamethasone",
            "rxnorm": "1514", "rxdisplay": "Betamethasone",
            "text": "Betamethasone 12mg IM x2 doses",
            "sig": "12 mg intramuscular injection, two doses 24 hours apart for fetal lung maturity",
            "freq": 1, "period": 24, "periodUnit": "h",
            "route_code": "78421000", "route_display": "Intramuscular route",
            "dose_value": 12, "dose_unit": "mg",
            "authored": "2026-02-15"
        },
    ]
    for m in meds:
        write_resource("MedicationRequest", {
            "resourceType": "MedicationRequest",
            "id": m["id"],
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": m["rxnorm"], "display": m["rxdisplay"]}],
                "text": m["text"]
            },
            "subject": {"reference": f"Patient/{pid}", "display": display},
            "authoredOn": m["authored"],
            "dosageInstruction": [{
                "text": m["sig"],
                "timing": {"repeat": {"frequency": m["freq"], "period": m["period"], "periodUnit": m["periodUnit"]}},
                "route": {"coding": [{"system": "http://snomed.info/sct", "code": m["route_code"], "display": m["route_display"]}]},
                "doseAndRate": [{"doseQuantity": {"value": m["dose_value"], "unit": m["dose_unit"]}}]
            }]
        })

    # --- Allergy: Latex ---
    write_resource("AllergyIntolerance", {
        "resourceType": "AllergyIntolerance",
        "id": "allergy-sarah-obrien-latex",
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]
        },
        "type": "allergy",
        "category": ["environment"],
        "criticality": "low",
        "code": {
            "coding": [{"system": "http://snomed.info/sct", "code": "111088007", "display": "Latex"}],
            "text": "Latex"
        },
        "patient": {"reference": f"Patient/{pid}", "display": display},
        "recordedDate": "2018-04-10",
        "reaction": [{
            "manifestation": [{
                "coding": [{"system": "http://snomed.info/sct", "code": "40275004", "display": "Contact dermatitis"}],
                "text": "Contact dermatitis"
            }],
            "severity": "mild"
        }]
    })

    # --- Vital Signs ---
    # Blood Pressure 168/108
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-sarah-obrien-bp-{encounter_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T10:00:00Z",
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": 168, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                "valueQuantity": {"value": 108, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            }
        ]
    })

    # Heart Rate 92
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-sarah-obrien-hr-{encounter_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T10:00:00Z",
        "valueQuantity": {"value": 92, "unit": "/min", "system": "http://unitsofmeasure.org", "code": "/min"}
    })

    # Temperature 98.6F
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-sarah-obrien-temp-{encounter_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T10:00:00Z",
        "valueQuantity": {"value": 98.6, "unit": "degF", "system": "http://unitsofmeasure.org", "code": "[degF]"}
    })

    # --- Labs (each a separate Observation) ---
    labs = [
        {
            "id": f"obs-sarah-obrien-platelets-{encounter_date}",
            "loinc": "777-3", "loinc_display": "Platelets [#/volume] in Blood",
            "text": "Platelets", "value": 98, "unit": "x10^3/uL",
            "unit_code": "10*3/uL",
            "interp_code": "L", "interp_display": "Low",
            "ref_low": 150, "ref_high": 400
        },
        {
            "id": f"obs-sarah-obrien-ast-{encounter_date}",
            "loinc": "1920-8", "loinc_display": "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma",
            "text": "AST", "value": 78, "unit": "U/L",
            "unit_code": "U/L",
            "interp_code": "H", "interp_display": "High",
            "ref_low": 10, "ref_high": 40
        },
        {
            "id": f"obs-sarah-obrien-alt-{encounter_date}",
            "loinc": "1742-6", "loinc_display": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma",
            "text": "ALT", "value": 82, "unit": "U/L",
            "unit_code": "U/L",
            "interp_code": "H", "interp_display": "High",
            "ref_low": 7, "ref_high": 56
        },
        {
            "id": f"obs-sarah-obrien-creatinine-{encounter_date}",
            "loinc": "2160-0", "loinc_display": "Creatinine [Mass/volume] in Serum or Plasma",
            "text": "Creatinine", "value": 1.1, "unit": "mg/dL",
            "unit_code": "mg/dL",
            "interp_code": "H", "interp_display": "High",
            "ref_low": 0.5, "ref_high": 0.9
        },
        {
            "id": f"obs-sarah-obrien-uric-acid-{encounter_date}",
            "loinc": "3084-1", "loinc_display": "Uric acid [Mass/volume] in Serum or Plasma",
            "text": "Uric Acid", "value": 7.8, "unit": "mg/dL",
            "unit_code": "mg/dL",
            "interp_code": "H", "interp_display": "High",
            "ref_low": 2.5, "ref_high": 6.0
        },
        {
            "id": f"obs-sarah-obrien-protein-cr-ratio-{encounter_date}",
            "loinc": "2890-2", "loinc_display": "Protein/Creatinine [Mass ratio] in Urine",
            "text": "Protein/Creatinine Ratio", "value": 4.2, "unit": "mg/mg",
            "unit_code": "mg/mg",
            "interp_code": "H", "interp_display": "High",
            "ref_low": 0, "ref_high": 0.2
        },
    ]
    for lab in labs:
        write_resource("Observation", {
            "resourceType": "Observation",
            "id": lab["id"],
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
            "code": {
                "coding": [{"system": "http://loinc.org", "code": lab["loinc"], "display": lab["loinc_display"]}],
                "text": lab["text"]
            },
            "subject": {"reference": f"Patient/{pid}"},
            "effectiveDateTime": f"{encounter_date}T08:00:00Z",
            "valueQuantity": {"value": lab["value"], "unit": lab["unit"], "system": "http://unitsofmeasure.org", "code": lab["unit_code"]},
            "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": lab["interp_code"], "display": lab["interp_display"]}]}],
            "referenceRange": [{"low": {"value": lab["ref_low"], "unit": lab["unit"]}, "high": {"value": lab["ref_high"], "unit": lab["unit"]}}]
        })

    # --- Encounter (IMP - inpatient L&D) ---
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
            "coding": [{"system": "http://snomed.info/sct", "code": "183460006", "display": "Obstetric admission"}],
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "period": {
            "start": f"{encounter_date}T08:30:00Z"
        },
        "reasonCode": [{
            "coding": [{"system": "http://snomed.info/sct", "code": "398254007", "display": "Severe preeclampsia"}],
            "text": "Severe preeclampsia at 34+2 weeks gestation with headache and visual changes"
        }]
    })

    # --- DocumentReferences ---
    hpi_text = (
        "29-year-old G1P0 woman at 34 weeks and 2 days gestation presents to Labor and Delivery triage "
        "with a chief complaint of persistent frontal headache and intermittent blurry vision that began "
        "approximately 6 hours ago. She reports that she checked her blood pressure at home using a wrist "
        "cuff and obtained a reading of 170/110 mmHg, which prompted her to call her OB provider. She denies "
        "epigastric or right upper quadrant pain, though she has noticed some mild nausea without vomiting. "
        "She denies vaginal bleeding, fluid leakage, decreased fetal movement, or regular contractions.\n\n"
        "Her pregnancy has been complicated by gestational diabetes diagnosed at 28 weeks on her glucose "
        "tolerance test, which has been well controlled with dietary modifications alone. Her most recent "
        "HbA1c was 5.4%. She has had an otherwise uncomplicated prenatal course with normal anatomy scan "
        "at 20 weeks, negative cell-free DNA screening, and appropriate fetal growth at her 32-week growth "
        "ultrasound. She has a known latex allergy causing contact dermatitis and uses non-latex gloves.\n\n"
        "On arrival to L&D, blood pressure was confirmed at 168/108 mmHg. Repeat blood pressure 15 minutes "
        "later was 172/112 mmHg. She was started on a magnesium sulfate loading dose of 4 grams IV over "
        "20 minutes followed by 2 g/hr maintenance infusion for seizure prophylaxis. Labetalol 200 mg PO "
        "was administered for acute blood pressure management. Betamethasone 12 mg IM was given for fetal "
        "lung maturity, with the second dose planned for 24 hours later. Stat labs were drawn including "
        "CBC, CMP, LDH, uric acid, and spot urine protein-to-creatinine ratio."
    )

    ros_text = (
        "Constitutional: Reports headache and mild nausea. Denies fever, chills, malaise, or fatigue beyond "
        "expected pregnancy-related fatigue.\n"
        "HEENT: Reports intermittent blurry vision described as 'seeing spots.' Denies scotomata, diplopia, "
        "tinnitus, or hearing changes.\n"
        "Cardiovascular: Denies chest pain, palpitations, or dyspnea on exertion.\n"
        "Respiratory: Denies cough, shortness of breath at rest, or wheezing.\n"
        "Gastrointestinal: Reports mild nausea without vomiting. Denies epigastric pain, right upper quadrant "
        "pain, diarrhea, or constipation. Appetite mildly decreased.\n"
        "Genitourinary: Denies dysuria, hematuria, or decreased urine output. Denies vaginal bleeding or "
        "fluid leakage.\n"
        "Musculoskeletal: Reports mild bilateral lower extremity edema (chronic, worsening). Denies joint pain.\n"
        "Neurological: Reports frontal headache rated 6/10. Denies focal weakness, numbness, or tingling. "
        "Reports intermittent visual disturbances.\n"
        "Obstetric: Reports normal fetal movement. Denies regular contractions. Occasional Braxton-Hicks "
        "contractions. No rupture of membranes."
    )

    pe_text = (
        "Vitals: BP 168/108 mmHg (left arm, manual), HR 92 bpm regular, RR 18, Temp 98.6 F oral, "
        "SpO2 99% on room air\n\n"
        "General: Alert, oriented, appearing uncomfortable with headache but in no acute respiratory distress. "
        "Well-nourished, gravid female.\n\n"
        "HEENT: Normocephalic, atraumatic. PERRLA bilaterally. No papilledema on fundoscopic exam. "
        "Oropharynx clear and moist. No facial edema.\n\n"
        "Neck: Supple, no lymphadenopathy, no thyromegaly, no JVD.\n\n"
        "Cardiovascular: Regular rate and rhythm. Normal S1/S2 with physiologic S3 of pregnancy. "
        "No pathologic murmurs, rubs, or gallops. 1+ bilateral pedal edema extending to mid-shin.\n\n"
        "Respiratory: Clear to auscultation bilaterally. No wheezes, rales, or rhonchi. Good air movement.\n\n"
        "Abdomen: Gravid, non-tender to palpation in all quadrants. No rebound or guarding. No right upper "
        "quadrant tenderness. Fundal height 33 cm. Fetal heart tones in 140s by continuous external monitor.\n\n"
        "Extremities: 1+ bilateral lower extremity pitting edema to mid-shin. Warm and well-perfused. "
        "2+ dorsalis pedis pulses bilaterally. Brisk capillary refill.\n\n"
        "Neurological: Alert and oriented x4. Cranial nerves II-XII intact. Deep tendon reflexes 3+ "
        "bilateral patellar (brisk, symmetric). No clonus. Sensation grossly intact. No focal deficits.\n\n"
        "Obstetric: Cervix 1 cm dilated, 50% effaced, -3 station. Membranes intact. Vertex presentation "
        "confirmed by ultrasound. External fetal monitoring shows reactive NST with category I tracing. "
        "Tocometry shows occasional irregular contractions."
    )

    clinical_note_text = (
        "29-year-old G1P0 at 34+2 weeks with severe preeclampsia presenting with headache, visual changes, "
        "and severely elevated blood pressures. Lab work is notable for thrombocytopenia (platelets 98K), "
        "elevated hepatic transaminases (AST 78, ALT 82), elevated creatinine at 1.1, and significant "
        "proteinuria with protein/creatinine ratio of 4.2 mg/mg. Uric acid is elevated at 7.8 mg/dL. "
        "These findings are consistent with severe features of preeclampsia with early laboratory evidence "
        "of HELLP syndrome.\n\n"
        "Patient has been started on magnesium sulfate for seizure prophylaxis with loading dose completed "
        "and maintenance infusion running at 2 g/hr. Labetalol 200 mg PO TID initiated for blood pressure "
        "control. First dose of betamethasone administered for fetal lung maturity at 34 weeks. Continuous "
        "fetal monitoring in place showing reassuring category I tracing.\n\n"
        "Plan is to administer the second dose of betamethasone in 24 hours and reassess maternal-fetal status. "
        "If blood pressures remain uncontrolled, clinical deterioration occurs, or labs worsen significantly, "
        "delivery will be expedited. MFM consultation has been placed. Blood bank has been notified and type "
        "and screen is on file. Neonatology has been alerted for possible preterm delivery. Strict I&Os, "
        "hourly neuro checks, and serial labs every 6 hours have been ordered."
    )

    docs = [
        ("doc-sarah-obrien-hpi", "10164-2", "History of Present illness", hpi_text),
        ("doc-sarah-obrien-ros", "10187-3", "Review of systems", ros_text),
        ("doc-sarah-obrien-physical-exam", "29545-1", "Physical findings", pe_text),
        ("doc-sarah-obrien-clinical-note", "11506-3", "Progress note", clinical_note_text),
    ]
    for doc_id, loinc, loinc_display, content_text in docs:
        write_resource("DocumentReference", {
            "resourceType": "DocumentReference",
            "id": doc_id,
            "status": "current",
            "type": {
                "coding": [{"system": "http://loinc.org", "code": loinc, "display": loinc_display}]
            },
            "category": [{
                "coding": [{
                    "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                    "code": "clinical-note",
                    "display": "Clinical Note"
                }]
            }],
            "subject": {"reference": f"Patient/{pid}"},
            "date": f"{encounter_date}T10:30:00Z",
            "author": [{"display": "Dr. Emily Rodriguez, MD - MFM"}],
            "content": [{
                "attachment": {
                    "contentType": "text/plain",
                    "data": b64(content_text)
                }
            }]
        })

    # --- Media: Fetal ultrasound ---
    write_resource("Media", {
        "resourceType": "Media",
        "id": "media-sarah-obrien-fetal-us",
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
                "code": "US",
                "display": "Ultrasound"
            }]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "createdDateTime": f"{encounter_date}T09:15:00Z",
        "bodySite": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "818983003",
                "display": "Abdomen"
            }]
        },
        "content": {
            "contentType": "image/png",
            "url": "file://data/images/sarah-obrien-fetal-us.png",
            "title": "Fetal ultrasound - 34+2 weeks"
        },
        "note": [{
            "text": "Fetal ultrasound at 34+2 weeks gestation. Estimated fetal weight at 53rd percentile, appropriate for gestational age. Amniotic fluid index 14 cm (normal). Fetal anatomy grossly normal. Vertex presentation confirmed. Placenta posterior, grade II, no evidence of abruption. Umbilical artery Doppler normal with S/D ratio 2.8. Middle cerebral artery PI within normal limits."
        }]
    })


# ===========================================================================
# PATIENT 8: Thomas Reeves
# ===========================================================================
def generate_thomas_reeves():
    print("\n=== Patient 8: Thomas Reeves ===")
    pid = "patient-thomas-reeves"
    display = "Thomas Reeves"
    encounter_date = "2026-02-10"
    encounter_id = f"encounter-thomas-reeves-{encounter_date}"

    # --- Patient ---
    write_resource("Patient", {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "TR-2026-008"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Reeves",
            "given": ["Thomas", "Andrew"]
        }],
        "gender": "male",
        "birthDate": "1973-11-08",
        "address": [{
            "use": "home",
            "line": ["2214 Birch Street"],
            "city": "Denver",
            "state": "CO",
            "postalCode": "80202"
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
    conditions = [
        ("condition-thomas-reeves-venom-allergy", "390952000", "Hymenoptera venom allergy", "Hymenoptera Venom Allergy (bee sting anaphylaxis)", "2025-07-15"),
        ("condition-thomas-reeves-hypertension", "38341003", "Hypertensive disorder", "Hypertension", "2019-03-01"),
        ("condition-thomas-reeves-afib", "282825002", "Paroxysmal atrial fibrillation", "Paroxysmal Atrial Fibrillation", "2022-09-01"),
    ]
    for cid, code, code_display, text, onset in conditions:
        write_resource("Condition", {
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

    # --- Medications ---
    meds = [
        {
            "id": "medrx-thomas-reeves-lisinopril",
            "rxnorm": "314077", "rxdisplay": "Lisinopril 10 MG Oral Tablet",
            "text": "Lisinopril 10mg",
            "sig": "Take 1 tablet by mouth once daily",
            "freq": 1, "period": 1, "periodUnit": "d",
            "route_code": "26643006", "route_display": "Oral route",
            "dose_value": 10, "dose_unit": "mg",
            "authored": "2019-03-15"
        },
        {
            "id": "medrx-thomas-reeves-flecainide",
            "rxnorm": "197589", "rxdisplay": "Flecainide 100 MG Oral Tablet",
            "text": "Flecainide 100mg",
            "sig": "Take 1 tablet by mouth twice daily",
            "freq": 2, "period": 1, "periodUnit": "d",
            "route_code": "26643006", "route_display": "Oral route",
            "dose_value": 100, "dose_unit": "mg",
            "authored": "2022-10-01"
        },
    ]
    for m in meds:
        write_resource("MedicationRequest", {
            "resourceType": "MedicationRequest",
            "id": m["id"],
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": m["rxnorm"], "display": m["rxdisplay"]}],
                "text": m["text"]
            },
            "subject": {"reference": f"Patient/{pid}", "display": display},
            "authoredOn": m["authored"],
            "dosageInstruction": [{
                "text": m["sig"],
                "timing": {"repeat": {"frequency": m["freq"], "period": m["period"], "periodUnit": m["periodUnit"]}},
                "route": {"coding": [{"system": "http://snomed.info/sct", "code": m["route_code"], "display": m["route_display"]}]},
                "doseAndRate": [{"doseQuantity": {"value": m["dose_value"], "unit": m["dose_unit"]}}]
            }]
        })

    # --- Allergy: Hymenoptera venom ---
    write_resource("AllergyIntolerance", {
        "resourceType": "AllergyIntolerance",
        "id": "allergy-thomas-reeves-hymenoptera-venom",
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]
        },
        "type": "allergy",
        "category": ["environment"],
        "criticality": "high",
        "code": {
            "coding": [{"system": "http://snomed.info/sct", "code": "288328004", "display": "Hymenoptera venom"}],
            "text": "Hymenoptera venom (bee sting)"
        },
        "patient": {"reference": f"Patient/{pid}", "display": display},
        "recordedDate": "2025-07-20",
        "reaction": [{
            "manifestation": [
                {
                    "coding": [{"system": "http://snomed.info/sct", "code": "39579001", "display": "Anaphylaxis"}],
                    "text": "Anaphylaxis"
                },
                {
                    "coding": [{"system": "http://snomed.info/sct", "code": "423341008", "display": "Laryngeal edema"}],
                    "text": "Laryngeal edema"
                },
                {
                    "coding": [{"system": "http://snomed.info/sct", "code": "45007003", "display": "Hypotension"}],
                    "text": "Hypotension"
                }
            ],
            "severity": "severe",
            "description": "Bee sting anaphylaxis Summer 2025 requiring 3 doses of epinephrine, presented with laryngeal edema and hypotension"
        }]
    })

    # --- Vital Signs ---
    # Blood Pressure 128/78
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-thomas-reeves-bp-{encounter_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T14:00:00Z",
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": 128, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                "valueQuantity": {"value": 78, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            }
        ]
    })

    # Heart Rate 68
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-thomas-reeves-hr-{encounter_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T14:00:00Z",
        "valueQuantity": {"value": 68, "unit": "/min", "system": "http://unitsofmeasure.org", "code": "/min"}
    })

    # Temperature 98.4F
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-thomas-reeves-temp-{encounter_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T14:00:00Z",
        "valueQuantity": {"value": 98.4, "unit": "degF", "system": "http://unitsofmeasure.org", "code": "[degF]"}
    })

    # --- Labs ---
    labs = [
        {
            "id": f"obs-thomas-reeves-tryptase-{encounter_date}",
            "loinc": "54448-2", "loinc_display": "Tryptase [Mass/volume] in Serum or Plasma",
            "text": "Tryptase", "value": 18, "unit": "ng/mL",
            "unit_code": "ng/mL",
            "interp_code": "H", "interp_display": "High",
            "ref_low": 0, "ref_high": 11.5
        },
        {
            "id": f"obs-thomas-reeves-ige-{encounter_date}",
            "loinc": "19113-0", "loinc_display": "IgE [Units/volume] in Serum or Plasma",
            "text": "IgE Total", "value": 385, "unit": "IU/mL",
            "unit_code": "IU/mL",
            "interp_code": "H", "interp_display": "High",
            "ref_low": 0, "ref_high": 100
        },
    ]
    for lab in labs:
        write_resource("Observation", {
            "resourceType": "Observation",
            "id": lab["id"],
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
            "code": {
                "coding": [{"system": "http://loinc.org", "code": lab["loinc"], "display": lab["loinc_display"]}],
                "text": lab["text"]
            },
            "subject": {"reference": f"Patient/{pid}"},
            "effectiveDateTime": f"{encounter_date}T13:00:00Z",
            "valueQuantity": {"value": lab["value"], "unit": lab["unit"], "system": "http://unitsofmeasure.org", "code": lab["unit_code"]},
            "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": lab["interp_code"], "display": lab["interp_display"]}]}],
            "referenceRange": [{"low": {"value": lab["ref_low"], "unit": lab["unit"]}, "high": {"value": lab["ref_high"], "unit": lab["unit"]}}]
        })

    # --- Encounter (AMB - allergy clinic) ---
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
            "coding": [{"system": "http://snomed.info/sct", "code": "185349003", "display": "Encounter for check up"}],
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "period": {
            "start": f"{encounter_date}T13:30:00Z",
            "end": f"{encounter_date}T14:30:00Z"
        },
        "reasonCode": [{
            "coding": [{"system": "http://snomed.info/sct", "code": "390952000", "display": "Hymenoptera venom allergy"}],
            "text": "Venom immunotherapy evaluation, 6 months post-anaphylaxis"
        }]
    })

    # --- DocumentReferences ---
    hpi_text = (
        "52-year-old man presents to the Allergy and Immunology clinic for venom immunotherapy evaluation "
        "approximately 6 months following a life-threatening anaphylactic reaction to a honeybee sting. "
        "The incident occurred in July 2025 while he was working in his garden. Within 5 minutes of the sting "
        "to his right forearm, he developed generalized urticaria, facial flushing, and progressive throat "
        "tightness with audible stridor. His wife administered his first EpiPen while calling 911. Paramedics "
        "administered a second dose of intramuscular epinephrine en route. In the emergency department, he "
        "required a third dose of epinephrine for persistent hypotension (systolic BP in the 70s) and "
        "worsening laryngeal edema.\n\n"
        "He was admitted to the ICU for 24-hour observation. Serum tryptase drawn 2 hours after the reaction "
        "was 18 ng/mL (elevated, reference <11.5). He was discharged with two EpiPen auto-injectors and "
        "instructions for urgent allergy referral. He has since carried his EpiPens at all times and has "
        "avoided outdoor activities during warmer months. He denies any subsequent stings or allergic reactions.\n\n"
        "His medical history is significant for hypertension controlled on lisinopril 10 mg daily and "
        "paroxysmal atrial fibrillation managed with flecainide 100 mg BID. He has had no episodes of AFib "
        "since starting flecainide. He is an electrician by trade and works primarily outdoors, which places "
        "him at significant occupational risk for future stings. He is motivated to pursue venom immunotherapy "
        "to reduce his risk of future anaphylaxis."
    )

    ros_text = (
        "Constitutional: No fever, weight loss, or night sweats. Reports increased anxiety related to outdoor "
        "activities since the anaphylactic event.\n"
        "HEENT: No nasal congestion, rhinorrhea, or sinus pressure. No throat tightness or dysphagia currently.\n"
        "Cardiovascular: No chest pain, palpitations, or shortness of breath at rest. No lightheadedness or "
        "syncope. Reports good exercise tolerance.\n"
        "Respiratory: No cough, wheezing, or dyspnea. No history of asthma.\n"
        "Gastrointestinal: No nausea, vomiting, abdominal pain, or diarrhea.\n"
        "Skin: No current urticaria, angioedema, or pruritus. No eczema or chronic skin conditions.\n"
        "Neurological: No headache, dizziness, or numbness. No tingling.\n"
        "Psychiatric: Reports heightened anxiety when outdoors, especially near flowering plants. "
        "No panic attacks. Sleep is occasionally disrupted by worry about future stings."
    )

    pe_text = (
        "Vitals: BP 128/78 mmHg, HR 68 bpm regular, RR 14, Temp 98.4 F oral, SpO2 99% on room air\n\n"
        "General: Alert, oriented, well-appearing man in no acute distress. Appears anxious but cooperative.\n\n"
        "HEENT: Normocephalic, atraumatic. Nasal mucosa pink without edema or polyps. Oropharynx clear, "
        "no posterior pharyngeal erythema or cobblestoning. No uvular edema. Tympanic membranes clear "
        "bilaterally.\n\n"
        "Neck: Supple, no lymphadenopathy, no thyromegaly. No JVD.\n\n"
        "Cardiovascular: Regular rate and rhythm, normal S1/S2. No murmurs, rubs, or gallops. "
        "No peripheral edema. Radial pulses 2+ bilaterally.\n\n"
        "Respiratory: Clear to auscultation bilaterally. No wheezes, rhonchi, or stridor. "
        "Symmetric chest expansion. No accessory muscle use.\n\n"
        "Abdomen: Soft, non-tender, non-distended. Normal bowel sounds in all four quadrants. "
        "No hepatosplenomegaly. No masses.\n\n"
        "Skin: No urticaria, angioedema, or active rash. Well-healed circular scar on right volar "
        "forearm at site of prior bee sting, approximately 8 mm. No eczematous changes. "
        "No dermatographism elicited.\n\n"
        "Extremities: Warm, well-perfused. No cyanosis, clubbing, or edema.\n\n"
        "Neurological: Alert and oriented x4. Cranial nerves II-XII grossly intact. "
        "Normal gait and station."
    )

    clinical_note_text = (
        "52-year-old electrician with a history of severe honeybee sting anaphylaxis in July 2025, "
        "presenting for venom immunotherapy evaluation. His reaction was classified as Grade IV anaphylaxis "
        "(Mueller classification) with respiratory compromise (laryngeal edema, stridor) and cardiovascular "
        "collapse (hypotension requiring 3 doses of epinephrine and ICU admission). Peak tryptase was "
        "18 ng/mL, and total IgE is elevated at 385 IU/mL.\n\n"
        "Given the severity of his prior reaction, his significant occupational exposure risk as an outdoor "
        "worker, and the presence of comorbid cardiovascular disease (hypertension, paroxysmal AFib), he is "
        "an excellent candidate for venom immunotherapy (VIT). Notably, his concurrent use of an ACE inhibitor "
        "(lisinopril) has been discussed -- ACE inhibitors may theoretically increase the risk of anaphylaxis "
        "during immunotherapy due to their effect on bradykinin metabolism. However, current guidelines suggest "
        "the benefit of VIT outweighs this theoretical risk, particularly given his high-grade prior reaction.\n\n"
        "Plan: Initiate honeybee venom immunotherapy using a rush protocol with premedication (cetirizine "
        "10 mg + montelukast 10 mg, 2 hours prior). Schedule first VIT session with 2-hour observation period. "
        "Ensure crash cart and epinephrine readily available. Continue current medications. "
        "Specific IgE to Apis mellifera venom ordered to confirm sensitization prior to VIT initiation. "
        "Follow-up in 1 week for first injection appointment."
    )

    docs = [
        ("doc-thomas-reeves-hpi", "10164-2", "History of Present illness", hpi_text),
        ("doc-thomas-reeves-ros", "10187-3", "Review of systems", ros_text),
        ("doc-thomas-reeves-physical-exam", "29545-1", "Physical findings", pe_text),
        ("doc-thomas-reeves-clinical-note", "11506-3", "Progress note", clinical_note_text),
    ]
    for doc_id, loinc, loinc_display, content_text in docs:
        write_resource("DocumentReference", {
            "resourceType": "DocumentReference",
            "id": doc_id,
            "status": "current",
            "type": {
                "coding": [{"system": "http://loinc.org", "code": loinc, "display": loinc_display}]
            },
            "category": [{
                "coding": [{
                    "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                    "code": "clinical-note",
                    "display": "Clinical Note"
                }]
            }],
            "subject": {"reference": f"Patient/{pid}"},
            "date": f"{encounter_date}T15:00:00Z",
            "author": [{"display": "Dr. Amanda Torres, MD - Allergy/Immunology"}],
            "content": [{
                "attachment": {
                    "contentType": "text/plain",
                    "data": b64(content_text)
                }
            }]
        })


# ===========================================================================
# PATIENT 9: George Nakamura
# ===========================================================================
def generate_george_nakamura():
    print("\n=== Patient 9: George Nakamura ===")
    pid = "patient-george-nakamura"
    display = "George Nakamura"
    encounter_date = "2026-02-17"
    encounter_id = f"encounter-george-nakamura-{encounter_date}"

    # --- Patient ---
    write_resource("Patient", {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [{
            "system": "http://hospital.example.org/patients",
            "value": "GN-2026-009"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Nakamura",
            "given": ["George", "Takeshi"]
        }],
        "gender": "male",
        "birthDate": "1947-08-12",
        "address": [{
            "use": "home",
            "line": ["1891 Cherry Blossom Drive"],
            "city": "Seattle",
            "state": "WA",
            "postalCode": "98101"
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
    conditions = [
        ("condition-george-nakamura-pancreatic-cancer", "363418001", "Malignant neoplasm of pancreas", "Metastatic Pancreatic Adenocarcinoma (liver, peritoneal)", "2025-08-01"),
        ("condition-george-nakamura-cancer-pain", "90673000", "Cancer pain syndrome", "Cancer Pain Syndrome", "2025-09-01"),
        ("condition-george-nakamura-cachexia", "238108007", "Cachexia", "Cachexia", "2025-11-01"),
        ("condition-george-nakamura-nausea-vomiting", "422400008", "Nausea and vomiting", "Nausea and Vomiting", "2025-10-15"),
    ]
    for cid, code, code_display, text, onset in conditions:
        write_resource("Condition", {
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

    # --- Medications ---
    meds = [
        {
            "id": "medrx-george-nakamura-morphine-er",
            "rxnorm": "863539", "rxdisplay": "Morphine Sulfate Extended Release 60 MG Oral Tablet",
            "text": "Morphine ER 60mg",
            "sig": "Take 1 tablet by mouth every 12 hours for pain (scheduled)",
            "freq": 1, "period": 12, "periodUnit": "h",
            "route_code": "26643006", "route_display": "Oral route",
            "dose_value": 60, "dose_unit": "mg",
            "authored": "2025-12-01"
        },
        {
            "id": "medrx-george-nakamura-morphine-ir",
            "rxnorm": "197696", "rxdisplay": "Morphine Sulfate 15 MG Oral Tablet",
            "text": "Morphine IR 15mg",
            "sig": "Take 1 tablet by mouth every 4 hours as needed for breakthrough pain",
            "freq": 1, "period": 4, "periodUnit": "h",
            "route_code": "26643006", "route_display": "Oral route",
            "dose_value": 15, "dose_unit": "mg",
            "authored": "2025-12-01"
        },
        {
            "id": "medrx-george-nakamura-ondansetron",
            "rxnorm": "312087", "rxdisplay": "Ondansetron 8 MG Oral Tablet",
            "text": "Ondansetron 8mg",
            "sig": "Take 1 tablet by mouth every 8 hours as needed for nausea",
            "freq": 1, "period": 8, "periodUnit": "h",
            "route_code": "26643006", "route_display": "Oral route",
            "dose_value": 8, "dose_unit": "mg",
            "authored": "2025-11-15"
        },
        {
            "id": "medrx-george-nakamura-dexamethasone",
            "rxnorm": "197579", "rxdisplay": "Dexamethasone 4 MG Oral Tablet",
            "text": "Dexamethasone 4mg",
            "sig": "Take 1 tablet by mouth once daily in the morning",
            "freq": 1, "period": 1, "periodUnit": "d",
            "route_code": "26643006", "route_display": "Oral route",
            "dose_value": 4, "dose_unit": "mg",
            "authored": "2025-12-15"
        },
    ]
    for m in meds:
        write_resource("MedicationRequest", {
            "resourceType": "MedicationRequest",
            "id": m["id"],
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": m["rxnorm"], "display": m["rxdisplay"]}],
                "text": m["text"]
            },
            "subject": {"reference": f"Patient/{pid}", "display": display},
            "authoredOn": m["authored"],
            "dosageInstruction": [{
                "text": m["sig"],
                "timing": {"repeat": {"frequency": m["freq"], "period": m["period"], "periodUnit": m["periodUnit"]}},
                "route": {"coding": [{"system": "http://snomed.info/sct", "code": m["route_code"], "display": m["route_display"]}]},
                "doseAndRate": [{"doseQuantity": {"value": m["dose_value"], "unit": m["dose_unit"]}}]
            }]
        })

    # --- Allergy: Codeine ---
    write_resource("AllergyIntolerance", {
        "resourceType": "AllergyIntolerance",
        "id": "allergy-george-nakamura-codeine",
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
            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "2670", "display": "Codeine"}],
            "text": "Codeine"
        },
        "patient": {"reference": f"Patient/{pid}", "display": display},
        "recordedDate": "2010-03-20",
        "reaction": [{
            "manifestation": [{
                "coding": [{"system": "http://snomed.info/sct", "code": "422400008", "display": "Nausea and vomiting"}],
                "text": "Nausea and vomiting"
            }],
            "severity": "moderate"
        }]
    })

    # --- Vital Signs ---
    # Blood Pressure 102/64
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-george-nakamura-bp-{encounter_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T09:00:00Z",
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": 102, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                "valueQuantity": {"value": 64, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
            }
        ]
    })

    # Heart Rate 94
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-george-nakamura-hr-{encounter_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T09:00:00Z",
        "valueQuantity": {"value": 94, "unit": "/min", "system": "http://unitsofmeasure.org", "code": "/min"}
    })

    # Temperature 98.2F
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-george-nakamura-temp-{encounter_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T09:00:00Z",
        "valueQuantity": {"value": 98.2, "unit": "degF", "system": "http://unitsofmeasure.org", "code": "[degF]"}
    })

    # Weight 52kg
    write_resource("Observation", {
        "resourceType": "Observation",
        "id": f"obs-george-nakamura-weight-{encounter_date}",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "29463-7", "display": "Body weight"}]},
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": f"{encounter_date}T09:00:00Z",
        "valueQuantity": {"value": 52, "unit": "kg", "system": "http://unitsofmeasure.org", "code": "kg"}
    })

    # --- Labs ---
    labs = [
        {
            "id": f"obs-george-nakamura-albumin-{encounter_date}",
            "loinc": "1751-7", "loinc_display": "Albumin [Mass/volume] in Serum or Plasma",
            "text": "Albumin", "value": 2.1, "unit": "g/dL",
            "unit_code": "g/dL",
            "interp_code": "L", "interp_display": "Low",
            "ref_low": 3.5, "ref_high": 5.5
        },
        {
            "id": f"obs-george-nakamura-bilirubin-{encounter_date}",
            "loinc": "1975-2", "loinc_display": "Total Bilirubin [Mass/volume] in Serum or Plasma",
            "text": "Total Bilirubin", "value": 2.8, "unit": "mg/dL",
            "unit_code": "mg/dL",
            "interp_code": "H", "interp_display": "High",
            "ref_low": 0.1, "ref_high": 1.2
        },
        {
            "id": f"obs-george-nakamura-creatinine-{encounter_date}",
            "loinc": "2160-0", "loinc_display": "Creatinine [Mass/volume] in Serum or Plasma",
            "text": "Creatinine", "value": 1.4, "unit": "mg/dL",
            "unit_code": "mg/dL",
            "interp_code": "H", "interp_display": "High",
            "ref_low": 0.7, "ref_high": 1.3
        },
    ]
    for lab in labs:
        write_resource("Observation", {
            "resourceType": "Observation",
            "id": lab["id"],
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
            "code": {
                "coding": [{"system": "http://loinc.org", "code": lab["loinc"], "display": lab["loinc_display"]}],
                "text": lab["text"]
            },
            "subject": {"reference": f"Patient/{pid}"},
            "effectiveDateTime": f"{encounter_date}T07:30:00Z",
            "valueQuantity": {"value": lab["value"], "unit": lab["unit"], "system": "http://unitsofmeasure.org", "code": lab["unit_code"]},
            "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": lab["interp_code"], "display": lab["interp_display"]}]}],
            "referenceRange": [{"low": {"value": lab["ref_low"], "unit": lab["unit"]}, "high": {"value": lab["ref_high"], "unit": lab["unit"]}}]
        })

    # --- Encounter (IMP - palliative/hospice) ---
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
            "coding": [{"system": "http://snomed.info/sct", "code": "305354007", "display": "Admission to palliative care department"}],
        }],
        "subject": {"reference": f"Patient/{pid}"},
        "period": {
            "start": f"{encounter_date}T07:00:00Z"
        },
        "reasonCode": [{
            "coding": [{"system": "http://snomed.info/sct", "code": "90673000", "display": "Cancer pain syndrome"}],
            "text": "Pain crisis with intractable nausea, hospice enrolled, symptom management"
        }]
    })

    # --- DocumentReferences ---
    hpi_text = (
        "78-year-old Japanese American man with metastatic pancreatic adenocarcinoma, diagnosed in August 2025, "
        "with known liver and peritoneal metastases, presents to the palliative care inpatient unit for "
        "management of a pain crisis and intractable nausea. He was enrolled in hospice care in January 2026 "
        "after declining further chemotherapy following progression on gemcitabine/nab-paclitaxel.\n\n"
        "Over the past 5 days, his pain has escalated significantly despite his current regimen of morphine "
        "sulfate ER 60 mg every 12 hours. He has been requiring an average of 4 breakthrough doses of morphine "
        "IR 15 mg daily over the past 72 hours, compared to his usual 1-2 doses per day. The pain is described "
        "as a deep, constant, boring epigastric pain radiating to the back, rated 8/10 at its worst. He also "
        "reports worsening nausea with episodes of vomiting 2-3 times daily despite ondansetron 8 mg PO PRN, "
        "which has been only partially effective.\n\n"
        "He has experienced progressive weight loss, now down to 52 kg from a baseline weight of 68 kg "
        "(24% weight loss over 6 months). His appetite has been minimal, tolerating only small sips of "
        "liquids and occasional spoonfuls of congee prepared by his wife. He is increasingly fatigued and "
        "spending most of the day in bed. He denies fever, new neurological symptoms, or urinary changes. "
        "His wife and adult daughter are at bedside and are aware of his prognosis. The family has expressed "
        "a preference for comfort-focused care and wishes to avoid hospitalization if symptoms can be "
        "managed at home. However, the current pain crisis exceeded home management capabilities."
    )

    ros_text = (
        "Constitutional: Profound fatigue, progressive weight loss (52 kg, down from 68 kg baseline). "
        "No fever or chills. Poor appetite, tolerating minimal oral intake.\n"
        "HEENT: Dry mouth. Mild scleral icterus noted by family. No vision changes, hearing loss, or "
        "epistaxis.\n"
        "Cardiovascular: No chest pain or palpitations. Notes occasional lightheadedness with position changes.\n"
        "Respiratory: Mild dyspnea on exertion (walking to bathroom). No cough or hemoptysis.\n"
        "Gastrointestinal: Severe nausea with vomiting 2-3 times daily. Deep epigastric pain radiating to "
        "back, rated 8/10. No hematemesis or melena. Reports intermittent constipation (last bowel movement "
        "2 days ago).\n"
        "Genitourinary: Decreased urine output noted by family. No dysuria or hematuria.\n"
        "Musculoskeletal: Generalized weakness and muscle wasting. Unable to walk more than 10 feet without "
        "assistance.\n"
        "Neurological: No new headache, confusion, or focal deficits. Reports intermittent drowsiness "
        "attributed to morphine.\n"
        "Psychiatric: Reports feelings of peace with his situation. Denies depression or active distress. "
        "Spiritual support from family and temple community."
    )

    pe_text = (
        "Vitals: BP 102/64 mmHg, HR 94 bpm regular, RR 18, Temp 98.2 F oral, SpO2 96% on room air, "
        "Weight 52 kg\n\n"
        "General: Cachectic elderly man resting in bed, appears older than stated age. Alert and oriented "
        "to person, place, time, and situation. Appears fatigued and uncomfortable but is conversant. "
        "ECOG performance status 3 (capable of limited self-care, confined to bed >50% of waking hours).\n\n"
        "HEENT: Temporal wasting evident bilaterally. Mild scleral icterus. Dry mucous membranes. "
        "Oral cavity without thrush or lesions.\n\n"
        "Neck: Supple, no palpable lymphadenopathy. No JVD.\n\n"
        "Cardiovascular: Tachycardic but regular rhythm. Normal S1/S2. No murmurs, rubs, or gallops. "
        "Thready peripheral pulses.\n\n"
        "Respiratory: Clear to auscultation bilaterally. Shallow but unlabored respirations. "
        "No wheezes or crackles.\n\n"
        "Abdomen: Distended with firm, non-tender hepatomegaly palpable 4 cm below the right costal margin. "
        "Moderate diffuse tenderness to deep palpation in the epigastrium. No rebound or guarding. "
        "Hypoactive bowel sounds. Mild shifting dullness suggesting small-volume ascites.\n\n"
        "Extremities: Marked muscle wasting of upper and lower extremities. No peripheral edema. "
        "Skin is dry and thin with poor turgor. No pressure injuries noted on sacrum or heels. "
        "Capillary refill 3 seconds.\n\n"
        "Neurological: Alert and oriented x4. Cranial nerves grossly intact. Strength 3/5 globally "
        "due to deconditioning and cachexia. Sensation intact. No asterixis.\n\n"
        "Skin: Jaundiced. No rashes or petechiae. No skin breakdown."
    )

    clinical_note_text = (
        "78-year-old man with metastatic pancreatic adenocarcinoma (liver and peritoneal metastases), "
        "hospice-enrolled, admitted for pain crisis and intractable nausea. Current morphine ER 60 mg q12h "
        "with 4 breakthrough doses of morphine IR 15 mg daily indicates a total daily morphine equivalent "
        "of approximately 180 mg, suggesting his baseline long-acting dose is inadequate.\n\n"
        "Assessment: Uncontrolled cancer pain likely secondary to disease progression and possible malignant "
        "bowel obstruction component contributing to nausea. Cachexia is severe with BMI approximately 17.3. "
        "Labs show declining hepatic function (bilirubin 2.8), hypoalbuminemia (2.1), and mild renal "
        "impairment (creatinine 1.4), all of which may affect drug metabolism and should guide dosing "
        "adjustments.\n\n"
        "Plan:\n"
        "1. Pain management: Increase morphine ER to 90 mg q12h (calculated from total daily dose including "
        "breakthrough usage). Increase morphine IR breakthrough to 20 mg q3h PRN. Monitor for respiratory "
        "depression given hepatic impairment.\n"
        "2. Nausea: Add haloperidol 0.5 mg IV q6h scheduled (more effective than ondansetron for malignant "
        "bowel obstruction-related nausea). Continue ondansetron PRN. Consider octreotide if obstructive "
        "symptoms persist.\n"
        "3. Constipation: Start methylnaltrexone 8 mg SQ every other day for opioid-induced constipation. "
        "Continue senna/docusate.\n"
        "4. Nutrition: Comfort feeding per patient preference. No artificial nutrition per goals of care.\n"
        "5. Goals of care: Family meeting with palliative care team, patient, wife, and daughter completed. "
        "POLST signed -- comfort measures only. Plan for return to home hospice once symptoms stabilized."
    )

    docs = [
        ("doc-george-nakamura-hpi", "10164-2", "History of Present illness", hpi_text),
        ("doc-george-nakamura-ros", "10187-3", "Review of systems", ros_text),
        ("doc-george-nakamura-physical-exam", "29545-1", "Physical findings", pe_text),
        ("doc-george-nakamura-clinical-note", "11506-3", "Progress note", clinical_note_text),
    ]
    for doc_id, loinc, loinc_display, content_text in docs:
        write_resource("DocumentReference", {
            "resourceType": "DocumentReference",
            "id": doc_id,
            "status": "current",
            "type": {
                "coding": [{"system": "http://loinc.org", "code": loinc, "display": loinc_display}]
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
            "author": [{"display": "Dr. Lisa Yamamoto, MD - Palliative Medicine"}],
            "content": [{
                "attachment": {
                    "contentType": "text/plain",
                    "data": b64(content_text)
                }
            }]
        })


# ===========================================================================
# MAIN
# ===========================================================================
if __name__ == "__main__":
    print("Generating FHIR R4 resources for patients 7-9...")
    generate_sarah_obrien()
    generate_thomas_reeves()
    generate_george_nakamura()

    # Summary
    print("\n=== Generation Complete ===")
    total = 0
    for resource_type in ["Patient", "Condition", "MedicationRequest", "AllergyIntolerance",
                          "Observation", "Encounter", "DocumentReference", "Media"]:
        d = BASE_DIR / resource_type
        files = list(d.glob("*.json"))
        count = len(files)
        total += count
        print(f"  {resource_type}: {count} files")
    print(f"  TOTAL: {total} files")
