"""Settings in one place: data sources, cities and their weights, model choices."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
OUTPUT = ROOT / "output"

# --- EIA weekly storage -----------------------------------------------------
# Lower 48 working gas in underground storage, Bcf, weeks ending Friday.
# The weekly report comes out Thursday 10:30 ET for the week ending the Friday before.
SERIES_ID = "NW2_EPG0_SWO_R48_BCF"
XLS_URL = "https://www.eia.gov/dnav/ng/hist_xls/NW2_EPG0_SWO_R48_BCFw.xls"
API_URL = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
# Optional: a free EIA API key (https://www.eia.gov/opendata/register.php) is used
# only if the Excel download fails. Put it in a file called eia_key.txt in the
# project folder, or in the EIA_API_KEY environment variable.

# --- Weather ----------------------------------------------------------------
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_PAUSE = 8.0  # seconds between long archive downloads (stays under the free per-minute limit)
BASE_F = 65.0  # degree days are measured from 65 °F, the US industry convention

# (lat, lon, heating weight, cooling weight)
# Heating weights lean toward the cold, gas-heated North-East and Midwest, where
# winter withdrawals come from. Cooling weights lean toward Texas, the South and
# California, where summer air-conditioning load is met by gas-fired power plants.
# These are rough hand-set weights, not official ones: a trading desk would use
# gas-customer or population weights. Changing them is a good experiment.
CITIES = {
    "Chicago":      (41.88, -87.63, 0.13, 0.06),
    "New York":     (40.71, -74.01, 0.13, 0.09),
    "Boston":       (42.36, -71.06, 0.05, 0.02),
    "Philadelphia": (39.95, -75.17, 0.06, 0.04),
    "Washington":   (38.91, -77.04, 0.05, 0.05),
    "Pittsburgh":   (40.44, -79.99, 0.05, 0.02),
    "Detroit":      (42.33, -83.05, 0.08, 0.03),
    "Columbus":     (39.96, -83.00, 0.05, 0.02),
    "Minneapolis":  (44.98, -93.27, 0.06, 0.02),
    "Kansas City":  (39.10, -94.58, 0.04, 0.03),
    "Denver":       (39.74, -104.99, 0.04, 0.02),
    "Atlanta":      (33.75, -84.39, 0.05, 0.08),
    "Dallas":       (32.78, -96.80, 0.06, 0.14),
    "Houston":      (29.76, -95.37, 0.04, 0.14),
    "Phoenix":      (33.45, -112.07, 0.01, 0.07),
    "Los Angeles":  (34.05, -118.24, 0.06, 0.08),
    "Miami":        (25.76, -80.19, 0.00, 0.09),
}

# --- Analysis ---------------------------------------------------------------
STORAGE_START = "2010-01-01"   # first week of the current EIA weekly series
WEATHER_START = "2000-01-01"   # earlier, so weather "normals" exist from 2010
NORMAL_YEARS = 10              # weather normal = average of the previous 10 years
TEST_START = "2018-01-01"      # walk-forward evaluation starts here
HOLDOUT_START = "2022-01-01"   # model choices were made on 2018-2021 only; 2022 on is the untouched test
DRIFT_YEARS = 3                # the weather-adjusted model only learns from recent years
INTERVAL = 0.80                # prediction interval coverage target
RANDOM_SEED = 0
