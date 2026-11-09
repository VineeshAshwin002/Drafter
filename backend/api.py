"""HTTP API for the email LangGraph workflow.

Run from the repository root:
    uvicorn backend.api:app --reload
"""

from pathlib import Path
from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .email_graph import resume_email_workflow, start_email_workflow


app = FastAPI(title="Email Creator API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)
EMAIL_OUTPUT_DIR = Path("generated_emails")
EMAIL_OUTPUT_DIR.mkdir(exist_ok=True)


class CreateEmailRequest(BaseModel):
    user_request: str = Field(min_length=1)
    filename: str | None = None


class ReviewRequest(BaseModel):
    answer: str
    request: str = ""


def workflow_response(thread_id: str, result: dict) -> dict:
    if "__interrupt__" in result:
        interrupt_value = result["__interrupt__"][0]
        question = getattr(interrupt_value, "value", interrupt_value)
        if isinstance(question, dict) and "value" in question:
            question = question["value"]
        return {
            "thread_id": thread_id,
            "status": "awaiting_update_confirmation",
            "question": question,
            "email_draft": result.get("email_draft", ""),
        }
    return {
        "thread_id": thread_id,
        "status": result["status"],
        "email_draft": result.get("email_draft", ""),
        "filename": result.get("filename", ""),
    }


@app.post("/emails")
def create_email(request: CreateEmailRequest) -> dict:
    filename = Path(request.filename or "generated_email.txt").name
    output_path = str(EMAIL_OUTPUT_DIR / filename)
    thread_id, result = start_email_workflow(request.user_request, output_path)
    return workflow_response(thread_id, result)


@app.post("/emails/{thread_id}/review")
def review_email(thread_id: str, request: ReviewRequest) -> dict:
    if request.answer.strip().lower() in {"yes", "y"} and not request.request.strip():
        raise HTTPException(
            status_code=422,
            detail="An update request is required when the answer is yes.",
        )
    try:
        result = resume_email_workflow(thread_id, request.model_dump())
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return workflow_response(thread_id, result)
