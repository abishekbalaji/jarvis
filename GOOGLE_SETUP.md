# Email & Calendar setup (one time, ~10 minutes)

This lets Jarvis read/send your Gmail and read your Google Calendar. It's free.
Google just requires you to create your own credentials so only YOU can authorize it.

Do these steps once. Use the **same Google account** throughout.

## 1. Create a Google Cloud project
1. Go to **https://console.cloud.google.com/** and sign in.
2. Top bar → project dropdown → **New Project**. Name it `Jarvis` → **Create**.
3. Make sure the `Jarvis` project is selected (top bar) before continuing.

## 2. Enable the two APIs
1. Left menu → **APIs & Services → Library**.
2. Search **Gmail API** → click it → **Enable**.
3. Go back to Library, search **Google Calendar API** → click it → **Enable**.

## 3. Set up the consent screen
1. **APIs & Services → OAuth consent screen**.
2. User Type: **External** → **Create**.
3. Fill in: App name `Jarvis`, your email for "User support email" and
   "Developer contact". Leave everything else → **Save and Continue**.
4. **Scopes** page → just **Save and Continue** (Jarvis requests what it needs at sign-in).
5. **Test users** page → **Add Users** → type **your own Gmail address** → **Save and Continue**.
   *(This is important — only test users can sign in while the app is in testing mode.)*
6. **Back to Dashboard**.

## 4. Create the credentials file
1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
2. Application type: **Desktop app**. Name: `Jarvis Desktop` → **Create**.
3. A popup appears → **Download JSON**.
4. Rename the downloaded file to exactly **`credentials.json`** and move it into:
   `C:\Users\abish\anthropic\jarvis\`

## 5. Sign in
1. Double-click **`setup-google.bat`** in the jarvis folder.
2. Your browser opens → choose your Google account.
3. You'll see **"Google hasn't verified this app"** — this is normal because it's
   your own personal app. Click **Advanced → Go to Jarvis (unsafe)**.
4. Approve the Gmail + Calendar permissions → **Allow**.
5. The window says "Google sign-in complete." Done! A `token.json` is saved so you
   won't have to do this again.

## Troubleshooting

**"Access blocked: Jarvis has not completed the Google verification process"
(Error 403: access_denied)** — you're not on the test-user list. Fix it:
1. Console → **APIs & Services → OAuth consent screen** (or **Google Auth
   Platform → Audience** in the newer UI).
2. **Test users** section → **+ Add users** → add your own Gmail address → **Save**.
3. Run `setup-google.bat` again.

(The separate "Google hasn't verified this app" warning is normal — click
**Advanced → Go to Jarvis (unsafe)** to proceed.)

## Done — try it
Run `run-jarvis.bat` and say:
- "Hey Jarvis" → *"Do I have any new email?"*
- "Hey Jarvis" → *"What's on my calendar?"*
- "Hey Jarvis" → *"Email john@example.com, subject Hello, body Just testing Jarvis."*

> Privacy: your email/calendar data stays between your PC and Google. Jarvis only
> reads it to answer you. `credentials.json` and `token.json` are personal — don't
> share them.
