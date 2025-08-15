import os
from dotenv import load_dotenv

load_dotenv()

# Set dummy environment variables for testing
os.environ["GOOGLE_CLOUD_PROJECT"] = "dummy-project"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
os.environ["MASTER_AGENT_MODEL"] = "gemini-1.5-flash"
os.environ["MODEL_NAME"] = "gemini-1.5-flash"
os.environ["MAX_LOOP_ITERATIONS"] = "3"
os.environ["GITHUB_TOKEN"] = "dummy-token"


from personal_clone.agent import create_master_agent

try:
    agent = create_master_agent()
    print("Master agent created successfully!")
except Exception as e:
    print(f"An error occurred: {e}")
