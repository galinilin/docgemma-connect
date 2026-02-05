# Claude Code Prompt: Medplum EHR Integration

Implement Medplum FHIR integration for the DocGemma agent. We're using the hosted Medplum at app.medplum.com.

## Context

DocGemma Connect is a medical AI agent for healthcare professionals. We need EHR tools that integrate with Medplum's FHIR R4 API. The tools must return **minified output** suitable for a 4B parameter model (not raw FHIR JSON).

## Environment Setup

```python
# Required env vars
MEDPLUM_CLIENT_ID=...
MEDPLUM_CLIENT_SECRET=...
MEDPLUM_BASE_URL=https://api.medplum.com/fhir/R4
```

## Tools to Implement

Create these 5 MCP tools in the tools directory:

### 1. `search_patient`
Find patients by name or date of birth.

```python
@mcp.tool
async def search_patient(name: str = None, dob: str = None) -> str:
    """
    Search for patients by name or date of birth.
    Returns a list of matching patients with their IDs.
    
    Args:
        name: Patient name (partial match supported)
        dob: Date of birth in YYYY-MM-DD format
    """
```

FHIR: `GET /Patient?name={name}&birthdate={dob}`

Output format (minified):
```
Found 2 patients:
1. John Smith (ID: abc-123) DOB: 1978-03-15
2. John Smithson (ID: def-456) DOB: 1982-07-22
```

### 2. `get_patient_chart`
Retrieve full clinical context in ONE call using `_revinclude`.

```python
@mcp.tool
async def get_patient_chart(patient_id: str) -> str:
    """
    Retrieves the FULL clinical context for a patient.
    Includes: demographics, active conditions, current medications, allergies, recent labs.
    Use this immediately after identifying the patient.
    
    Args:
        patient_id: The FHIR Patient resource ID
    """
```

FHIR (single call):
```
GET /Patient/{id}?_revinclude=Condition:subject
                 &_revinclude=MedicationRequest:subject
                 &_revinclude=AllergyIntolerance:patient
```

Then separate call for recent labs:
```
GET /Observation?subject={id}&category=laboratory&_count=20&_sort=-date
```

Output format (minified for 4B model):
```
PATIENT: John Smith (ID: abc-123)
DOB: 1978-03-15 | Sex: Male

CONDITIONS:
- Atrial Fibrillation (active)
- Hypertension (active)
- Type 2 Diabetes (active)

MEDICATIONS:
- Warfarin 5mg daily (active)
- Metformin 1000mg BID (active)
- Lisinopril 10mg daily (active)

ALLERGIES:
- Penicillin (severe) - Anaphylaxis

RECENT LABS (last 30 days):
- INR: 2.3 (2026-02-01)
- HbA1c: 7.2% (2026-01-15)
- Creatinine: 1.1 mg/dL (2026-01-15)
```

### 3. `add_allergy`
Document a new allergy.

```python
@mcp.tool
async def add_allergy(
    patient_id: str, 
    substance: str, 
    reaction: str, 
    severity: str = "moderate"
) -> str:
    """
    Document a new allergy in the patient's chart.
    
    Args:
        patient_id: The FHIR Patient resource ID
        substance: The allergen (e.g., "Penicillin", "Sulfa")
        reaction: The reaction type (e.g., "Anaphylaxis", "Rash", "Hives")
        severity: "mild", "moderate", or "severe"
    """
```

FHIR: `POST /AllergyIntolerance`
```json
{
  "resourceType": "AllergyIntolerance",
  "clinicalStatus": {
    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]
  },
  "verificationStatus": {
    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]
  },
  "patient": {"reference": "Patient/{patient_id}"},
  "code": {"text": "{substance}"},
  "reaction": [{
    "manifestation": [{"text": "{reaction}"}],
    "severity": "{severity}"
  }],
  "recordedDate": "{ISO timestamp}"
}
```

Output: `✅ Allergy documented: {substance} ({severity}) for Patient {patient_id}`

