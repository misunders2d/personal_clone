import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from io import BytesIO
import json

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_drive_service():
    """Returns a Google Drive service using OAuth2 flow."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Make sure to have GDRIVE_OAUTH environment variable initialized
            flow = InstalledAppFlow.from_client_config(json.loads(os.environ.get('GDRIVE_OAUTH','')), scopes=SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


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

