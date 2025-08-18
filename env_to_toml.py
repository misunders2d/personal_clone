# small useful utility to convert .env variables to TOML format for deploying on Streamlit

import toml
import os

def convert_env_to_toml(env_file_path, toml_file_path):
    """
    Converts a .env file to a .toml file.

    Args:
        env_file_path (str): The path to the input .env file.
        toml_file_path (str): The path to the output .toml file.
    """
    # Ensure the .env file exists
    if not os.path.exists(env_file_path):
        print(f"Error: .env file not found at '{env_file_path}'")
        return

    # Read .env file and parse key-value pairs
    data = {}
    with open(env_file_path, 'r') as env_file:
        for line in env_file:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                try:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    data[key] = value
                except ValueError:
                    print(f"Skipping malformed line: '{line}'")

    # Write the parsed data to a .toml file
    with open(toml_file_path, 'w') as toml_file:
        toml.dump(data, toml_file)

    print(f"Successfully converted '{env_file_path}' to '{toml_file_path}'")

if __name__ == '__main__':
    # Define file paths
    input_env_file = '.env'
    output_toml_file = '.toml'

    # Convert the file
    convert_env_to_toml(input_env_file, output_toml_file)