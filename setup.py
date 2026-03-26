import os
import secrets
import sys

from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

ENV_FILE_PATH = os.environ.get("DOTENV_PATH", "./data/.env")

CONFIG_FIELDS = [
    {
        "key": "GEMINI_API_KEY",
        "label": "Google Gemini API Key",
        "section": "required",
        "type": "password",
        "placeholder": "AIzaSy...",
        "help": "Powers the agent brain. Get one free at https://aistudio.google.com/app/apikey",
        "required": True,
        "validate": True,
    },
    {
        "key": "TELEGRAM_BOT_TOKEN",
        "label": "Telegram Bot Token",
        "section": "messaging",
        "type": "password",
        "placeholder": "123456:ABC-DEF...",
        "help": "Create a bot via @BotFather on Telegram, copy the token it gives you.",
    },
    {
        "key": "SLACK_BOT_TOKEN",
        "label": "Slack Bot Token",
        "section": "messaging",
        "type": "password",
        "placeholder": "xoxb-...",
        "help": "Create a Slack App, add bot scopes, install to workspace, then copy the Bot User OAuth Token.",
    },
    {
        "key": "SLACK_APP_TOKEN",
        "label": "Slack App Token",
        "section": "messaging",
        "type": "password",
        "placeholder": "xapp-...",
        "help": "Found in App Settings -> Basic Information -> App-Level Tokens.",
    },
    {
        "key": "SLACK_SIGNING_SECRET",
        "label": "Slack Signing Secret",
        "section": "messaging",
        "type": "password",
        "placeholder": "abc123def456...",
        "help": "Found on your Slack App's Basic Information page under App Credentials.",
    },
    {
        "key": "OPENAI_API_KEY",
        "label": "OpenAI API Key",
        "section": "optional_models",
        "type": "password",
        "placeholder": "sk-...",
        "help": "Optional: Use GPT models via LiteLLM.",
    },
    {
        "key": "CLAUDE_API_KEY",
        "label": "Claude API Key",
        "section": "optional_models",
        "type": "password",
        "placeholder": "sk-ant-...",
        "help": "Optional: Use Claude models via LiteLLM.",
    },
]


def validate_gemini_key(key: str) -> bool:
    """Checks if the Gemini API Key is valid."""
    try:
        os.environ["GEMINI_API_KEY"] = key
        from google.genai import Client

        client = Client(api_key=key)
        # Ping model list to verify key
        client.models.get(model="gemini-2.0-flash")
        return True
    except Exception as e:
        print(f"  Invalid Key: {e}")
        return False


def mask(val: str) -> str:
    if not val:
        return "Not set"
    return f"{val[:4]}...{val[-4:]}" if len(val) > 8 else "********"


def run_setup():
    console.clear()
    console.print(
        Panel.fit(
            "[bold blue] PERSONAL CLONE[/bold blue]\n[italic]Setup Wizard[/italic]",
            border_style="blue",
        )
    )

    os.makedirs(os.path.dirname(os.path.abspath(ENV_FILE_PATH)), exist_ok=True)
    load_dotenv(ENV_FILE_PATH)

    for field in CONFIG_FIELDS:
        key = field["key"]
        label = field["label"]
        required = field.get("required", False)
        help_text = field.get("help", "")

        current_val = os.environ.get(key, "")

        while True:
            print(f"\n  {label}")
            if help_text:
                print(f"  ({help_text})")
            if current_val:
                print(f"  Current: {mask(current_val)}")

            prompt = f"  Enter {label}"
            if current_val:
                prompt += " (Enter to keep current)"
            elif not required:
                prompt += " (Enter to skip)"

            user_input = input(f"{prompt}: ").strip()

            if not user_input:
                if required and not current_val:
                    print("  This key is required.")
                    continue
                break

            if field.get("validate"):
                print("  Validating...")
                if validate_gemini_key(user_input):
                    set_key(ENV_FILE_PATH, key, user_input)
                    os.environ[key] = user_input
                    print("  Verified and saved.")
                    break
                else:
                    continue
            else:
                set_key(ENV_FILE_PATH, key, user_input)
                os.environ[key] = user_input
                print("  Saved.")
                break

    # Generate admin passcode if missing
    if not os.environ.get("ADMIN_PASSCODE"):
        passcode = secrets.token_hex(16).upper()
        set_key(ENV_FILE_PATH, "ADMIN_PASSCODE", passcode)

    console.print(f"\n{'═' * 50}")
    console.print("[bold green]  Setup Complete![/bold green]")
    console.print(f"  Config saved to: [cyan]{ENV_FILE_PATH}[/cyan]")

    # Summary
    has_tg = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))
    has_slack = bool(os.environ.get("SLACK_BOT_TOKEN"))
    if has_tg or has_slack:
        platforms = []
        if has_tg:
            platforms.append("Telegram (polling mode — no public URL needed)")
        if has_slack:
            platforms.append("Slack (webhook mode — requires public URL)")
        console.print(f"  Messaging: {', '.join(platforms)}")
    else:
        console.print(
            "  [yellow]No messaging platform configured. You can add one later via /setup.[/yellow]"
        )


if __name__ == "__main__":
    try:
        # Check if rich is available for better UI, else use plain input
        try:
            # If rich is available, we could use a better UI,
            # but for now, the plain input version is more robust inside containers.
            pass
        except ImportError:
            pass

        run_setup()
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(0)
