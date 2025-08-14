import os
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from io import BytesIO
from google.oauth2 import service_account
import json
import tempfile


# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    "https://www.googleapis.com/auth/drive"
]  # Allows access to files created or opened by the app

if "gcp_service_account" in st.secrets:
    gcp_service_account_info = st.secrets["gcp_service_account"]
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".json"
    ) as temp_key_file:
        json.dump(dict(gcp_service_account_info), temp_key_file)
        temp_key_file_path = temp_key_file.name
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_key_file_path


def get_drive_service():
    """Returns a Google Drive service using service account credentials from st.secrets."""
    service_account_info = dict(st.secrets["gcp_service_account"])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


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

def transfer_ownership(file_id: str, new_owner_email: str) -> bool:
    """Transfers ownership of a Google Drive file to a new user.

    The service account (current owner) will automatically be downgraded to a writer.

    Args:
        file_id: The ID of the file to transfer ownership.
        new_owner_email: The email address of the new owner.

    Returns:
        True if ownership transfer was successful, False otherwise.
    """
    service = get_drive_service()
    try:
        # Create a new permission for the new owner with 'owner' role
        new_permission = {
            'type': 'user',
            'role': 'owner',
            'emailAddress': new_owner_email
        }
        # Use transferOwnership=True to explicitly trigger the ownership transfer.
        # sendNotificationEmail=True (default behavior) ensures the new owner is notified.
        service.permissions().create(
            fileId=file_id,
            body=new_permission,
            transferOwnership=True,
            fields='id' # Request only the ID field in the response
        ).execute()

        print(f"Ownership of file {file_id} successfully transferred to {new_owner_email}")
        return True
    except Exception as e:
        print(f"Error transferring ownership for file {file_id} to {new_owner_email}: {e}")
        return False

def create_and_transfer_file_ownership(file_name: str, content: str, folder_id: str, new_owner_email: str) -> str | None:
    """Uploads a file to Google Drive using the service account and then transfers its ownership.

    Args:
        file_name: The name of the file to upload.
        content: The content of the file as a string.
        folder_id: The ID of the Google Drive folder where the file will be uploaded.
        new_owner_email: The email address of the new owner.

    Returns:
        The ID of the uploaded file if both upload and ownership transfer were successful,
        None otherwise.
    """
    file_id = upload_file_to_drive(file_name, content, folder_id)
    if file_id:
        if transfer_ownership(file_id, new_owner_email):
            return file_id
        else:
            # Log or handle the scenario where the file was uploaded but ownership transfer failed.
            print(f"Warning: File {file_id} was uploaded, but ownership transfer to {new_owner_email} failed.")
            return None
    return None
