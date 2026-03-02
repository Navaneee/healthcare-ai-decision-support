#!/usr/bin/env python
import json
import re
import uuid
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from medical_analysis.crew import MedicalAnalysisCrew
from backend.database import (
    init_db, save_report, save_agent_output,
    save_review, update_report_status
)
from backend.alerts import send_alert


# ─── JSON Cleaner ────────────────────────────────────────────────
def clean_json_output(raw_output: str) -> dict:
    try:
        cleaned = re.sub(r'```json\s*', '', raw_output)
        cleaned = re.sub(r'```\s*', '', cleaned)
        cleaned = cleaned.strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw_output": raw_output}


# ─── Main Pipeline Runner ────────────────────────────────────────
def run(report_text: str = None) -> dict:
    # Initialize database
    init_db()

    if report_text is None:
        report_text = """
        Patient: John Doe
        Age: 52
        Blood Pressure: 155/95 mmHg
        Fasting Glucose: 175 mg/dL
        Total Cholesterol: 225 mg/dL
        Symptoms: Occasional headaches, fatigue, blurred vision
        Current Medications: None
        """

    # Generate IDs
    report_id = str(uuid.uuid4())
    review_id = str(uuid.uuid4())

    print("\n" + "="*50)
    print("Starting Medical Analysis Pipeline")
    print(f"Report ID: {report_id}")
    print("="*50 + "\n")

    # Save report to database
    save_report(report_id, report_text)

    # Run the crew
    inputs = {'report_text': report_text}
    result = MedicalAnalysisCrew().crew().kickoff(inputs=inputs)

    # Parse individual task outputs
    outputs = {}
    try:
        outputs["patient_data"] = clean_json_output(
            str(result.tasks_output[0]) if result.tasks_output else ""
        )
        outputs["guidelines"] = clean_json_output(
            str(result.tasks_output[1]) if len(result.tasks_output) > 1 else ""
        )
        outputs["risk_assessment"] = clean_json_output(
            str(result.tasks_output[2]) if len(result.tasks_output) > 2 else ""
        )
        outputs["safety_validation"] = clean_json_output(
            str(result.tasks_output[3]) if len(result.tasks_output) > 3 else ""
        )
    except Exception as e:
        print(f"Warning: Could not parse individual outputs — {e}")
        outputs["final_output"] = clean_json_output(str(result.raw))

    # Save each agent output to database
    agent_map = {
        "patient_data": "report_analyzer",
        "guidelines": "guideline_retriever",
        "risk_assessment": "risk_explainer",
        "safety_validation": "safety_validator"
    }
    for key, agent_name in agent_map.items():
        if key in outputs:
            save_agent_output(report_id, agent_name, outputs[key])

    # Update report status and create review
    update_report_status(report_id, "pending_review")
    save_review(report_id, review_id)

    # Send alert to reviewer
    send_alert(review_id, report_id, outputs)

    print("\n" + "="*50)
    print("Pipeline Complete!")
    print(f"Review ID: {review_id}")
    print("="*50)
    print("\nFinal Output:")
    print(json.dumps(outputs, indent=2))

    return {
        "report_id": report_id,
        "review_id": review_id,
        "outputs": outputs
    }


def train():
    print("Training not implemented yet.")

def replay():
    print("Replay not implemented yet.")

def test():
    print("Test not implemented yet.")

def run_with_trigger():
    run()


if __name__ == "__main__":
    run()