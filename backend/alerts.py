from datetime import datetime

# ─── Alert Configuration ─────────────────────────────────────────
REVIEW_BASE_URL = "http://localhost:8501"  # Streamlit frontend URL

# ─── Main Alert Function ─────────────────────────────────────────

def send_alert(review_id: str, report_id: str, agent_outputs: dict) -> None:
    """
    Send alert to reviewer when a new report is ready for review.
    Currently prints to console.
    Structured to easily swap in email/Slack/SMS later.
    """
    alert_message = _build_alert_message(review_id, report_id, agent_outputs)
    _console_alert(alert_message)

    # Future: uncomment to enable other channels
    # _email_alert(alert_message)
    # _slack_alert(alert_message)


def _build_alert_message(review_id: str, report_id: str, agent_outputs: dict) -> dict:
    """Build the alert message payload."""

    # Extract key info for the alert
    patient_data = agent_outputs.get("patient_data", {})
    risk_assessment = agent_outputs.get("risk_assessment", {})

    # Get highest risk level
    conditions = risk_assessment.get("conditions", [])
    high_risk_conditions = [
        c["condition"] for c in conditions
        if c.get("risk_level") == "High"
    ]

    return {
        "review_id": review_id,
        "report_id": report_id,
        "review_url": f"{REVIEW_BASE_URL}?page=review&review_id={review_id}",
        "timestamp": datetime.utcnow().isoformat(),
        "patient_age": patient_data.get("age", "Unknown"),
        "high_risk_conditions": high_risk_conditions,
        "total_conditions": len(conditions),
        "urgency": "HIGH" if high_risk_conditions else "NORMAL"
    }


def _console_alert(message: dict) -> None:
    """Print alert to console — current implementation."""
    print("\n" + "="*60)
    print("🚨 NEW MEDICAL REPORT READY FOR REVIEW")
    print("="*60)
    print(f"  Review ID    : {message['review_id']}")
    print(f"  Report ID    : {message['report_id']}")
    print(f"  Patient Age  : {message['patient_age']}")
    print(f"  Urgency      : {message['urgency']}")
    print(f"  High Risk    : {', '.join(message['high_risk_conditions']) or 'None'}")
    print(f"  Timestamp    : {message['timestamp']}")
    print(f"  Review URL   : {message['review_url']}")
    print("="*60 + "\n")


# ─── Future Alert Channels ───────────────────────────────────────

def _email_alert(message: dict) -> None:
    """
    Email alert — uncomment and configure when ready.
    Requires: pip install secure-smtplib
    """
    # import smtplib
    # from email.message import EmailMessage
    # msg = EmailMessage()
    # msg['Subject'] = f"[URGENT] Medical Review Required - {message['review_id']}"
    # msg['From'] = 'system@yourdomain.com'
    # msg['To'] = 'reviewer@yourdomain.com'
    # msg.set_content(f"""
    # New medical report requires your review.
    # Review ID : {message['review_id']}
    # Urgency   : {message['urgency']}
    # Link      : {message['review_url']}
    # """)
    # with smtplib.SMTP('smtp.yourdomain.com') as smtp:
    #     smtp.send_message(msg)
    pass


def _slack_alert(message: dict) -> None:
    """
    Slack webhook alert — uncomment and configure when ready.
    Requires: pip install slack-sdk
    """
    # import requests
    # webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    # payload = {
    #     "text": f"🚨 New medical report ready for review!\n"
    #             f"Review ID: {message['review_id']}\n"
    #             f"Urgency: {message['urgency']}\n"
    #             f"Link: {message['review_url']}"
    # }
    # requests.post(webhook_url, json=payload)
    pass