"""
google_services.py - Jarvis's Gmail + Google Calendar powers.

One-time setup (see README "Email & Calendar setup"):
  1. Create a Google Cloud project, enable the Gmail API + Calendar API.
  2. Make an OAuth "Desktop app" credential, download it as credentials.json,
     and put it in this folder.
  3. Run setup-google.bat once to sign in (opens your browser).

After that, Jarvis can read/send mail and read your calendar. Tokens are cached
in token.json so you only sign in once.
"""

import os
import base64
import datetime
from email.mime.text import MIMEText

import paths

_CREDS_FILE = os.path.join(paths.ROOT, "credentials.json")
_TOKEN_FILE = os.path.join(paths.ROOT, "token.json")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
]

_creds = None


def is_configured() -> bool:
    return os.path.exists(_CREDS_FILE)


def _get_creds():
    """Load cached credentials, refreshing or running the sign-in flow as needed."""
    global _creds
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    if _creds and _creds.valid:
        return _creds

    creds = None
    if os.path.exists(_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(_TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(_CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    _creds = creds
    return creds


def authorize():
    """Run the one-time browser sign-in. Called by setup_google.py."""
    if not is_configured():
        print("\n[!] credentials.json not found in the jarvis folder.")
        print("    Follow the 'Email & Calendar setup' steps in the README first.\n")
        return False
    _get_creds()
    print("\n✅ Google sign-in complete. Jarvis can now use Gmail and Calendar.\n")
    return True


def _service(name, version):
    from googleapiclient.discovery import build
    return build(name, version, credentials=_get_creds(), cache_discovery=False)


# ---------------------------------------------------------------------------
# Gmail
# ---------------------------------------------------------------------------
def check_email(_: str = "") -> str:
    """Summarize the most recent unread emails in the inbox."""
    if not is_configured():
        return "Email isn't set up yet, sir. Please complete the Google setup."
    try:
        svc = _service("gmail", "v1")
        resp = svc.users().messages().list(
            userId="me", labelIds=["INBOX", "UNREAD"], maxResults=5).execute()
        msgs = resp.get("messages", [])
        if not msgs:
            return "You have no unread emails, sir."
        lines = []
        for m in msgs:
            full = svc.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject"]).execute()
            headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}
            sender = headers.get("From", "unknown").split("<")[0].strip().strip('"')
            subject = headers.get("Subject", "(no subject)")
            lines.append(f"From {sender}: {subject}")
        return (f"You have {len(lines)} unread email(s), sir:\n" + "\n".join(lines))
    except Exception as e:
        return f"I couldn't check your email ({type(e).__name__})."


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email from the user's Gmail account."""
    if not is_configured():
        return "Email isn't set up yet, sir. Please complete the Google setup."
    try:
        svc = _service("gmail", "v1")
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"Email sent to {to}, sir."
    except Exception as e:
        return f"I couldn't send the email ({type(e).__name__})."


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------
def get_calendar_events(_: str = "") -> str:
    """List the next few upcoming calendar events."""
    if not is_configured():
        return "Calendar isn't set up yet, sir. Please complete the Google setup."
    try:
        svc = _service("calendar", "v3")
        now = datetime.datetime.utcnow().isoformat() + "Z"
        resp = svc.events().list(
            calendarId="primary", timeMin=now, maxResults=5,
            singleEvents=True, orderBy="startTime").execute()
        events = resp.get("items", [])
        if not events:
            return "You have no upcoming events, sir."
        lines = []
        for ev in events:
            start = ev["start"].get("dateTime", ev["start"].get("date"))
            try:
                dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                when = dt.strftime("%a %b %d at %I:%M %p")
            except ValueError:
                when = start
            lines.append(f"{ev.get('summary', '(no title)')} — {when}")
        return "Your upcoming events, sir:\n" + "\n".join(lines)
    except Exception as e:
        return f"I couldn't check your calendar ({type(e).__name__})."
