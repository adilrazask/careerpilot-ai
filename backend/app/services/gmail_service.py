"""
Gmail API Service (OAuth2)
Replaces SMTP with Gmail REST API v1.
Saves message_id and thread_id from API responses.
Creates real Gmail drafts for pending approvals.
Raises GmailAPIError if credentials missing; NEVER falls back to mock silently.
"""
from __future__ import annotations
import os
import json
import base64
import urllib.parse
from typing import Dict, Any, List, Optional, Union
import requests
from email.message import EmailMessage

GMAIL_API_BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"

class GmailAPIError(Exception):
    """Raised when Gmail API returns an error or credentials are missing."""
    pass

class GmailService:
    """
    Gmail API service for creating drafts and sending messages via OAuth.
    If credentials are missing, raises GmailAPIError; never falls back silently.
    """

    @classmethod
    def get_access_token(cls) -> str:
        """
        Retrieves OAuth2 access token.
        Looks in environment variables (GMAIL_API_TOKEN, GMAIL_OAUTH_TOKEN)
        or credentials file.
        Raises GmailAPIError if missing.
        """
        token = os.environ.get("GMAIL_API_TOKEN") or os.environ.get("GMAIL_OAUTH_TOKEN")
        if token and token.strip():
            return token.strip()

        token_path = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
        if os.path.exists(token_path):
            try:
                with open(token_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "access_token" in data and data["access_token"].strip():
                        return data["access_token"].strip()
                    if "token" in data and data["token"].strip():
                        return data["token"].strip()
            except Exception as e:
                raise GmailAPIError(f"Failed to read token.json: {e}")

        raise GmailAPIError(
            "Gmail API credentials missing. Configure GMAIL_API_TOKEN or token.json. "
            "Mock fallback is strictly prohibited."
        )

    @classmethod
    def generate_oauth_authorization_url(
        cls,
        client_id: str,
        redirect_uri: str,
        state: str = "careerpilot_oauth_state",
        scope: str = "https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.readonly"
    ) -> str:
        """Constructs Google OAuth 2.0 authorization URL."""
        base = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }
        return f"{base}?{urllib.parse.urlencode(params)}"

    @classmethod
    def exchange_oauth_code_for_token(
        cls,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Exchanges authorization code for access and refresh tokens."""
        url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        res = requests.post(url, data=payload, timeout=20)
        if res.status_code != 200:
            raise GmailAPIError(f"OAuth token exchange failed ({res.status_code}): {res.text}")
        return res.json()

    @classmethod
    def refresh_oauth_token(
        cls,
        refresh_token: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        """Refreshes expired access token using refresh_token."""
        url = "https://oauth2.googleapis.com/token"
        payload = {
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token"
        }
        res = requests.post(url, data=payload, timeout=20)
        if res.status_code != 200:
            raise GmailAPIError(f"OAuth token refresh failed ({res.status_code}): {res.text}")
        return res.json()

    @classmethod
    def save_token_to_environment(cls, token_data: Union[str, Dict[str, Any]]) -> str:
        """
        Saves token securely in environment variables (never in git).
        Sets GMAIL_API_TOKEN in os.environ and updates runtime settings.
        """
        if isinstance(token_data, dict):
            access_token = token_data.get("access_token") or token_data.get("token") or ""
        else:
            access_token = str(token_data).strip()

        if not access_token:
            raise GmailAPIError("Cannot save empty OAuth token to environment.")

        os.environ["GMAIL_API_TOKEN"] = access_token
        from app.config import settings
        settings.GMAIL_API_TOKEN = access_token
        return access_token

    @classmethod
    def build_raw_email(
        cls,
        sender: str,
        recipient: str,
        subject: str,
        body_text: str,
        pdf_attachment_path: Optional[str] = None,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None
    ) -> str:
        """Builds an RFC 2822 email and returns URL-safe base64 encoded string."""
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to
        msg.set_content(body_text)

        if pdf_attachment_path and os.path.exists(pdf_attachment_path):
            with open(pdf_attachment_path, "rb") as f:
                pdf_data = f.read()
            msg.add_attachment(
                pdf_data,
                maintype="application",
                subtype="pdf",
                filename="SK_Adil_Raja_Resume.pdf"
            )

        raw_bytes = msg.as_bytes()
        return base64.urlsafe_b64encode(raw_bytes).decode("ascii")

    @classmethod
    def create_draft(
        cls,
        sender: str,
        recipient: str,
        subject: str,
        body_text: str,
        pdf_attachment_path: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a real Gmail draft for pending approval."""
        token = cls.get_access_token()
        raw_msg = cls.build_raw_email(sender, recipient, subject, body_text, pdf_attachment_path, thread_id)

        payload: Dict[str, Any] = {"message": {"raw": raw_msg}}
        if thread_id:
            payload["message"]["threadId"] = thread_id

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        res = requests.post(f"{GMAIL_API_BASE_URL}/drafts", headers=headers, json=payload, timeout=20)
        if res.status_code not in (200, 201):
            raise GmailAPIError(f"Gmail API drafts.create failed ({res.status_code}): {res.text}")

        data = res.json()
        draft_id = data.get("id")
        msg = data.get("message", {})
        return {
            "draft_id": draft_id,
            "message_id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "status": "DRAFT_CREATED",
            "provider": "GMAIL_API"
        }

    @classmethod
    def send_message(
        cls,
        sender: str,
        recipient: str,
        subject: str,
        body_text: str,
        pdf_attachment_path: Optional[str] = None,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatches an email via Gmail API and returns message_id and thread_id."""
        token = cls.get_access_token()
        raw_msg = cls.build_raw_email(sender, recipient, subject, body_text, pdf_attachment_path, thread_id, in_reply_to)

        payload: Dict[str, Any] = {"raw": raw_msg}
        if thread_id:
            payload["threadId"] = thread_id

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        res = requests.post(f"{GMAIL_API_BASE_URL}/messages/send", headers=headers, json=payload, timeout=20)
        if res.status_code not in (200, 201):
            raise GmailAPIError(f"Gmail API messages.send failed ({res.status_code}): {res.text}")

        data = res.json()
        return {
            "message_id": data.get("id"),
            "thread_id": data.get("threadId"),
            "provider": "GMAIL_API",
            "status": "SENT"
        }

    @classmethod
    def check_thread_messages(cls, thread_id: str) -> List[Dict[str, Any]]:
        """Fetches all messages in a thread to check for responses, bounces, or auto-replies."""
        if not thread_id:
            return []
        token = cls.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{GMAIL_API_BASE_URL}/threads/{thread_id}", headers=headers, timeout=20)
        if res.status_code != 200:
            raise GmailAPIError(f"Gmail API threads.get failed ({res.status_code}): {res.text}")

        data = res.json()
        return data.get("messages", [])

    @classmethod
    def get_drafts_count(cls) -> int:
        """Fetches total number of drafts currently present in the user's Gmail mailbox."""
        token = cls.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{GMAIL_API_BASE_URL}/drafts", headers=headers, timeout=20)
        if res.status_code != 200:
            raise GmailAPIError(f"Gmail API drafts.list failed ({res.status_code}): {res.text}")
        data = res.json()
        drafts = data.get("drafts", [])
        return len(drafts)

    @classmethod
    def list_messages_by_query(cls, query: str = "label:job-alerts", max_results: int = 50) -> List[Dict[str, Any]]:
        """Lists message summaries matching a search query or label."""
        token = cls.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": query, "maxResults": max_results}
        res = requests.get(f"{GMAIL_API_BASE_URL}/messages", headers=headers, params=params, timeout=20)
        if res.status_code != 200:
            raise GmailAPIError(f"Gmail API messages.list failed ({res.status_code}): {res.text}")
        data = res.json()
        return data.get("messages", [])

    @classmethod
    def get_message(cls, message_id: str) -> Dict[str, Any]:
        """Retrieves full message details by ID."""
        token = cls.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{GMAIL_API_BASE_URL}/messages/{message_id}?format=full", headers=headers, timeout=20)
        if res.status_code != 200:
            raise GmailAPIError(f"Gmail API messages.get failed ({res.status_code}): {res.text}")
        return res.json()
