"""
weather_fetcher.py
------------------
Fetches weather risk data for Gujarat manufacturing hubs
using Open-Meteo API (completely free, no API key required).

Monitors: Ahmedabad, Surat, Vadodara, Rajkot, Kandla, Mundra
API Docs: https://open-meteo.com/en/docs
"""

import requests
from dotenv import load_dotenv

load_dotenv()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# ─────────────────────────────────────────────
# GUJARAT MANUFACTURING HUBS
# ─────────────────────────────────────────────

MONITORED_CITIES = [
    {"name": "Ahmedabad", "lat": 23.0225, "lon": 72.5714, "role": "Pharma, textiles, FMCG hub"},
    {"name": "Surat",     "lat": 21.1702, "lon": 72.8311, "role": "Textiles, diamonds, chemicals"},
    {"name": "Vadodara",  "lat": 22.3072, "lon": 73.1812, "role": "Petrochemicals, engineering"},
    {"name": "Rajkot",    "lat": 22.3039, "lon": 70.8022, "role": "Auto parts, engineering goods"},
    {"name": "Kandla",    "lat": 23.0333, "lon": 70.2167, "role": "Kandla Port — largest cargo port"},
    {"name": "Mundra",    "lat": 22.8392, "lon": 69.7229, "role": "Mundra Port — major container terminal"},
]

# WMO Weather Codes that signal supply chain risk
# Full list: https://open-meteo.com/en/docs#weathervariables
SEVERE_WMO_CODES = {
    51: ("Light drizzle",           1),
    53: ("Moderate drizzle",        2),
    55: ("Dense drizzle",           2),
    61: ("Slight rain",             2),
    63: ("Moderate rain",           3),
    65: ("Heavy rain",              4),
    71: ("Slight snow",             2),
    73: ("Moderate snow",           3),
    75: ("Heavy snow",              4),
    77: ("Snow grains",             2),
    80: ("Slight rain showers",     2),
    81: ("Moderate rain showers",   3),
    82: ("Violent rain showers",    5),
    85: ("Slight snow showers",     2),
    86: ("Heavy snow showers",      4),
    95: ("Thunderstorm",            4),
    96: ("Thunderstorm with hail",  5),
    99: ("Thunderstorm heavy hail", 5),
}

WIND_RISK_THRESHOLDS = {5: 80, 4: 60, 3: 40, 2: 25}
RAIN_RISK_THRESHOLDS = {5: 50, 4: 30, 3: 15, 2: 8}


# ─────────────────────────────────────────────
# FETCHER
# ─────────────────────────────────────────────

def fetch_weather_for_city(city: dict) -> dict | None:
    """Fetches current weather for a city using Open-Meteo (no API key needed)."""
    params = {
        "latitude":            city["lat"],
        "longitude":           city["lon"],
        "current":             "temperature_2m,windspeed_10m,precipitation,weathercode,visibility",
        "windspeed_unit":      "kmh",
        "precipitation_unit":  "mm",
        "forecast_days":       1,
    }

    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Weather fetch failed for {city['name']}: {e}")
        return None


def assess_weather_risk(weather_data: dict, city: dict) -> dict:
    """Assesses supply chain risk from Open-Meteo weather data."""
    current      = weather_data.get("current", {})
    wmo_code     = current.get("weathercode", 0)
    wind_kph     = current.get("windspeed_10m", 0)
    precip_mm    = current.get("precipitation", 0)
    temp_c       = current.get("temperature_2m", 25)
    vis_m        = current.get("visibility", 10000)
    vis_km       = vis_m / 1000 if vis_m else 10

    # Score each factor
    wmo_info           = SEVERE_WMO_CODES.get(wmo_code, ("Clear", 0))
    condition_text     = wmo_info[0]
    condition_severity = wmo_info[1]

    wind_severity = 0
    for sev, threshold in sorted(WIND_RISK_THRESHOLDS.items(), reverse=True):
        if wind_kph >= threshold:
            wind_severity = sev
            break

    rain_severity = 0
    for sev, threshold in sorted(RAIN_RISK_THRESHOLDS.items(), reverse=True):
        if precip_mm >= threshold:
            rain_severity = sev
            break

    vis_severity = 3 if vis_km < 1 else 2 if vis_km < 3 else 0

    max_severity = max(condition_severity, wind_severity, rain_severity, vis_severity)

    risk_factors = []
    if condition_severity >= 3: risk_factors.append(condition_text)
    if wind_severity >= 3:      risk_factors.append(f"wind {wind_kph:.0f}kph")
    if rain_severity >= 3:      risk_factors.append(f"rain {precip_mm:.1f}mm")
    if vis_severity >= 2:       risk_factors.append(f"visibility {vis_km:.1f}km")

    is_risk   = max_severity >= 3
    risk_desc = ", ".join(risk_factors) if risk_factors else "Normal conditions"

    return {
        "city":        city["name"],
        "role":        city["role"],
        "condition":   condition_text,
        "wmo_code":    wmo_code,
        "temp_c":      temp_c,
        "wind_kph":    wind_kph,
        "precip_mm":   precip_mm,
        "vis_km":      vis_km,
        "severity":    max_severity,
        "is_risk":     is_risk,
        "risk_factors": risk_factors,
        "risk_desc":   risk_desc,
    }


