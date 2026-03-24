import requests
from FaaSr_py.client.py_client_stubs import faasr_log, faasr_put_file, faasr_secret


def build_url(lat: str, lon: str, api_key: str) -> str:
    """
    Build the URL for the OpenWeather API 5-day forecast endpoint.

    Args:
        lat: The latitude coordinate.
        lon: The longitude coordinate.
        api_key: The OpenWeather API key.

    Returns:
        The URL to fetch 5-day forecast data (3-hour intervals) from.
    """
    base_url = "https://api.openweathermap.org/data/2.5/forecast"
    return f"{base_url}?lat={lat}&lon={lon}&appid={api_key}&units=metric"


def fetch_weather_data(url: str, output_name: str) -> dict:
    """
    Fetch weather data from the OpenWeather API and save it to a local file.

    Args:
        url: The URL to fetch weather data from.
        output_name: The name of the file to save the data to.

    Returns:
        The weather data as a dictionary.
    """
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        weather_data = response.json()

        with open(output_name, "w") as f:
            import json

            json.dump(weather_data, f, indent=2)

        return weather_data

    except Exception as e:
        faasr_log(f"Error fetching weather data from {url}: {e}")
        raise e


def get_weather_data(folder_name: str, output_name: str, lat: str, lon: str, location_name: str):
    """
    Fetch 5-day forecast data (3-hour intervals) from OpenWeather API using a secret API key
    and upload it to an S3 bucket.

    This function demonstrates the use of faasr_secret() to securely retrieve
    API credentials.

    Args:
        folder_name: The name of the folder to upload the data to.
        output_name: The name of the file to upload the data to.
        lat: The latitude coordinate.
        lon: The longitude coordinate.
        location_name: A descriptive name for the location (for logging).
    """

    # 1. Get the API key from the secret store using faasr_secret
    faasr_log("Retrieving OpenWeather API key from secret store")
    api_key = faasr_secret("OPENWEATHER_API_KEY")
    faasr_log("Successfully retrieved API key")

    # 2. Build the URL
    url = build_url(lat, lon, api_key)
    faasr_log(
        f"Fetching 5-day forecast data (3-hour intervals) for {location_name} (lat={lat}, lon={lon})"
    )

    # 3. Fetch the weather data and save to local file
    weather_data = fetch_weather_data(url, output_name)
    city_name = weather_data.get("city", {}).get("name", "Unknown")
    num_timestamps = len(weather_data.get("list", []))
    faasr_log(
        f"Fetched forecast data for {city_name}: {num_timestamps} timestamps (3-hour intervals)"
    )

    # 4. Upload the file to the S3 bucket
    faasr_put_file(
        local_file=output_name,
        remote_folder=folder_name,
        remote_file=output_name,
    )

    faasr_log(f"Uploaded forecast data to {folder_name}/{output_name}")
