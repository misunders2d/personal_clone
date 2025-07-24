import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from io import BytesIO
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.file'] # Allows access to files created or opened by the app

GOOGLE_DRIVE_CLIENT_ID = os.getenv('GOOGLE_DRIVE_CLIENT_ID')
GOOGLE_DRIVE_CLIENT_SECRET = os.getenv('GOOGLE_DRIVE_CLIENT_SECRET')
TOKEN_PATH = os.getenv('TOKEN_PATH','')

def get_drive_service():
    """Shows basic usage of the Drive v3 API.
    Prints the names and IDs of the first 10 files the user has access to.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                os.remove(TOKEN_PATH)
                creds = None # Force re-authentication
        
        if not creds:
            client_config = {
                "installed": {
                    "client_id": GOOGLE_DRIVE_CLIENT_ID,
                    "project_id": "your-project-id", # Placeholder
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": GOOGLE_DRIVE_CLIENT_SECRET,
                    "redirect_uris": ["http://localhost"]
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            
            with open(TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(folder_name: str, parent_folder_id: str = 'root') -> str:
    """Gets the ID of an existing folder or creates a new one if it doesn't exist.

    Args:
        folder_name: The name of the folder to find or create.
        parent_folder_id: The ID of the parent folder. Defaults to 'root' (My Drive).

    Returns:
        The ID of the found or created folder.
    """
    service = get_drive_service()
    # Search for the folder
    query = f"name = '{folder_name}' and '{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder'"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])

    if items:
        return items[0]['id']
    else:
        # Create the folder if it doesn't exist
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

def upload_file_to_drive(file_name: str, content: str, folder_id: str) -> str:
    """Uploads a file to Google Drive within a specified folder.

    Args:
        file_name: The name of the file to upload.
        content: The content of the file as a string.
        folder_id: The ID of the Google Drive folder where the file will be uploaded.

    Returns:
        The ID of the uploaded file.
    """
    service = get_drive_service()
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaIoBaseUpload(BytesIO(content.encode('utf-8')), mimetype='text/plain', resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def download_file_from_drive(file_id: str) -> str:
    """Downloads a file from Google Drive.

    Args:
        file_id: The ID of the file to download.

    Returns:
        The content of the file as a string.
    """
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return fh.getvalue().decode('utf-8')

def update_file_in_drive(file_id: str, new_content: str) -> str:
    """Updates the content of an existing file in Google Drive.

    Args:
        file_id: The ID of the file to update.
        new_content: The new content for the file.

    Returns:
        The ID of the updated file.
    """
    service = get_drive_service()
    media = MediaIoBaseUpload(BytesIO(new_content.encode('utf-8')), mimetype='text/plain', resumable=True)
    file = service.files().update(fileId=file_id, media_body=media).execute()
    return file.get('id')

def delete_file_from_drive(file_id: str) -> bool:
    """Deletes a file from Google Drive.

    Args:
        file_id: The ID of the file to delete.

    Returns:
        True if the file was successfully deleted.
    """
    service = get_drive_service()
    service.files().delete(fileId=file_id).execute()
    return True

def list_files_in_folder(folder_id: str = 'root') -> list[dict]:
    """Lists files within a specified Google Drive folder.

    Args:
        folder_id: The ID of the Google Drive folder to list files from. Defaults to 'root' (My Drive).

    Returns:
        A list of dictionaries, each representing a file with 'id' and 'name'.
    """
    service = get_drive_service()
    results = service.files().list(
        q=f"'{folder_id}' in parents",
        pageSize=100, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    return items