def fetch_all_weather_risks() -> list[dict]:
    """
    Main function. Fetches weather for all Gujarat hubs,
    assesses risk, returns sorted assessments.
    """
    print(f"\n[WEATHER FETCHER] Checking {len(MONITORED_CITIES)} Gujarat manufacturing hubs...\n")

    assessments = []
    for city in MONITORED_CITIES:
        data = fetch_weather_for_city(city)
        if not data:
            continue

        assessment = assess_weather_risk(data, city)
        assessments.append(assessment)

        status = "⚠️  RISK" if assessment["is_risk"] else "✅ OK  "
        print(
            f"  {assessment['city']:<12} "
            f"{assessment['condition']:<25} "
            f"💨 {assessment['wind_kph']:.0f}kph  "
            f"🌧 {assessment['precip_mm']:.1f}mm  "
            f"{status}"
        )

    assessments.sort(key=lambda x: x["severity"], reverse=True)
    risk_cities = [a for a in assessments if a["is_risk"]]
    print(f"\n[WEATHER FETCHER] {len(risk_cities)}/{len(assessments)} cities showing weather risk\n")
    return assessments


def get_weather_risk_articles(assessments: list[dict]) -> list[dict]:
    """
    Converts weather risk assessments into article-like dicts
    so they feed directly into the existing risk scorer pipeline.
    """
    articles = []
    for a in assessments:
        if not a["is_risk"]:
            continue
        articles.append({
            "title":           f"Weather alert: {a['risk_desc']} in {a['city']}, Gujarat",
            "description":     (
                f"{a['condition']} conditions in {a['city']} ({a['role']}). "
                f"Wind: {a['wind_kph']:.0f}kph, Rain: {a['precip_mm']:.1f}mm, "
                f"Visibility: {a['vis_km']:.1f}km. "
                f"Supply chain disruption risk for manufacturing and port operations."
            ),
            "url":             f"weather://live/{a['city'].lower()}",
            "source":          "Open-Meteo Live",
            "published_at":    "",
            "content_snippet": "",
            "is_weather":      True,
            "severity_hint":   a["severity"],
        })
    return articles


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    assessments = fetch_all_weather_risks()

    print(f"{'─'*60}")
    print(f"WEATHER RISK SUMMARY — Gujarat Manufacturing Hubs")
    print(f"{'─'*60}")

    for a in assessments:
        risk_tag = f" ⚠️  Severity {a['severity']}" if a["is_risk"] else ""
        print(f"\n{a['city']} ({a['role']})")
        print(f"  Condition : {a['condition']}{risk_tag}")
        print(f"  Wind      : {a['wind_kph']:.0f} kph")
        print(f"  Rain      : {a['precip_mm']:.1f} mm")
        print(f"  Temp      : {a['temp_c']:.1f}°C")

    weather_articles = get_weather_risk_articles(assessments)
    if weather_articles:
        print(f"\n{'─'*60}")
        print(f"SIGNALS FOR RISK SCORER ({len(weather_articles)} weather articles):")
        for a in weather_articles:
            print(f"\n  {a['title']}")
    else:
        print(f"\n✅ No weather risks in Gujarat hubs today.")