import streamlit as st
import requests
import json
import time

# ─── Configuration ───────────────────────────────────────────────
API_URL = "http://localhost:8000"

# ─── Page Config ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Healthcare AI Decision Support",
    page_icon="🏥",
    layout="wide"
)

# ─── Sidebar Navigation ──────────────────────────────────────────
st.sidebar.title("🏥 Healthcare AI")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["Submit Report", "Pending Reviews", "Review Detail", "History"]
)

# ═══════════════════════════════════════════════════════════════
# PAGE 1 — SUBMIT REPORT
# ═══════════════════════════════════════════════════════════════
if page == "Submit Report":
    st.title("📋 Submit Medical Report")
    st.markdown("Enter a patient medical report below to begin AI analysis.")

    report_text = st.text_area(
        "Patient Medical Report",
        height=250,
        placeholder="""Patient: John Doe
Age: 52
Blood Pressure: 155/95 mmHg
Fasting Glucose: 175 mg/dL
Total Cholesterol: 225 mg/dL
Symptoms: Occasional headaches, fatigue
Current Medications: None"""
    )

    if st.button("🚀 Submit for Analysis", type="primary"):
        if not report_text.strip():
            st.error("Please enter a medical report before submitting.")
        else:
            with st.spinner("Submitting report..."):
                try:
                    response = requests.post(
                        f"{API_URL}/reports/submit",
                        json={"report_text": report_text}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        report_id = data["report_id"]

                        st.success("Report submitted successfully!")
                        st.info(f"**Report ID:** `{report_id}`")
                        st.warning("The AI pipeline is now running in the background. This may take 20-40 minutes. Check **Pending Reviews** once complete.")

                        # Save report_id in session
                        st.session_state["last_report_id"] = report_id
                    else:
                        st.error(f"Submission failed: {response.text}")
                except Exception as e:
                    st.error(f"Could not connect to API: {e}")

    # Status checker
    st.markdown("---")
    st.subheader("🔍 Check Report Status")
    check_id = st.text_input("Enter Report ID to check status")

    if st.button("Check Status"):
        if check_id.strip():
            try:
                response = requests.get(f"{API_URL}/reports/{check_id}/status")
                if response.status_code == 200:
                    data = response.json()
                    status = data["status"]

                    if status == "processing":
                        st.warning(f"⏳ Status: **Processing** — Pipeline is still running")
                    elif status == "pending_review":
                        st.success(f"✅ Status: **Pending Review** — Go to Pending Reviews page")
                    elif status == "approved":
                        st.success(f"✅ Status: **Approved**")
                    elif status == "rejected":
                        st.error(f"❌ Status: **Rejected** — Pipeline re-triggered")
                    elif status == "failed":
                        st.error(f"❌ Status: **Failed** — Please resubmit")

                    st.caption(f"Submitted at: {data['submitted_at']}")
                else:
                    st.error("Report ID not found.")
            except Exception as e:
                st.error(f"Could not connect to API: {e}")


# ═══════════════════════════════════════════════════════════════
# PAGE 2 — PENDING REVIEWS
# ═══════════════════════════════════════════════════════════════
elif page == "Pending Reviews":
    st.title("⏳ Pending Reviews")
    st.markdown("Cases awaiting human review and approval.")

    if st.button("🔄 Refresh"):
        st.rerun()

    try:
        response = requests.get(f"{API_URL}/reviews/pending")
        if response.status_code == 200:
            data = response.json()
            reviews = data["pending_reviews"]

            if not reviews:
                st.info("No pending reviews at the moment.")
            else:
                st.success(f"**{data['count']} case(s) awaiting review**")

                for review in reviews:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.markdown(f"**Review ID:** `{review['review_id']}`")
                        with col2:
                            st.markdown(f"**Submitted:** {review['submitted_at']}")
                        with col3:
                            if st.button("Review →", key=review['review_id']):
                                st.session_state["selected_review_id"] = review['review_id']
                                st.info("Go to **Review Detail** page to view this case.")
                        st.markdown("---")
    except Exception as e:
        st.error(f"Could not connect to API: {e}")


# ═══════════════════════════════════════════════════════════════
# PAGE 3 — REVIEW DETAIL
# ═══════════════════════════════════════════════════════════════
elif page == "Review Detail":
    st.title("🔬 Review Detail")

    # Get review ID from session or manual input
    default_id = st.session_state.get("selected_review_id", "")
    review_id = st.text_input("Enter Review ID", value=default_id)

    if st.button("Load Review") or default_id:
        if review_id.strip():
            try:
                response = requests.get(f"{API_URL}/reviews/{review_id}")
                if response.status_code == 200:
                    review = response.json()

                    if review["status"] != "pending_review":
                        st.warning(f"This review is already **{review['status']}**")

                    st.markdown("---")

                    # ── Original Report ──
                    with st.expander("📄 Original Patient Report", expanded=False):
                        st.text(review.get("report_text", "Not available"))

                    agent_outputs = review.get("agent_outputs", {})

                    # ── Section 1: Patient Data ──
                    st.subheader("1️⃣ Extracted Patient Data")
                    patient_data = agent_outputs.get("report_analyzer", {})
                    if patient_data:
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Age", patient_data.get("age", "N/A"))
                        col2.metric(
                            "Blood Pressure",
                            patient_data.get("blood_pressure", "N/A"),
                            patient_data.get("blood_pressure_flag", "")
                        )
                        col3.metric(
                            "Glucose (mg/dL)",
                            patient_data.get("glucose", "N/A"),
                            patient_data.get("glucose_flag", "")
                        )
                        col4.metric(
                            "Cholesterol (mg/dL)",
                            patient_data.get("cholesterol", "N/A"),
                            patient_data.get("cholesterol_flag", "")
                        )
                    else:
                        st.info("Patient data not available")

                    st.markdown("---")

                    # ── Section 2: Guidelines ──
                    st.subheader("2️⃣ Retrieved Clinical Guidelines")
                    guidelines = agent_outputs.get("guideline_retriever", {})
                    if guidelines:
                        for key, value in guidelines.items():
                            condition = key.replace("_guidelines", "").title()
                            with st.expander(f"📖 {condition} Guidelines"):
                                st.write(value)
                    else:
                        st.info("Guidelines not available")

                    st.markdown("---")

                    # ── Section 3: Risk Assessment ──
                    st.subheader("3️⃣ Risk Assessment")
                    risk = agent_outputs.get("risk_explainer", {})
                    conditions = risk.get("conditions", [])
                    if conditions:
                        for condition in conditions:
                            risk_level = condition.get("risk_level", "Unknown")
                            color = "🔴" if risk_level == "High" else "🟡" if risk_level == "Moderate" else "🟢"
                            with st.expander(f"{color} {condition.get('condition')} — {risk_level} Risk"):
                                st.write(condition.get("explanation", ""))
                    else:
                        st.info("Risk assessment not available")

                    st.markdown("---")

                    # ── Section 4: Safety Validation ──
                    st.subheader("4️⃣ Safety Validation")
                    safety = agent_outputs.get("safety_validator", {})
                    issues = safety.get("issues", [])
                    if issues:
                        for issue in issues:
                            severity = issue.get("severity", "Unknown")
                            color = "🔴" if severity == "High" else "🟡"
                            with st.expander(f"{color} {issue.get('issue', '')}"):
                                st.markdown(f"**Severity:** {severity}")
                                st.markdown(f"**Recommendation:** {issue.get('recommendation', '')}")
                    else:
                        st.info("No safety issues identified")

                    st.markdown("---")

                    # ── Section 5: Reviewer Actions ──
                    if review["status"] == "pending_review":
                        st.subheader("5️⃣ Reviewer Action")

                        reviewer_notes = st.text_area(
                            "Reviewer Notes",
                            placeholder="Add your notes, observations, or reasons for approval/rejection...",
                            height=120
                        )

                        col1, col2 = st.columns(2)

                        with col1:
                            if st.button("✅ Approve", type="primary", use_container_width=True):
                                if not reviewer_notes.strip():
                                    st.error("Please add reviewer notes before approving.")
                                else:
                                    try:
                                        res = requests.post(
                                            f"{API_URL}/reviews/{review_id}/approve",
                                            json={
                                                "reviewer_notes": reviewer_notes,
                                                "modified_output": None
                                            }
                                        )
                                        if res.status_code == 200:
                                            st.success("✅ Review approved successfully!")
                                            st.session_state["selected_review_id"] = ""
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error(f"Approval failed: {res.text}")
                                    except Exception as e:
                                        st.error(f"Error: {e}")

                        with col2:
                            if st.button("❌ Reject", type="secondary", use_container_width=True):
                                if not reviewer_notes.strip():
                                    st.error("Please add rejection reason before rejecting.")
                                else:
                                    try:
                                        res = requests.post(
                                            f"{API_URL}/reviews/{review_id}/reject",
                                            json={"reviewer_notes": reviewer_notes}
                                        )
                                        if res.status_code == 200:
                                            st.error("❌ Review rejected. Pipeline re-triggered with your feedback.")
                                            st.session_state["selected_review_id"] = ""
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error(f"Rejection failed: {res.text}")
                                    except Exception as e:
                                        st.error(f"Error: {e}")

                else:
                    st.error("Review not found.")
            except Exception as e:
                st.error(f"Could not connect to API: {e}")


# ═══════════════════════════════════════════════════════════════
# PAGE 4 — HISTORY
# ═══════════════════════════════════════════════════════════════
elif page == "History":
    st.title("📚 Review History")
    st.markdown("All completed reviews.")

    if st.button("🔄 Refresh"):
        st.rerun()

    try:
        response = requests.get(f"{API_URL}/reviews/history")
        if response.status_code == 200:
            data = response.json()
            history = data["history"]

            if not history:
                st.info("No completed reviews yet.")
            else:
                st.success(f"**{data['count']} completed review(s)**")

                for item in history:
                    status_icon = "✅" if item["status"] == "approved" else "❌"
                    with st.expander(
                        f"{status_icon} Review `{item['review_id']}` — {item['status'].upper()}"
                    ):
                        col1, col2 = st.columns(2)
                        col1.markdown(f"**Report ID:** `{item['report_id']}`")
                        col2.markdown(f"**Reviewed at:** {item['reviewed_at']}")
                        st.markdown(f"**Reviewer Notes:** {item['reviewer_notes']}")
        else:
            st.error("Could not fetch history.")
    except Exception as e:
        st.error(f"Could not connect to API: {e}")