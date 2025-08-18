import streamlit as st
from login import require_login
import os
import json

# Import ADK services and types
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types
from google.adk.runners import Runner

# Import master_agent after dotenv.load_dotenv() to ensure env vars are loaded
from personal_clone.agent import create_master_agent
import traceback

st.set_page_config(layout="wide")

# environment variables setup
def inject_section(section_name, section_value):
    """Convert a st.secrets section into an env var (JSON if dict/list)."""
    if isinstance(section_value, (dict, list)):
        os.environ[section_name] = json.dumps(section_value)
    else:
        os.environ[section_name] = str(section_value)


def traverse(prefix, data):
    """Recursively traverse st.secrets and inject top-level sections."""
    for key, value in data.items():
        name = key if not prefix else f"{prefix}__{key}"
        if isinstance(value, dict):
            # inject the whole table as JSON under its top-level name
            if not prefix:  
                inject_section(key, value)
            traverse(name, value)
        else:
            if not prefix:
                inject_section(key, value)


def load_secrets_into_env():
    """Load st.secrets into os.environ with JSON blobs for tables."""
    if st is not None and hasattr(st, "secrets"):
        traverse("", dict(st.secrets))

APP_NAME = "misunderstood-personal-clone-app"
USER_ID = (
    st.user.email
    if "email" in st.user and isinstance(st.user.email, str)
    else "undefined"
)

require_login()

user_picture = (
    st.user.picture
    if st.user.picture and isinstance(st.user.picture, str)
    else "media/user_avatar.jpg"
)
new_msg = ""

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(
        message["role"],
        avatar=(user_picture if message["role"] == "user" else "media/haken.jpg"),
    ):  #
        st.markdown(message["content"])


async def run_agent(user_input: str, session_id: str, user_id: str):
    global new_msg

    if "session_service" not in st.session_state:
        st.session_state["session_service"] = InMemorySessionService()
        await st.session_state["session_service"].create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
    else:
        await st.session_state["session_service"].get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
    session_service = st.session_state["session_service"]
    artifact_service = InMemoryArtifactService()

    runner = Runner(
        agent=create_master_agent(),
        app_name=APP_NAME,
        session_service=session_service,
        artifact_service=artifact_service,
    )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=user_input)]),
    ):

        if event.content and event.content.parts and event.content.parts[0].text:
            new_msg += event.content.parts[0].text
            yield event.content.parts[0].text
        elif (
            event.content
            and event.content.parts
            and event.content.parts[0].function_call
        ):
            st.toast(f"Running {event.content.parts[0].function_call.name}")
        elif (
            event.content
            and event.content.parts
            and event.content.parts[0].function_response
            and event.content.parts[0].function_response.response
            and "result" in event.content.parts[0].function_response.response
            and isinstance(
                event.content.parts[0].function_response.response["result"], str
            )
        ):
            new_msg += event.content.parts[0].function_response.response["result"]
            yield event.content.parts[0].function_response.response["result"]
        # handle errors
        elif event.error_code:
            st.error(f"Sorry, the following error happened:\n{event.error_code}")
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[
                        types.Part(text=f"This error happened, please check: {event}")
                    ],
                ),
            ):
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    new_msg += event.content.parts[0].text
                    yield event.content.parts[0].text

        # else:
        #     yield event


if prompt := st.chat_input("Ask me what I can do ;)", accept_file=True):
    prompt_text = prompt.text
    prompt_files = prompt.files
    st.chat_message("user", avatar=user_picture).markdown(prompt.text)
    st.session_state.messages.append({"role": "user", "content": prompt.text})

    with st.chat_message("Jeff", avatar="media/haken.jpg"):
        try:
            st.write_stream(
                run_agent(
                    user_input=prompt_text, session_id="session123", user_id=USER_ID
                )
            )
        except Exception as e:
            st.write(f"Sorry, an error occurred, please try later:\n{e}")
            st.write(traceback.format_exc())
    st.session_state.messages.append({"role": "assistant", "content": new_msg})
