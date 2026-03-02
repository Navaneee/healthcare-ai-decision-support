from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.database import (
    init_db, save_report, get_report,
    update_report_status, get_agent_outputs,
    save_review, get_pending_reviews,
    get_review_detail, approve_review,
    reject_review, get_review_history,
    get_audit_log
)
from backend.alerts import send_alert

# ─── App Setup ───────────────────────────────────────────────────
app = FastAPI(
    title="Healthcare AI Decision Support API",
    description="Multi-agent medical report analysis system",
    version="1.0.0"
)

# Allow Streamlit to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()
    print("FastAPI started — Database initialized")

# ─── Request Models ───────────────────────────────────────────────

class ReportSubmission(BaseModel):
    report_text: str

class ApprovalPayload(BaseModel):
    reviewer_notes: str
    modified_output: Optional[dict] = None

class RejectionPayload(BaseModel):
    reviewer_notes: str

# ─── Background Task — Run CrewAI Pipeline ───────────────────────

def run_pipeline_background(report_id: str, report_text: str):
    """
    Runs the full CrewAI pipeline in the background.
    Called automatically after report submission.
    """
    try:
        import json
        import re
        from medical_analysis.crew import MedicalAnalysisCrew

        def clean_json(raw):
            try:
                cleaned = re.sub(r'```json\s*', '', raw)
                cleaned = re.sub(r'```\s*', '', cleaned)
                return json.loads(cleaned.strip())
            except:
                return {"raw_output": raw}

        # Run the crew
        inputs = {'report_text': report_text}
        result = MedicalAnalysisCrew().crew().kickoff(inputs=inputs)

        # Parse outputs
        outputs = {}
        try:
            outputs["patient_data"] = clean_json(str(result.tasks_output[0]))
            outputs["guidelines"] = clean_json(str(result.tasks_output[1]))
            outputs["risk_assessment"] = clean_json(str(result.tasks_output[2]))
            outputs["safety_validation"] = clean_json(str(result.tasks_output[3]))
        except Exception as e:
            outputs["final_output"] = clean_json(str(result.raw))

        # Save agent outputs to database
        agent_map = {
            "patient_data": "report_analyzer",
            "guidelines": "guideline_retriever",
            "risk_assessment": "risk_explainer",
            "safety_validation": "safety_validator"
        }
        for key, agent_name in agent_map.items():
            if key in outputs:
                from backend.database import save_agent_output
                save_agent_output(report_id, agent_name, outputs[key])

        # Create review and send alert
        review_id = str(uuid.uuid4())
        update_report_status(report_id, "pending_review")
        save_review(report_id, review_id)
        send_alert(review_id, report_id, outputs)

        print(f"Pipeline complete for report {report_id}")
        print(f"Review ID: {review_id}")

    except Exception as e:
        update_report_status(report_id, "failed")
        print(f"Pipeline failed for report {report_id}: {e}")


# ─── API Endpoints ───────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Healthcare AI Decision Support API is running"}


@app.post("/reports/submit")
def submit_report(payload: ReportSubmission, background_tasks: BackgroundTasks):
    """
    Submit a new patient report for analysis.
    Immediately returns report_id while pipeline runs in background.
    """
    if not payload.report_text.strip():
        raise HTTPException(status_code=400, detail="Report text cannot be empty")

    report_id = str(uuid.uuid4())

    # Save report to database immediately
    save_report(report_id, payload.report_text)

    # Run CrewAI pipeline in background
    background_tasks.add_task(
        run_pipeline_background,
        report_id,
        payload.report_text
    )

    return {
        "message": "Report submitted successfully",
        "report_id": report_id,
        "status": "processing"
    }


@app.get("/reports/{report_id}/status")
def get_report_status(report_id: str):
    """Check the processing status of a submitted report."""
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "report_id": report_id,
        "status": report["status"],
        "submitted_at": report["submitted_at"]
    }


@app.get("/reviews/pending")
def list_pending_reviews():
    """Get all reviews awaiting human approval."""
    reviews = get_pending_reviews()
    return {"pending_reviews": reviews, "count": len(reviews)}


@app.get("/reviews/history")
def list_review_history():
    """Get all completed reviews."""
    history = get_review_history()
    return {"history": history, "count": len(history)}


@app.get("/reviews/{review_id}")
def get_review(review_id: str):
    """Get full detail of a specific review including all agent outputs."""
    review = get_review_detail(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.post("/reviews/{review_id}/approve")
def approve(review_id: str, payload: ApprovalPayload):
    """Approve a review with optional modifications."""
    review = get_review_detail(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review["status"] != "pending_review":
        raise HTTPException(status_code=400, detail="Review is not pending")

    approve_review(review_id, payload.reviewer_notes, payload.modified_output)
    return {
        "message": "Review approved successfully",
        "review_id": review_id
    }


@app.post("/reviews/{review_id}/reject")
def reject(review_id: str, payload: RejectionPayload, background_tasks: BackgroundTasks):
    """
    Reject a review.
    Automatically re-triggers the pipeline with reviewer feedback.
    """
    review = get_review_detail(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")