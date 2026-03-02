from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import os

# ─── Database Configuration ──────────────────────────────────────
DATABASE_URL = "sqlite:///./database/medical_reviews.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ─── Models ──────────────────────────────────────────────────────

class Report(Base):
    __tablename__ = "reports"

    report_id       = Column(String, primary_key=True)
    raw_report_text = Column(Text, nullable=False)
    submitted_at    = Column(String, nullable=False)
    status          = Column(String, default="processing")
    # Status values: processing, pending_review, approved, rejected


class AgentOutput(Base):
    __tablename__ = "agent_outputs"

    output_id    = Column(String, primary_key=True)
    report_id    = Column(String, nullable=False)
    agent_name   = Column(String, nullable=False)
    output_json  = Column(Text, nullable=False)
    created_at   = Column(String, nullable=False)


class Review(Base):
    __tablename__ = "reviews"

    review_id       = Column(String, primary_key=True)
    report_id       = Column(String, nullable=False)
    status          = Column(String, default="pending_review")
    reviewer_notes  = Column(Text, nullable=True)
    modified_output = Column(Text, nullable=True)
    reviewed_at     = Column(String, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id     = Column(String, primary_key=True)
    report_id  = Column(String, nullable=False)
    action     = Column(String, nullable=False)
    details    = Column(Text, nullable=True)
    timestamp  = Column(String, nullable=False)


# ─── Initialize Database ─────────────────────────────────────────

def init_db():
    """Create all tables if they don't exist."""
    os.makedirs("./database", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully.")


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Report Operations ───────────────────────────────────────────

def save_report(report_id: str, raw_report_text: str) -> None:
    db = SessionLocal()
    try:
        report = Report(
            report_id=report_id,
            raw_report_text=raw_report_text,
            submitted_at=datetime.utcnow().isoformat(),
            status="processing"
        )
        db.add(report)
        db.commit()
        log_action(report_id, "report_submitted", "Report received and processing started")
    finally:
        db.close()


def update_report_status(report_id: str, status: str) -> None:
    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.report_id == report_id).first()
        if report:
            report.status = status
            db.commit()
            log_action(report_id, f"status_updated", f"Status changed to {status}")
    finally:
        db.close()


def get_report(report_id: str) -> dict:
    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.report_id == report_id).first()
        if not report:
            return None
        return {
            "report_id": report.report_id,
            "raw_report_text": report.raw_report_text,
            "submitted_at": report.submitted_at,
            "status": report.status
        }
    finally:
        db.close()


# ─── Agent Output Operations ─────────────────────────────────────

def save_agent_output(report_id: str, agent_name: str, output: dict) -> None:
    import uuid
    db = SessionLocal()
    try:
        agent_output = AgentOutput(
            output_id=str(uuid.uuid4()),
            report_id=report_id,
            agent_name=agent_name,
            output_json=json.dumps(output),
            created_at=datetime.utcnow().isoformat()
        )
        db.add(agent_output)
        db.commit()
        log_action(report_id, "agent_output_saved", f"Output saved for agent: {agent_name}")
    finally:
        db.close()


def get_agent_outputs(report_id: str) -> dict:
    db = SessionLocal()
    try:
        outputs = db.query(AgentOutput).filter(
            AgentOutput.report_id == report_id
        ).all()
        return {
            o.agent_name: json.loads(o.output_json)
            for o in outputs
        }
    finally:
        db.close()


# ─── Review Operations ───────────────────────────────────────────

def save_review(report_id: str, review_id: str) -> None:
    db = SessionLocal()
    try:
        review = Review(
            review_id=review_id,
            report_id=report_id,
            status="pending_review"
        )
        db.add(review)
        db.commit()
        log_action(report_id, "review_created", f"Review {review_id} created and pending")
    finally:
        db.close()


def get_pending_reviews() -> list:
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(
            Review.status == "pending_review"
        ).all()
        results = []
        for r in reviews:
            report = db.query(Report).filter(
                Report.report_id == r.report_id
            ).first()
            results.append({
                "review_id": r.review_id,
                "report_id": r.report_id,
                "status": r.status,
                "submitted_at": report.submitted_at if report else None
            })
        return results
    finally:
        db.close()


def get_review_detail(review_id: str) -> dict:
    db = SessionLocal()
    try:
        review = db.query(Review).filter(
            Review.review_id == review_id
        ).first()
        if not review:
            return None

        # Get agent outputs for this report
        outputs = get_agent_outputs(review.report_id)
        report = get_report(review.report_id)

        return {
            "review_id": review.review_id,
            "report_id": review.report_id,
            "status": review.status,
            "reviewer_notes": review.reviewer_notes,
            "modified_output": json.loads(review.modified_output) if review.modified_output else None,
            "reviewed_at": review.reviewed_at,
            "report_text": report["raw_report_text"] if report else None,
            "agent_outputs": outputs
        }
    finally:
        db.close()


def approve_review(review_id: str, reviewer_notes: str, modified_output: dict = None) -> None:
    db = SessionLocal()
    try:
        review = db.query(Review).filter(
            Review.review_id == review_id
        ).first()
        if review:
            review.status = "approved"
            review.reviewer_notes = reviewer_notes
            review.modified_output = json.dumps(modified_output) if modified_output else None
            review.reviewed_at = datetime.utcnow().isoformat()
            db.commit()
            update_report_status(review.report_id, "approved")
            log_action(review.report_id, "review_approved", f"Review {review_id} approved")
    finally:
        db.close()


def reject_review(review_id: str, reviewer_notes: str) -> None:
    db = SessionLocal()
    try:
        review = db.query(Review).filter(
            Review.review_id == review_id
        ).first()
        if review:
            review.status = "rejected"
            review.reviewer_notes = reviewer_notes
            review.reviewed_at = datetime.utcnow().isoformat()
            db.commit()
            update_report_status(review.report_id, "rejected")
            log_action(review.report_id, "review_rejected", f"Review {review_id} rejected")
    finally:
        db.close()


def get_review_history() -> list:
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(
            Review.status.in_(["approved", "rejected"])
        ).all()
        return [
            {
                "review_id": r.review_id,
                "report_id": r.report_id,
                "status": r.status,
                "reviewer_notes": r.reviewer_notes,
                "reviewed_at": r.reviewed_at
            }
            for r in reviews
        ]
    finally:
        db.close()


# ─── Audit Log Operations ────────────────────────────────────────

def log_action(report_id: str, action: str, details: str = None) -> None:
    import uuid
    db = SessionLocal()
    try:
        log = AuditLog(
            log_id=str(uuid.uuid4()),
            report_id=report_id,
            action=action,
            details=details,
            timestamp=datetime.utcnow().isoformat()
        )
        db.add(log)
        db.commit()
    finally:
        db.close()


def get_audit_log(report_id: str) -> list:
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).filter(
            AuditLog.report_id == report_id
        ).order_by(AuditLog.timestamp).all()
        return [
            {
                "action": l.action,
                "details": l.details,
                "timestamp": l.timestamp
            }
            for l in logs
        ]
    finally:
        db.close()


if __name__ == "__main__":
    init_db()