import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Google Drive API scope: allow read/write to your files
SCOPES = ['https://www.googleapis.com/auth/drive.file']


def get_drive_service():
    """Authenticate and return Google Drive service"""
    import logging
    base_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(base_dir, 'token.pickle')
    creds_path = os.path.join(base_dir, 'credentials.json')
    creds = None
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            logging.warning(f"Could not load token.pickle: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.error(f"Failed to refresh credentials: {e}")
                creds = None
        if not creds or not creds.valid:
            if not os.path.exists(creds_path):
                raise FileNotFoundError("credentials.json not found in project directory.")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            try:
                creds = flow.run_local_server(port=0, open_browser=False)
            except Exception as e:
                logging.error(f"Google auth failed: {e}")
                raise
            try:
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                logging.warning(f"Could not save token.pickle: {e}")

    return build('drive', 'v3', credentials=creds)


def upload_or_update(filename, filepath, folder_id=None):
    """Upload new file or update existing one in Google Drive"""
    import logging
    if not os.path.exists(filepath):
        logging.warning(f"File not found for upload: {filepath}")
        return
    try:
        service = get_drive_service()
        # Check if file already exists
        query = f"name='{filename}'"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        file_metadata = {'name': filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        media = MediaFileUpload(filepath, resumable=True)
        if files:
            # Update existing file
            file_id = files[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
            print(f"🔄 Updated {filename} in Google Drive")
        else:
            # Upload new file
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"✅ Uploaded {filename} to Google Drive (ID: {file.get('id')})")
    except Exception as e:
        logging.error(f"Failed to upload/update {filename}: {e}")
