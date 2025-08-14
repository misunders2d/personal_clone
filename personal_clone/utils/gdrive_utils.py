import os
import pickle
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from io import BytesIO


# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    "https://www.googleapis.com/auth/drive"
]  # Allows access to files created or opened by the app


TOKEN_PATH = os.path.join(os.path.dirname(__file__), '../.streamlit/token.pickle')

def get_drive_service():
    """Returns a Google Drive service using OAuth2 flow."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                os.remove(TOKEN_PATH)
                # Rerun to trigger the flow again
                st.rerun()
        else:
            # Create a dictionary for the client secrets from st.secrets
            client_secrets = {
                "installed": {
                    "client_id": st.secrets["google_oauth"]["client_id"],
                    "client_secret": st.secrets["google_oauth"]["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost:8501"]
                }
            }
            flow = InstalledAppFlow.from_client_config(client_secrets, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)


def get_or_create_folder(folder_name: str, parent_folder_id: str = "root") -> str:
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
    items = results.get("files", [])

    if items:
        return items[0]["id"]
    else:
        # Create the folder if it doesn't exist
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id],
        }
        folder = service.files().create(body=file_metadata, fields="id").execute()
        return folder.get("id")


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
    file_metadata = {"name": file_name, "parents": [folder_id]}
    media = MediaIoBaseUpload(
        BytesIO(content.encode("utf-8")), mimetype="text/plain", resumable=True
    )
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    return file.get("id")


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
    return fh.getvalue().decode("utf-8")


def update_file_in_drive(file_id: str, new_content: str) -> str:
    """Updates the content of an existing file in Google Drive.

    Args:
        file_id: The ID of the file to update.
        new_content: The new content for the file.

    Returns:
        The ID of the updated file.
    """
    service = get_drive_service()
    media = MediaIoBaseUpload(
        BytesIO(new_content.encode("utf-8")), mimetype="text/plain", resumable=True
    )
    file = service.files().update(fileId=file_id, media_body=media).execute()
    return file.get("id")


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


def list_files_in_folder(folder_id: str = "root") -> list[dict]:
    """Lists files within a specified Google Drive folder.

    Args:
        folder_id: The ID of the Google Drive folder to list files from. Defaults to 'root' (My Drive).

    Returns:
        A list of dictionaries, each representing a file with 'id' and 'name'.
    """
    service = get_drive_service()
    results = (
        service.files()
        .list(
            q=f"'{folder_id}' in parents",
            pageSize=100,
            fields="nextPageToken, files(id, name)",
        )
        .execute()
    )
    items = results.get("files", [])
    return items
