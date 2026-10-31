"""The download code works, using fake web responses (no internet needed)."""
import io
import json

import pandas as pd
import pytest
import requests

from gasstore import config, storage, weather


class FakeResponse:
    def __init__(self, content=b"", payload=None):
        self.content, self._payload = content, payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RAW", tmp_path / "raw")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    return tmp_path


def test_weather_download_merges_archive_and_forecast(tmp_data, monkeypatch):
    monkeypatch.setattr(config, "WEATHER_START", "2024-01-01")
    calls = []

    def fake_get(url, params, timeout):
        calls.append(url)
        if url == config.ARCHIVE_URL:
            days = pd.date_range(params["start_date"], params["end_date"])
            temps = [40.0] * len(days)
        else:  # forecast: overlaps the archive by a few days, then goes past it
            days = pd.date_range(pd.Timestamp.today().normalize() - pd.Timedelta(days=14), periods=21)
            temps = [99.0] * len(days)
        return FakeResponse(payload={"daily": {"time": [d.strftime("%Y-%m-%d") for d in days],
                                               "temperature_2m_mean": temps}})

    monkeypatch.setattr(requests, "get", fake_get)
    d = weather.fetch_daily()
    assert set(d["city"]) == set(config.CITIES)
    assert not d.duplicated(["date", "city"]).any()
    assert (d.loc[d["source"] == "archive", "temp_f"] == 40).all()  # archive wins overlaps
    assert (d["source"] == "forecast").any()
    # A second run only asks the archive for days it doesn't have yet.
    calls.clear()
    weather.fetch_daily()
    assert calls.count(config.ARCHIVE_URL) == 0


def test_storage_falls_back_to_manual_file(tmp_data, monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("no internet")

    monkeypatch.setattr(requests, "get", boom)
    monkeypatch.delenv("EIA_API_KEY", raising=False)
    (tmp_data / "raw").mkdir()
    pd.DataFrame({"week_ending": ["2020-01-03", "2020-01-10"], "storage_bcf": [3000, 2900]}).to_csv(
        tmp_data / "raw" / "storage_manual.csv", index=False)
    df = storage.fetch_storage()
    assert list(df["storage_bcf"]) == [3000, 2900]


def test_storage_api_fallback(tmp_data, monkeypatch):
    def fake_get(url, params=None, timeout=None, headers=None):
        if url == config.XLS_URL:
            raise requests.HTTPError("404")
        return FakeResponse(payload={"response": {"data": [
            {"period": "2020-01-03", "value": "3000"}, {"period": "2020-01-10", "value": "2900"}]}})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setenv("EIA_API_KEY", "x")
    df = storage.fetch_storage()
    assert list(df["storage_bcf"]) == [3000, 2900]
