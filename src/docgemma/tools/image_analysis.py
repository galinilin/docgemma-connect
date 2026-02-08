"""Medical image analysis tool using MedGemma vision.

Sends the image to the vLLM endpoint via OpenAI-compatible vision API
and returns the model's clinical analysis.
"""

from __future__ import annotations

import base64
import os

import httpx

from .schemas import ImageAnalysisInput, ImageAnalysisOutput

REQUEST_TIMEOUT = 120.0  # Vision inference can be slow

VISION_SYSTEM_PROMPT = (
    "You are a clinical imaging assistant for healthcare professionals. "
    "Analyze medical images and provide detailed, structured findings. "
    "Identify the imaging modality, anatomical region, key observations, "
    "and any abnormalities. Use standard radiological terminology."
)

DEFAULT_QUERY = (
    "Describe this medical image in detail. "
    "Identify the imaging modality, anatomical region, and any notable findings."
)


async def analyze_medical_image(input_data: ImageAnalysisInput) -> ImageAnalysisOutput:
    """Analyze a medical image using MedGemma vision.

    Sends image to vLLM endpoint as base64 in OpenAI vision format.
    Returns model's clinical analysis of the image.
    """
    endpoint = os.environ.get("DOCGEMMA_ENDPOINT", "").rstrip("/")
    api_key = os.environ.get("DOCGEMMA_API_KEY", "")
    model_id = os.environ.get("DOCGEMMA_MODEL", "google/medgemma-1.5-4b-it")
    query = input_data.query or DEFAULT_QUERY

    if not endpoint:
        return ImageAnalysisOutput(
            findings="",
            query=query,
            error="DOCGEMMA_ENDPOINT not configured",
        )

    # Encode image to base64
    image_b64 = base64.b64encode(input_data.image_data).decode("utf-8")

    # Build OpenAI vision API messages with system priming
    messages = [
        {"role": "system", "content": VISION_SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            {"type": "text", "text": query},
        ]},
    ]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model_id,
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.3,
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{endpoint}/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            findings = resp.json()["choices"][0]["message"]["content"]
            return ImageAnalysisOutput(findings=findings, query=query, error=None)

    except httpx.TimeoutException:
        return ImageAnalysisOutput(
            findings="",
            query=query,
            error=f"Vision inference timed out after {REQUEST_TIMEOUT}s",
        )
    except Exception as e:
        return ImageAnalysisOutput(
            findings="",
            query=query,
            error=f"{type(e).__name__}: {e}",
        )
