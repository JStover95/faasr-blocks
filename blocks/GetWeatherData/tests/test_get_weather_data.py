"""Unit tests for GetWeatherData block (happy path + missing secret)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from faasr_blocks.testing.harness import faasr_test_environment

BLOCK_ROOT = Path(__file__).resolve().parent.parent
SRC = BLOCK_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import blocks.GetWeatherData.src.get_weather_data as get_weather_data  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_get_weather_data_success():
    """Happy path: secret, HTTP response, S3 put, logs."""
    payload = json.loads((FIXTURES_DIR / "mock_weather_response.json").read_text(encoding="utf-8"))

    with faasr_test_environment(FIXTURES_DIR, "blocks.GetWeatherData.src.get_weather_data") as env:
        env.secret.with_secret("OPENWEATHER_API_KEY", "test_api_key")

        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status = MagicMock()

        with patch.object(get_weather_data.requests, "get", return_value=mock_resp):
            get_weather_data.get_weather_data(
                folder_name="test_folder",
                output_name="weather.json",
                lat="44.5646",
                lon="-123.2620",
                location_name="Corvallis, OR",
            )

        assert len(env.put_file.uploaded_files) == 1
        up = env.put_file.uploaded_files[0]
        assert up["remote_file"] == "weather.json"
        assert up["remote_folder"] == "test_folder"
        assert up["dest_path"].exists()
        written = json.loads(up["dest_path"].read_text(encoding="utf-8"))
        assert written["city"]["name"] == "Corvallis"
        assert len(written["list"]) == 2

        assert "Successfully retrieved API key" in env.log.log_messages
        assert any("Fetched forecast data for Corvallis" in m for m in env.log.log_messages)


def test_get_weather_data_missing_secret():
    """Missing OPENWEATHER_API_KEY raises before HTTP call."""
    with faasr_test_environment(FIXTURES_DIR, "blocks.GetWeatherData.src.get_weather_data"):
        with patch.object(get_weather_data.requests, "get") as mock_get:
            with pytest.raises(KeyError, match="OPENWEATHER_API_KEY"):
                get_weather_data.get_weather_data(
                    folder_name="test_folder",
                    output_name="weather.json",
                    lat="44.5646",
                    lon="-123.2620",
                    location_name="Corvallis, OR",
                )
            mock_get.assert_not_called()
