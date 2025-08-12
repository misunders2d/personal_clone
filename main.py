import streamlit as st
from login import login_st
from dotenv import load_dotenv
load_dotenv()

# Import ADK services and types
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types
from google.adk.runners import Runner

# Import master_agent after dotenv.load_dotenv() to ensure env vars are loaded
from personal_clone.agent import master_agent

st.set_page_config(layout="wide")

st.title("Personal Clone")
APP_NAME = "misunderstood-personal-clone-app"
USER_ID = "misunderstood"


if login_st():
    
    user_picture = st.user.picture if st.user.picture and isinstance(st.user.picture, str) else 'media/user_avatar.jpg'
    new_msg = ''
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=user_picture if message["role"]=="user" else 'media/jeff_avatar.jpeg'): #
            st.markdown(message["content"])

    async def run_agent(user_input:str, session_id:str, user_id:str):
        global new_msg
        
        if 'session_service' not in st.session_state:
            st.session_state['session_service'] = InMemorySessionService()
            await st.session_state['session_service'].create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id
            )
        else:
            await st.session_state['session_service'].get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id)
        session_service = st.session_state['session_service']
        artifact_service = InMemoryArtifactService()

        runner = Runner(
            agent=master_agent,
            app_name=APP_NAME,
            session_service=session_service,
            artifact_service=artifact_service
        )

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(role='user', parts=[types.Part(text=user_input)])):

            if event.content and event.content.parts and event.content.parts[0].text:
                new_msg += event.content.parts[0].text
                yield event.content.parts[0].text
            elif event.content and event.content.parts and event.content.parts[0].function_call:
                # yield f'Running {event.content.parts[0].function_call.name} function\n'
                st.toast(f'Running {event.content.parts[0].function_call.name} function\n')
            elif (
                event.content and event.content.parts
                and event.content.parts[0].function_response
                and event.content.parts[0].function_response.response
                and 'result' in event.content.parts[0].function_response.response
                and isinstance(event.content.parts[0].function_response.response['result'], str)
                ):
                new_msg += event.content.parts[0].function_response.response['result']
                yield event.content.parts[0].function_response.response['result']
            #handle errors
            elif event.error_code:
                st.error(f"Sorry, the following error happened:\n{event.error_code}")
                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=types.Content(role='user', parts=[types.Part(text=f'This error happened, please check: {event}')])):
                    if event.content and event.content.parts and event.content.parts[0].text:
                        new_msg += event.content.parts[0].text
                        yield event.content.parts[0].text
                
            # else:
            #     yield event



    if prompt := st.chat_input("Ask me what I can do ;)", accept_file=True):
        prompt_text = prompt.text
        prompt_files = prompt.files
        st.chat_message("user", avatar=user_picture).markdown(prompt.text)
        st.session_state.messages.append({"role": "user", "content": prompt.text})

        with st.chat_message("Jeff", avatar='media/jeff_avatar.jpeg'):
            try:
                st.write_stream(run_agent(user_input=prompt_text, session_id='session123', user_id=USER_ID))
            except Exception as e:
                st.write(f'Sorry, an error occurred, please try later:\n{e}')
        st.session_state.messages.append({"role": "assistant", "content": new_msg})

