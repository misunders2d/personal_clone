import asyncio
from personal_clone.agent import master_agent
from google.genai.types import Content, Part

async def main():
    """Provides a command-line interface for interacting with the personal_clone agent."""
    print("Personal Clone Developer Agent")
    print("-----------------------------")
    print("Enter 'quit' to exit.")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "quit":
            break

        content = Content(role='user', parts=[Part(text=user_input)])
        events = master_agent.run_async(new_message=content)

        async for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                print(f"Agent: {event.content.parts[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
