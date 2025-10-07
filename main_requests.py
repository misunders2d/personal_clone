from google import auth as google_auth
from google.auth.transport import requests as google_requests
import requests
import json

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
    return response.json()


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
    return response.json()


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


def query_agent(user_id: str, message_text: str) -> str:
    """Send a query to the ADK agent and return the full response."""
    # session_id = ensure_session(user_id)
    session_id = "7151728852648067072"

    url = f"{endpoint}:streamQuery"
    headers = {
        "Authorization": f"Bearer {identity_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    body = {
        "class_method": "async_stream_query",
        "input": {
            "user_id": user_id,
            "session_id": session_id,
            "message": message_text,
        },
    }

    resp = requests.post(url, headers=headers, data=json.dumps(body), stream=True)
    resp.raise_for_status()

    full_response = ""
    for chunk in resp.iter_lines():
        if not chunk:
            continue
        try:
            part_block = json.loads(chunk.decode("utf-8"))
        except Exception:
            continue
        parts = part_block.get("content", {}).get("parts", [])
        for part in parts:
            if part.get("thought"):
                print(f'Thought: {part.get("text")}')
            elif part.get("text"):
                print(f'Agent response: {part.get("text")}')
            else:
                print(f"TECHNICAL: {part}")

    print()  # newline after streaming output
    return full_response


if __name__ == "__main__":
    while True:
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() in {"exit", "quit"}:
            break
        print("Agent:", end=" ", flush=True)
        response = query_agent(USER_ID, user_input)
