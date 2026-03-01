# Birthday to Google Calendar Sync Form

A beautiful, glassmorphism-themed birthday sync tool. This simple web app allows users to input a name, birth date, and a celebratory picture, syncing the date up directly with Google Calendar as an annually recurring event!

## Setup Instructions

1. **Install python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Google Calendar API Integration:**
   To securely sink events to the calendar, the application uses the official Google Cloud capabilities.
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project and enable the **Google Calendar API** in the library.
   - Navigate to **APIs & Services** > **Credentials**.
   - Create **OAuth client ID** credentials (choose "Desktop app" as application type).
   - Once generated, download the JSON file and rename it exactly to `credentials.json`.
   - Place `credentials.json` directly into this directory (`e:/code/ARD/birthday-form/credentials.json`).

3. **Run the Application:**
   Run the python backend to serve the application.

   ```bash
   python app.py
   ```

   _Note: If `credentials.json` is missing, the application will operate in "simulation mode", meaning everything works locally and images upload successfully, but it won't actually hit the Google Calendar endpoints._

4. **Uploads Folder:**
   All uploaded images will be saved securely inside the local `/uploads/` directory with their filenames intact.

Enjoy!
