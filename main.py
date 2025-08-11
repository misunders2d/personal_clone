import streamlit as st
import asyncio
import uuid
import dotenv
import os
import vertexai # Import vertexai

dotenv.load_dotenv()

# Import ADK services and types
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.genai import types
from google.adk.runners import Runner

# Import master_agent after dotenv.load_dotenv() to ensure env vars are loaded
from personal_clone.agent import master_agent

st.set_page_config(layout="wide")

st.title("Personal Clone")

async def main():
    # --- App Constants ---
    APP_NAME = "personal-clone-app"
    USER_ID = "streamlit-user"

    # Initialize Vertex AI with project and location from .env
    # This ensures the correct project is used, overriding gcloud config if necessary.
    vertexai.init(
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION")
    )

    # Debugging: Display GOOGLE_GENAI_USE_VERTEXAI value
    st.write(f"GOOGLE_GENAI_USE_VERTEXAI: {os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")}")
    st.write(f"GOOGLE_CLOUD_PROJECT: {os.environ.get("GOOGLE_CLOUD_PROJECT")}")
    st.write(f"GOOGLE_CLOUD_LOCATION: {os.environ.get("GOOGLE_CLOUD_LOCATION")}")

    # Initialize services and runner, and store them in session_state
    if "runner" not in st.session_state:
        st.session_state.session_service = InMemorySessionService()
        st.session_state.artifact_service = InMemoryArtifactService()
        st.session_state.memory_service = InMemoryMemoryService()

        st.session_state.runner = Runner(
            agent=master_agent, 
            app_name=APP_NAME,
            session_service=st.session_state.session_service,
            artifact_service=st.session_state.artifact_service,
            memory_service=st.session_state.memory_service
        )

    # Initialize chat history and session
    if "messages" not in st.session_state:
        st.session_state.messages = []
        session = await st.session_state.session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
        st.session_state.session_id = session.id

    # Main chat interface
    chat_container = st.container()

    with chat_container:
        # Display chat messages from history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat input with file upload
    chat_input_result = st.chat_input(
        "What is up?", 
        accept_file="multiple", 
        key="chat_input_with_files"
    )

    # React to user input
    if chat_input_result:
        prompt = chat_input_result.text
        uploaded_files = chat_input_result.files

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Handle file uploads
        parts = [types.Part(text=prompt)]
        if uploaded_files:
            file_names = []
            for uploaded_file in uploaded_files:
                file_names.append(uploaded_file.name)
                parts.append(types.Part(text=f"\n\n--- Attached File: {uploaded_file.name} ---\n\n"))
                parts.append(types.Part(inline_data=types.Blob(mime_type=uploaded_file.type, data=uploaded_file.getvalue())))
            
            # Add a message to chat history about uploaded files
            file_upload_message = f"_Files uploaded: {', '.join(file_names)}_ "
            st.session_state.messages.append({"role": "user", "content": file_upload_message})

        new_message = types.Content(role="user", parts=parts)

        # Process the prompt using the ADK Runner
        response_events = st.session_state.runner.run_async(
            user_id=USER_ID, 
            session_id=st.session_state.session_id, 
            new_message=new_message
        )
        
        agent_response = ""
        async for event in response_events:
            if event.is_final_response() and event.content and event.content.parts:
                agent_response = event.content.parts[0].text
                break

        # Display assistant response
        with st.chat_message("assistant"):
            st.markdown(agent_response)
        st.session_state.messages.append({"role": "assistant", "content": agent_response})

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        st.error(f"An error occurred: {e}")
