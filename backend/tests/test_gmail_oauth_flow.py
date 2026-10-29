import os
import pytest
from unittest.mock import patch, MagicMock
from app.services.gmail_service import GmailService, GmailAPIError

def test_generate_oauth_authorization_url():
    url = GmailService.generate_oauth_authorization_url(
        client_id="my-google-client-id.apps.googleusercontent.com",
        redirect_uri="http://localhost:8000/api/auth/gmail/callback",
        state="secure_random_state_xyz"
    )
    assert "https://accounts.google.com/o/oauth2/v2/auth" in url
    assert "client_id=my-google-client-id.apps.googleusercontent.com" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauth%2Fgmail%2Fcallback" in url
    assert "scope=" in url
    assert "state=secure_random_state_xyz" in url
    assert "prompt=consent" in url

def test_exchange_code_for_token():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "ya29.a0AfH6SMD_mock_token_12345",
        "refresh_token": "1//04mock_refresh_token_67890",
        "expires_in": 3600,
        "token_type": "Bearer"
    }

    with patch("requests.post", return_value=mock_response):
        tokens = GmailService.exchange_oauth_code_for_token(
            code="4/0AWmock_auth_code_xyz",
            client_id="my-client-id",
            client_secret="my-client-secret",
            redirect_uri="http://localhost:8000/api/auth/gmail/callback"
        )

    assert tokens["access_token"] == "ya29.a0AfH6SMD_mock_token_12345"
    assert tokens["refresh_token"] == "1//04mock_refresh_token_67890"

def test_save_token_to_environment():
    token_str = "ya29.mock_secure_token_live"
    saved = GmailService.save_token_to_environment(token_str)
    assert saved == token_str
    assert os.environ.get("GMAIL_API_TOKEN") == token_str

    # Test dictionary input
    token_dict = {"access_token": "ya29.mock_dict_token"}
    saved2 = GmailService.save_token_to_environment(token_dict)
    assert saved2 == "ya29.mock_dict_token"
    assert os.environ.get("GMAIL_API_TOKEN") == "ya29.mock_dict_token"

def test_create_real_draft_returns_draft_and_message_id():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "draft_id_998877",
        "message": {
            "id": "msg_id_112233",
            "threadId": "thread_id_445566"
        }
    }

    with patch.dict(os.environ, {"GMAIL_API_TOKEN": "valid_token_test"}):
        with patch("requests.post", return_value=mock_response):
            draft = GmailService.create_draft(
                sender="adilrazask@gmail.com",
                recipient="hr@apexlogistics.com",
                subject="Application for Operations Executive",
                body_text="Dear Hiring Team,\n\nPlease find attached my resume."
            )

    assert draft["draft_id"] == "draft_id_998877"
    assert draft["message_id"] == "msg_id_112233"
    assert draft["thread_id"] == "thread_id_445566"
    assert draft["status"] == "DRAFT_CREATED"
    assert draft["provider"] == "GMAIL_API"
