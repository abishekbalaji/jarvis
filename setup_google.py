"""Run once to sign in to Google (opens your browser). Use setup-google.bat."""
import google_services

google_services.authorize()
input("Press Enter to close this window...")
