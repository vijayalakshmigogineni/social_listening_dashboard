"""
Zero-shot classification service for the Social Listening Dashboard.

Runs the same model and call the backend used in-process
(backend/app/analysis/model_registry.py), so scores are unchanged.
"""

import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from transformers import pipeline

MODEL_NAME = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
API_KEY = os.getenv("SPACE_API_KEY", "")

classifier = pipeline("zero-shot-classification", model=MODEL_NAME)
app = FastAPI(title="Zero-shot classifier")


class ClassifyRequest(BaseModel):
    text: str
    hypotheses: list[str]


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/classify")
def classify(req: ClassifyRequest, authorization: str = Header(default="")):
    if API_KEY and authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="invalid api key")
    if not req.hypotheses:
        raise HTTPException(status_code=422, detail="hypotheses must not be empty")
    # hypothesis_template="{}": hypotheses are already full NLI sentences.
    result = classifier(req.text, req.hypotheses, hypothesis_template="{}", multi_label=False)
    return {"labels": result["labels"], "scores": result["scores"]}
