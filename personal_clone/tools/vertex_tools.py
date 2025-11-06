from google.cloud import storage
from google.oauth2 import service_account
import json
from .. import config

bucket_name = config.GOOGLE_CLOUD_STORAGE_BUCKET.replace("gs://", "")
documents_folder = "documents/"


def list_blobs():
    """Lists all the blobs/documents in the given GCS bucket."""

    try:
        all_files = []
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(config.GCP_SERVICE_ACCOUNT_INFO)
        )
        storage_client = storage.Client(
            project=config.GOOGLE_CLOUD_PROJECT, credentials=credentials
        )

        bucket = storage_client.bucket(bucket_name)

        blobs = bucket.list_blobs(prefix=documents_folder)

        for blob in blobs:
            all_files.append(blob.name)
        return {
            "status": "success",
            "files": [x for x in all_files if x != documents_folder],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def upload_blob(source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(config.GCP_SERVICE_ACCOUNT_INFO)
        )
        storage_client = storage.Client(
            project=config.GOOGLE_CLOUD_PROJECT, credentials=credentials
        )

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(source_file_name)

        return {
            "status": "success",
            "message": f"File {source_file_name} uploaded to {destination_blob_name}.",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