### 4. `prescribe_medication`
Write a new prescription.

```python
@mcp.tool
async def prescribe_medication(
    patient_id: str, 
    medication_name: str, 
    dosage: str,
    frequency: str
) -> str:
    """
    Write a new prescription (MedicationRequest) to the EHR.
    ONLY use this if the clinician explicitly confirms the order.
    
    Args:
        patient_id: The FHIR Patient resource ID
        medication_name: Drug name (e.g., "Lisinopril")
        dosage: Dose amount (e.g., "10mg")
        frequency: How often (e.g., "once daily", "BID", "TID")
    """
```

FHIR: `POST /MedicationRequest`
```json
{
  "resourceType": "MedicationRequest",
  "status": "active",
  "intent": "order",
  "medicationCodeableConcept": {"text": "{medication_name} {dosage}"},
  "subject": {"reference": "Patient/{patient_id}"},
  "dosageInstruction": [{"text": "{dosage} {frequency}"}],
  "authoredOn": "{ISO timestamp}"
}
```

Output: `✅ Prescribed: {medication_name} {dosage} {frequency} for Patient {patient_id} (Order ID: {id})`

### 5. `save_clinical_note`
Save AI analysis to the EHR as an audit trail.

```python
@mcp.tool
async def save_clinical_note(
    patient_id: str, 
    note_text: str,
    note_type: str = "clinical-note"
) -> str:
    """
    Save a clinical note or AI consultation summary to the patient's chart.
    Use this to document AI-assisted analysis and recommendations.
    
    Args:
        patient_id: The FHIR Patient resource ID
        note_text: The clinical note content
        note_type: Type of note ("clinical-note", "consultation", "assessment")
    """
```

FHIR: `POST /DocumentReference`
```json
{
  "resourceType": "DocumentReference",
  "status": "current",
  "type": {
    "coding": [{"system": "http://loinc.org", "code": "11506-3", "display": "Progress note"}]
  },
  "subject": {"reference": "Patient/{patient_id}"},
  "date": "{ISO timestamp}",
  "author": [{"display": "DocGemma AI Assistant"}],
  "content": [{
    "attachment": {
      "contentType": "text/plain",
      "data": "{base64 encoded note_text}"
    }
  }]
}
```

Output: `✅ Note saved to Patient {patient_id}'s chart (Doc ID: {id})`

## Implementation Requirements

1. **Authentication**: Implement OAuth2 client credentials flow for Medplum
   ```python
   async def get_medplum_token() -> str:
       # POST to https://api.medplum.com/oauth2/token
       # with client_id, client_secret, grant_type=client_credentials
   ```

2. **Error handling**: Return clear error messages, not stack traces
   ```
   ❌ Patient not found: No patient with ID xyz-789
   ❌ EHR rejected order: Missing required field 'dosage'
   ```

3. **Minification**: Strip all FHIR metadata bloat. Only return clinically relevant text. The 4B model cannot handle raw FHIR JSON.

4. **Use httpx**: For async HTTP calls to Medplum API

## File Structure

```
docgemma/tools/
├── medplum/
│   ├── __init__.py
│   ├── client.py        # Auth, token management, base HTTP
│   ├── search.py        # search_patient
│   ├── chart.py         # get_patient_chart  
│   ├── allergies.py     # add_allergy
│   ├── medications.py   # prescribe_medication
│   └── notes.py         # save_clinical_note
```

## Testing

After implementation, test with this sequence:
```
1. search_patient(name="Smith")
2. get_patient_chart(patient_id="...")
3. add_allergy(patient_id="...", substance="Sulfa", reaction="Rash", severity="moderate")
4. prescribe_medication(patient_id="...", medication_name="Lisinopril", dosage="10mg", frequency="once daily")
5. save_clinical_note(patient_id="...", note_text="AI assessment: Patient stable, new allergy documented.")
```

Verify writes appear in Medplum dashboard at app.medplum.com.
