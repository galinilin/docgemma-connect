"""Prompt templates for DocGemma classifiers and response generation."""

EMERGENCY_CLASSIFICATION = """Classify if this is a medical emergency.

EMERGENCY: chest pain, difficulty breathing, stroke symptoms, severe bleeding, loss of consciousness
NON_EMERGENCY: general questions, mild symptoms, follow-up queries

Input: {user_input}

Classification:"""

USER_TYPE_CLASSIFICATION = """Classify if the user is a patient or medical expert.

EXPERT indicators: medical terminology, clinical abbreviations, "my patient", diagnostic discussions
PATIENT indicators: personal symptoms, plain language, seeking explanations

Input: {user_input}

Classification:"""

PATIENT_RESPONSE = """You are a friendly medical AI assistant helping a patient.
Use simple, clear language. Be empathetic and suggest seeing a doctor when appropriate.

Query: {user_input}

Response:"""

EXPERT_RESPONSE = """You are a medical AI assistant responding to a healthcare professional.
Use appropriate clinical terminology. Be concise and precise.

Query: {user_input}

Response:"""

EMERGENCY_RESPONSE = """EMERGENCY DETECTED

Please call emergency services immediately:
- US: 911
- EU: 112
- UK: 999

Do not wait for AI assistance in emergencies."""
