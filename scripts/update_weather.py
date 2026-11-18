"""Fetch free Open-Meteo modeled weather and daily forecast for listed US resorts.
Run with: python scripts/update_weather.py
No third-party Python packages needed.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESORTS = ROOT / 'data' / 'resorts.json'
OUTPUT = ROOT / 'public' / 'weather.json'
API = 'https://api.open-meteo.com/v1/forecast'


def fetch(resort):
    params = {
        'latitude': resort['lat'], 'longitude': resort['lon'],
        'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,snowfall,weather_code',
        'hourly': 'snowfall',
        'daily': 'temperature_2m_max,temperature_2m_min,snowfall_sum,precipitation_sum,weather_code',
        'temperature_unit': 'fahrenheit', 'wind_speed_unit': 'mph',
        'precipitation_unit': 'inch', 'timezone': 'auto', 'forecast_days': 7,
        'past_days': 2,
    }
    if resort.get('elevation_m') is not None:
        params['elevation'] = resort['elevation_m']
    url = API + '?' + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={'User-Agent': 'SnowScope-MVP/0.1 (GitHub Pages weather dashboard)'})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = json.load(response)
    hourly = raw.get('hourly', {})
    dates = hourly.get('time', [])
    snowfall = hourly.get('snowfall', [])
    current_time = raw.get('current', {}).get('time', '')
    # Hourly snowfall from Open-Meteo is in centimeters; convert to inches.
    recent = [float(v or 0) for t, v in zip(dates, snowfall) if current_time and t <= current_time]
    daily = raw.get('daily', {})
    return {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'Open-Meteo modeled weather',
        'current': raw.get('current', {}),
        'recent_snowfall_24h_in': round(sum(recent[-24:]) / 2.54, 1) if len(recent) >= 24 else None,
        'daily': [{
            'date': day,
            'high_f': daily.get('temperature_2m_max', [None]*len(daily['time']))[i],
            'low_f': daily.get('temperature_2m_min', [None]*len(daily['time']))[i],
            'snowfall_in': round((daily.get('snowfall_sum', [0]*len(daily['time']))[i] or 0) / 2.54, 1),
            'weather_code': daily.get('weather_code', [None]*len(daily['time']))[i]
        } for i, day in enumerate(daily.get('time', [])) if day >= current_time[:10]][:7],
        'base_depth_in': None, 'trails_open': None, 'trails_total': None,
        'lifts_open': None, 'lifts_total': None,
    }


def main():
    resorts = json.loads(RESORTS.read_text(encoding='utf-8'))
    existing = {}
    if OUTPUT.exists():
        try:
            existing = json.loads(OUTPUT.read_text(encoding='utf-8')).get('resorts', {})
        except (ValueError, OSError):
            pass
    # Cap daily calls for free-tier courtesy. Rotate through the directory,
    # while prioritizing mountains that have never received weather.
    from datetime import date
    batch_size = 100
    missing = [r for r in resorts if r['id'] not in existing]
    present = [r for r in resorts if r['id'] in existing]
    offset = (date.today().toordinal() * batch_size) % max(1, len(present))
    ordered = missing + (present[offset:] + present[:offset])
    batch = ordered[:batch_size]
    updated = 0
    for resort in batch:
        try:
            existing[resort['id']] = fetch(resort)
            updated += 1
            print(f"OK {resort['name']}", flush=True)
        except Exception as exc:
            print(f"FAILED {resort['name']}: {exc}", flush=True)
        time.sleep(0.3)
    if updated == 0:
        raise RuntimeError('No resort weather fetched; refusing to publish empty update')
    payload = {'generated_at': datetime.now(timezone.utc).isoformat(), 'resorts': existing}
    OUTPUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(f'Updated {updated}/{len(batch)} selected resorts ({len(resorts)} listed total)')

if __name__ == '__main__':
    main()
