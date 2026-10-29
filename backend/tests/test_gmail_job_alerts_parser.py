import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import JobListing
from app.services.gmail_job_alerts_parser import GmailJobAlertParser

@pytest.fixture
def parser_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_parse_linkedin_alert():
    html_body = """
    <div>
        <h3>3 new jobs match your preferences</h3>
        <tr>
            <td>
                <a href="https://www.linkedin.com/jobs/view/operations-lead-at-tatasteel-12345?refId=xyz">
                    Operations Lead
                </a>
                <span>Tata Steel | Hyderabad, India</span>
            </td>
        </tr>
    </div>
    """
    leads = GmailJobAlertParser.parse_job_alert_content(
        message_id="msg-linkedin-101",
        sender="jobalerts-noreply@linkedin.com",
        subject="3 new jobs for Operations Lead",
        body=html_body
    )
    assert len(leads) == 1
    assert leads[0]["title"] == "Operations Lead"
    assert "linkedin.com/jobs/view/operations-lead-at-tatasteel-12345" in leads[0]["url"]
    assert leads[0]["message_id"] == "msg-linkedin-101"

def test_parse_naukri_alert():
    html_body = """
    <div>
        <p>Recommended jobs for you:</p>
        <div>
            <a href="https://www.naukri.com/job-listings-supply-chain-executive-delhivery-hyderabad-998877?src=alert">
                Supply Chain Executive
            </a>
            <div>Delhivery Logistics | Hyderabad</div>
        </div>
    </div>
    """
    leads = GmailJobAlertParser.parse_job_alert_content(
        message_id="msg-naukri-202",
        sender="jobalerts@naukri.com",
        subject="Jobs matching your search for Operations",
        body=html_body
    )
    assert len(leads) == 1
    assert leads[0]["title"] == "Supply Chain Executive"
    assert "naukri.com/job-listings-supply-chain-executive" in leads[0]["url"]
    assert leads[0]["message_id"] == "msg-naukri-202"

def test_parse_indeed_alert():
    html_body = """
    <div>
        <a href="https://in.indeed.com/viewjob?jk=indeedjob123456&from=ja">
            Warehouse Operations Manager
        </a>
        <div>Blue Dart Express | Hyderabad</div>
    </div>
    """
    leads = GmailJobAlertParser.parse_job_alert_content(
        message_id="msg-indeed-303",
        sender="alert@indeed.com",
        subject="Indeed Job Alert: Operations",
        body=html_body
    )
    assert len(leads) == 1
    assert leads[0]["title"] == "Warehouse Operations Manager"
    assert "indeedjob123456" in leads[0]["url"]

def test_parse_apna_alert():
    html_body = """
    <div>
        <a href="https://apna.co/job/hyderabad/operations-executive-887766">
            Operations Executive
        </a>
        <div>Flipkart Supply Chain | Hyderabad</div>
    </div>
    """
    leads = GmailJobAlertParser.parse_job_alert_content(
        message_id="msg-apna-404",
        sender="alerts@apna.co",
        subject="New Jobs on Apna",
        body=html_body
    )
    assert len(leads) == 1
    assert leads[0]["title"] == "Operations Executive"
    assert "apna.co/job/hyderabad/operations-executive-887766" in leads[0]["url"]

def test_ingest_job_alerts_and_url_validation(parser_test_db):
    session = parser_test_db
    mock_messages = [{"id": "msg-alert-555"}]
    mock_full_msg = {
        "id": "msg-alert-555",
        "payload": {
            "headers": [
                {"name": "From", "value": "jobalerts-noreply@linkedin.com"},
                {"name": "Subject", "value": "Job Alert: Operations Executive"}
            ],
            "body": {
                "data": "PGRpdj48YSBocmVmPSJodHRwczovL3d3dy5saW5rZWRpbi5jb20vam9icy92aWV3L29wZXJhdGlvbnMtZXhlYy01NTUiPk9wZXJhdGlvbnMgRXhlY3V0aXZlPC9hPjxzcGFuPlZlbmRvciBMb2dpc3RpY3MgfCBHeWRlcmFiYWQ8L3NwYW4+PC9kaXY+"
            }
        }
    }

    with patch("app.services.gmail_service.GmailService.list_messages_by_query", return_value=mock_messages):
        with patch("app.services.gmail_service.GmailService.get_message", return_value=mock_full_msg):
            # Mock URL validation returning HTTP 200
            with patch("app.services.gmail_job_alerts_parser.check_live_job_url", return_value=(True, "HTTP 200 OK")):
                imported = GmailJobAlertParser.ingest_job_alerts_from_gmail(session, label="job-alerts")

    assert len(imported) == 1
    item = imported[0]
    assert item["source_platform"] == "gmail_alert"
    assert item["is_seed"] is False
    assert item["vacancy_status"] == "VERIFIED_OPEN"
    assert item["message_id"] == "msg-alert-555"

    job_in_db = session.query(JobListing).filter_by(original_url="https://www.linkedin.com/jobs/view/operations-exec-555").first()
    assert job_in_db is not None
    assert job_in_db.source_platform == "gmail_alert"
    assert job_in_db.is_seed is False
    assert job_in_db.last_verified_at is not None
