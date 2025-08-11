import os
import requests
from typing import Optional, Dict, Any

class WeatherAPIError(Exception):
    """Custom exception for weather API errors."""
    pass

def _parse_weather_data(data: Dict[str, Any], units: str) -> Dict[str, Any]:
    """
    Parses the raw JSON response from the OpenWeatherMap API and extracts relevant weather details.
    """
    if not data or "main" not in data or "weather" not in data or "wind" not in data:
        raise WeatherAPIError("Invalid or incomplete weather data received.")

    main_data = data["main"]
    weather_data = data["weather"][0]
    wind_data = data["wind"]
    city_name = data.get("name", "N/A")
    country = data.get("sys", {}).get("country", "N/A")

    temperature_unit = ""
    if units == "metric":
        temperature_unit = "°C"
    elif units == "imperial":
        temperature_unit = "°F"
    elif units == "standard":
        temperature_unit = "K"

    return {
        "city": city_name,
        "country": country,
        "temperature": f"{main_data.get('temp')}{temperature_unit}",
        "feels_like": f"{main_data.get('feels_like')}{temperature_unit}",
        "min_temperature": f"{main_data.get('temp_min')}{temperature_unit}",
        "max_temperature": f"{main_data.get('temp_max')}{temperature_unit}",
        "description": weather_data.get("description", "N/A").capitalize(),
        "humidity": f"{main_data.get('humidity')}%",
        "pressure": f"{main_data.get('pressure')} hPa",
        "wind_speed": f"{wind_data.get('speed')} m/s", # OpenWeatherMap uses m/s by default for metric/standard
        "visibility": f"{data.get('visibility')} meters" if data.get('visibility') else "N/A",
        "cloudiness": f"{data.get('clouds', {}).get('all')}%" if data.get('clouds', {}).get('all') is not None else "N/A",
        "sunrise": data.get('sys', {}).get('sunrise'),
        "sunset": data.get('sys', {}).get('sunset'),
    }

def get_weather(
    city: str,
    api_key: Optional[str] = None,
    units: str = "metric",  # "metric", "imperial", "standard"
    lang: str = "en"
) -> Optional[Dict[str, Any]]:
    """
    Fetches current weather data for a specified city using the OpenWeatherMap API.

    Args:
        city (str): The name of the city to get weather for.
        api_key (Optional[str]): Your OpenWeatherMap API key. If None, it attempts
                                   to retrieve from OPENWEATHERMAP_API_KEY environment variable.
        units (str): Units of measurement. Can be "metric", "imperial", or "standard" (Kelvin).
        lang (str): Language of the output.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing structured weather data, or None if an error occurs.

    Raises:
        WeatherAPIError: If there are issues with API key, network, API response, or data parsing.
    """
    api_key_to_use = api_key or os.environ.get("OPENWEATHERMAP_API_KEY")

    if not api_key_to_use:
        raise WeatherAPIError(
            "OpenWeatherMap API key not found. Please provide it as an argument "
            "or set the OPENWEATHERMAP_API_KEY environment variable."
        )

    BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key_to_use,
        "units": units,
        "lang": lang,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return _parse_weather_data(data, units)

    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise WeatherAPIError(f"Invalid API key. Please check your OpenWeatherMap API key. (Status: {response.status_code})") from e
        elif response.status_code == 404:
            raise WeatherAPIError(f"City not found: {city}. (Status: {response.status_code})") from e
        elif response.status_code == 429:
            raise WeatherAPIError(f"Rate limit exceeded. Too many requests to OpenWeatherMap API. (Status: {response.status_code})") from e
        else:
            raise WeatherAPIError(f"HTTP error occurred: {e}. (Status: {response.status_code}, Response: {response.text})") from e
    except requests.exceptions.ConnectionError as e:
        raise WeatherAPIError(f"Network connection error: Could not connect to OpenWeatherMap API. {e}") from e
    except requests.exceptions.Timeout as e:
        raise WeatherAPIError(f"Timeout error: OpenWeatherMap API did not respond in time. {e}") from e
    except requests.exceptions.RequestException as e:
        raise WeatherAPIError(f"An unexpected request error occurred: {e}") from e
    except ValueError as e:
        raise WeatherAPIError(f"Error parsing JSON response from OpenWeatherMap API: {e}. Response content: {response.text}") from e
    except Exception as e:
        raise WeatherAPIError(f"An unexpected error occurred during weather data retrieval: {e}") from e

if __name__ == "__main__":
    # To run this example, set your API key as an environment variable:
    # export OPENWEATHERMAP_API_KEY="YOUR_API_KEY"
    # or pass it directly to the function call.

    print("--- Testing get_weather function ---")

    # Example 1: Valid city, API key from environment (recommended for testing)
    print("\n--- Test 1: Valid city (metric) ---")
    try:
        weather_data = get_weather(city="London")
        if weather_data:
            print("Weather in London (Metric):")
            for key, value in weather_data.items():
                print(f"  {key}: {value}")
        else:
            print("Could not retrieve weather for London.")
    except WeatherAPIError as e:
        print(f"Error: {e}")

    # Example 2: Valid city with imperial units
    print("\n--- Test 2: Valid city (imperial) ---")
    try:
        weather_data = get_weather(city="New York", units="imperial")
        if weather_data:
            print("Weather in New York (Imperial):")
            for key, value in weather_data.items():
                print(f"  {key}: {value}")
        else:
            print("Could not retrieve weather for New York.")
    except WeatherAPIError as e:
        print(f"Error: {e}")

    # Example 3: Invalid city
    print("\n--- Test 3: Invalid city ---")
    try:
        weather_data = get_weather(city="NonExistentCity123")
        if weather_data:
            print("Weather in NonExistentCity123:", weather_data)
        else:
            print("Could not retrieve weather for NonExistentCity123 (expected error).")
    except WeatherAPIError as e:
        print(f"Caught expected error for invalid city: {e}")

    # Example 4: No API key (expected to fail if not set in environment)
    print("\n--- Test 4: No API Key (expected error) ---")
    original_api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if "OPENWEATHERMAP_API_KEY" in os.environ:
        del os.environ["OPENWEATHERMAP_API_KEY"] # Temporarily unset for test
    try:
        get_weather(city="Tokyo", api_key=None)
    except WeatherAPIError as e:
        print(f"Caught expected error for missing API key: {e}")
    finally:
        if original_api_key:
            os.environ["OPENWEATHERMAP_API_KEY"] = original_api_key # Restore API key

    # Example 5: Providing API key directly
    print("\n--- Test 5: Providing API Key directly (replace with your key for testing) ---")
    # Replace "YOUR_API_KEY_HERE" with an actual OpenWeatherMap API key for this test to pass
    # For CI/CD, consider setting this as a secret variable
    test_api_key = os.environ.get("OPENWEATHERMAP_API_KEY") # Use env var if set, otherwise placeholder
    if not test_api_key:
        print("Skipping Test 5: OPENWEATHERMAP_API_KEY environment variable not set. Please set it or provide a dummy key for this test.")
    else:
        try:
            weather_data = get_weather(city="Berlin", api_key=test_api_key)
            if weather_data:
                print("Weather in Berlin (Metric, API key direct):")
                for key, value in weather_data.items():
                    print(f"  {key}: {value}")
            else:
                print("Could not retrieve weather for Berlin.")
        except WeatherAPIError as e:
            print(f"Error: {e}")
