import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import JobListing, ApplicationRecord, FollowUpTask, EmailMessage
from app.services.cleanup_service import run_mock_and_seed_cleanup

@pytest.fixture
def cleanup_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed job + app + follow up task (has mock email only)
    j1 = JobListing(id=1, title="Seed Job", company_name="Corp A", original_url="https://a.com", description="d", is_seed=True)
    session.add(j1)
    a1 = ApplicationRecord(id=1, job_id=1, current_status="DISCOVERED")
    session.add(a1)
    em1 = EmailMessage(id=1, application_id=1, direction="outbound", sender="a@b.com", recipient="c@d.com", subject="s", body_text="b", provider="mock_smtp", status="SENT")
    session.add(em1)
    t1 = FollowUpTask(id=1, application_id=1, follow_up_sequence=1, due_date=datetime.now(timezone.utc), status="SCHEDULED")
    session.add(t1)

    # Non-seed job + app + follow up task (has real email with message_id)
    j2 = JobListing(id=2, title="Live Job", company_name="Corp B", original_url="https://b.com", description="d", is_seed=False)
    session.add(j2)
    a2 = ApplicationRecord(id=2, job_id=2, current_status="EMAIL_SENT")
    session.add(a2)
    em2 = EmailMessage(id=2, application_id=2, direction="outbound", sender="a@b.com", recipient="c@d.com", subject="s", body_text="b", provider="GMAIL_API", status="SENT", message_id_header="18d348a0f8b1a2c3")
    session.add(em2)
    t2 = FollowUpTask(id=2, application_id=2, follow_up_sequence=1, due_date=datetime.now(timezone.utc), status="SCHEDULED")
    session.add(t2)

    session.commit()
    yield session
    session.close()

def test_mock_followup_and_seed_cleanup(cleanup_test_db):
    res = run_mock_and_seed_cleanup(cleanup_test_db, delete_seed_apps=False)

    # t1 had mock email -> CANCELLED_MOCK
    t1 = cleanup_test_db.query(FollowUpTask).filter_by(id=1).first()
    assert t1.status == "CANCELLED_MOCK"
    assert "no real sent email" in t1.notes

    # t2 had real GMAIL_API email with message_id_header -> remains SCHEDULED
    t2 = cleanup_test_db.query(FollowUpTask).filter_by(id=2).first()
    assert t2.status == "SCHEDULED"

    # a1 was built from is_seed=True -> ARCHIVED_SEED
    a1 = cleanup_test_db.query(ApplicationRecord).filter_by(id=1).first()
    assert a1.current_status == "ARCHIVED_SEED"

    # a2 was built from is_seed=False -> remains EMAIL_SENT
    a2 = cleanup_test_db.query(ApplicationRecord).filter_by(id=2).first()
    assert a2.current_status == "EMAIL_SENT"

    assert res["follow_up_tasks"]["after"]["cancelled_mock"] == 1
    assert res["follow_up_tasks"]["after"]["scheduled"] == 1
    assert res["applications"]["after"]["archived_seed"] == 1
