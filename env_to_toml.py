# small useful utility to convert .env variables to TOML format for deploying on Streamlit

import os
import json
from dotenv import dotenv_values
import toml


def parse_value(value: str):
    """
    Try to parse .env value into a TOML-compatible type.
    Supports: int, float, bool, JSON objects/arrays, lists, or fallback to string.
    """
    value = value.strip()

    # Try boolean
    if value.lower() in ["true", "false"]:
        return value.lower() == "true"

    # Try int
    try:
        return int(value)
    except ValueError:
        pass

    # Try float
    try:
        return float(value)
    except ValueError:
        pass

    # Try JSON (object or array)
    try:
        parsed = json.loads(value)
        return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # Try list (comma-separated)
    if "," in value:
        return [v.strip() for v in value.split(",")]

    # Fallback: string
    return value


def env_to_toml(env_file: str, toml_file: str):
    env_vars = dotenv_values(env_file)
    parsed_vars = {
        key: parse_value(value) for key, value in env_vars.items() if value is not None
    }

    with open(toml_file, "w") as f:
        toml.dump(parsed_vars, f)

    print(f"Converted {env_file} → {toml_file}")


if __name__ == "__main__":
    env_to_toml(".env", "config.toml")
