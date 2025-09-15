from google import auth as google_auth
from google.auth.transport import requests as google_requests
import requests
import json
import asyncio

endpoint = "https://us-central1-aiplatform.googleapis.com/v1/projects/personal-clone-464511/locations/us-central1/reasoningEngines/303645529173131264"
USER_ID = "sergey@mellanni.com"


def get_identity_token():
    credentials, _ = google_auth.default()
    auth_request = google_requests.Request()
    credentials.refresh(auth_request)
    return credentials.token


if "identity_token" not in globals():
    identity_token = get_identity_token()


def get_resource_data():
    response = requests.get(
        endpoint,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {identity_token}",
        },
    )
    response.raise_for_status()
    if response.status_code == 200:
        return response.json()


def create_session():
    response = requests.post(
        f"{endpoint}:query",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {identity_token}",
        },
        data=json.dumps(
            {
                "class_method": "create_session",
                "input": {"user_id": USER_ID},
            }
        ),
    )
    print(response.json())


def list_sessions(user_id):
    response = requests.post(
        f"{endpoint}:query",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {identity_token}",
        },
        data=json.dumps(
            {
                "class_method": "list_sessions",
                "input": {"user_id": USER_ID},
            }
        ),
    )
    print(response.text)


async def stream_response(user_id=USER_ID, session_id=""):
    requests.post(
        f"{endpoint}:streamQuery?alt=sse",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {identity_token}",
        },
        data=json.dumps(
            {
                "class_method": "async_stream_query",
                "input": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "message": "How are you today?",
                },
            }
        ),
        stream=True,
    )


def get_session(user_id=USER_ID, session_id=""):
    response = requests.post(
        f"{endpoint}:query",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {identity_token}",
        },
        data=json.dumps(
            {
                "class_method": "get_session",
                "input": {"user_id": user_id, "session_id": session_id},
            }
        ),
    )
    print(response.json())


if __name__ == "__main__":
    # create_session()
    # asyncio.run(stream_response(session_id="3682947787898486784"))
    # get_session(session_id="3682947787898486784")
    list_sessions(user_id=USER_ID)
