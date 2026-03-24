import json

import requests
from FaaSr_py.client.py_client_stubs import faasr_log, faasr_put_file, faasr_secret


def build_url(lat: str, lon: str, api_key: str) -> str:
    base_url = "https://api.openweathermap.org/data/2.5/forecast"
    return f"{base_url}?lat={lat}&lon={lon}&appid={api_key}&units=metric"


def get_weather_data(folder_name: str, output_name: str, lat: str, lon: str, location_name: str) -> None:
    faasr_log("Retrieving OpenWeather API key from secret store")
    api_key = faasr_secret("OPENWEATHER_API_KEY")
    faasr_log("Successfully retrieved API key")

    url = build_url(lat, lon, api_key)
    faasr_log(
        f"Fetching 5-day forecast data (3-hour intervals) for {location_name} (lat={lat}, lon={lon})"
    )

    response = requests.get(url, timeout=20)
    response.raise_for_status()
    weather_data = response.json()

    with open(output_name, "w") as f:
        json.dump(weather_data, f, indent=2)

    city_name = weather_data.get("city", {}).get("name", "Unknown")
    num_timestamps = len(weather_data.get("list", []))
    faasr_log(
        f"Fetched forecast data for {city_name}: {num_timestamps} timestamps (3-hour intervals)"
    )

    faasr_put_file(
        local_file=output_name,
        remote_folder=folder_name,
        remote_file=output_name,
    )
    faasr_log(f"Uploaded forecast data to {folder_name}/{output_name}")
