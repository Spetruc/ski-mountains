"""Conservative OpenStreetMap resort candidate importer.

Runs on demand, not daily. Keeps existing records and flags imported records for review.
Usage: python scripts/import_osm_resorts.py --preview
       python scripts/import_osm_resorts.py --apply
"""
import argparse
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data' / 'resorts.json'
REPORT = ROOT / 'data' / 'osm_import_report.json'
ENDPOINTS = [
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass-api.de/api/interpreter',
]
# Small overlapping US bounding boxes, intersected with the US country area.
# Deliberately excludes territories; candidates are still marked for review.
REGIONS = {
    'northeast': (39.0, -80.5, 48.0, -66.0),
    'mid_atlantic': (35.0, -84.5, 42.0, -74.0),
    'southeast': (24.0, -92.0, 36.0, -75.0),
    'great_lakes': (40.0, -93.0, 49.5, -80.0),
    'central': (32.0, -104.0, 43.0, -89.0),
    'northern_plains': (42.0, -105.0, 49.5, -92.0),
    'rockies_north': (41.0, -117.0, 49.5, -103.0),
    'rockies_south': (31.0, -115.0, 42.0, -102.0),
    'pacific_north': (41.0, -125.0, 49.5, -115.0),
    'pacific_south': (32.0, -125.0, 42.0, -113.0),
    'alaska_south': (51.0, -170.0, 63.0, -129.0),
    'alaska_north': (62.0, -170.0, 72.0, -129.0),
    'alaska_west': (51.0, -180.0, 72.0, -169.0),
    'hawaii': (18.0, -161.0, 23.0, -154.0),
}
CACHE = ROOT / 'data' / 'osm_batches'


def query_for(bbox):
    bounds = ','.join(map(str, bbox))
    return f'''[out:json][timeout:70];
area["ISO3166-1"="US"][admin_level=2]->.usa;
(
 nwr["landuse"="winter_sports"]["name"](area.usa)({bounds});
 nwr["site"="piste"]["name"](area.usa)({bounds});
 nwr["sport"="skiing"]["name"]["leisure"="sports_centre"](area.usa)({bounds});
);
out center tags;'''

EXCLUDE = re.compile(r'\b(trail|chairlift|gondola|magic carpet|parking|ski school|rental|snowmobile|cross.country|nordic center|nordic centre)\b', re.I)


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:65]


def distance_km(a, b):
    p1, p2 = math.radians(a['lat']), math.radians(b['lat'])
    dlat, dlon = p2-p1, math.radians(b['lon']-a['lon'])
    h = math.sin(dlat/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlon/2)**2
    return 12742*math.asin(min(1, math.sqrt(h)))


def download():
    CACHE.mkdir(parents=True, exist_ok=True)
    combined = {}
    for region, bbox in REGIONS.items():
        checkpoint = CACHE / f'{region}.json'
        if checkpoint.exists():
            elements = json.loads(checkpoint.read_text(encoding='utf-8'))
            print(f'{region}: using saved batch ({len(elements)} features)', flush=True)
        else:
            last_error = None
            for attempt in range(4):
                endpoint = ENDPOINTS[attempt % len(ENDPOINTS)]
                request = urllib.request.Request(
                    endpoint,
                    data=urllib.parse.urlencode({'data': query_for(bbox)}).encode(),
                    headers={'User-Agent': 'SnowScope/0.3 (open-source ski resort directory; sequential requests)'})
                try:
                    print(f'{region}: request {attempt + 1}/4', flush=True)
                    with urllib.request.urlopen(request, timeout=105) as response:
                        payload = json.load(response)
                    elements = payload['elements']
                    checkpoint.write_text(json.dumps(elements), encoding='utf-8')
                    print(f'{region}: received {len(elements)} features', flush=True)
                    break
                except (OSError, ValueError, KeyError) as exc:
                    last_error = exc
                    print(f'{region}: {type(exc).__name__}: {exc}', flush=True)
                    time.sleep(5 * (attempt + 1))
            else:
                raise RuntimeError(
                    f'{region} failed after retries; completed batch files remain available. '
                    f'Last error: {last_error}')
            time.sleep(2)
        for element in elements:
            combined[(element['type'], element['id'])] = element
    return list(combined.values())


def collect(elements, existing):
    candidates, skipped = [], {'invalid': 0, 'excluded': 0, 'duplicate': 0}
    seen = list(existing)
    for element in elements:
        tags = element.get('tags', {})
        name = (tags.get('name:en') or tags.get('name') or '').strip()
        loc = element.get('center', element)
        lat, lon = loc.get('lat'), loc.get('lon')
        if not name or not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)) or not (18 <= lat <= 72 and -180 <= lon <= -65):
            skipped['invalid'] += 1
            continue
        if EXCLUDE.search(name) or tags.get('piste:type') or tags.get('disused') == 'yes' or tags.get('abandoned') == 'yes':
            skipped['excluded'] += 1
            continue
        item = {'id': f"osm-{element['type']}-{element['id']}", 'name': name,
                'state': tags.get('addr:state') or tags.get('is_in:state') or 'Unverified',
                'lat': round(lat, 6), 'lon': round(lon, 6),
                'elevation_m': None, 'source': 'OpenStreetMap',
                'osm_ref': f"{element['type']}/{element['id']}", 'needs_review': True}
        # Conservative geographic/name duplicate filter; candidates remain auditable.
        if any(distance_km(item, other) < 3 and (slug(item['name']) == slug(other['name']) or distance_km(item, other) < 0.35) for other in seen):
            skipped['duplicate'] += 1
            continue
        candidates.append(item)
        seen.append(item)
    return candidates, skipped


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preview', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    existing = json.loads(DEST.read_text(encoding='utf-8'))
    elements = download()
    if not elements:
        raise RuntimeError('OpenStreetMap query returned no features; refusing to change directory')
    candidates, skipped = collect(elements, existing)
    report = {'existing_count': len(existing), 'osm_elements': len(elements),
              'new_candidates': len(candidates), 'skipped': skipped,
              'note': 'OSM candidates are unverified. Review names, state, elevations and duplicates.',
              'candidates': candidates}
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"OSM elements: {len(elements)}; existing: {len(existing)}; new candidates: {len(candidates)}; skipped: {skipped}")
    if args.apply:
        if len(candidates) > 1500:
            raise RuntimeError('Unexpectedly large import; inspect report before applying')
        DEST.write_text(json.dumps(existing + candidates, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f'Applied {len(candidates)} candidates; inspect data/osm_import_report.json')
    else:
        print('Preview only: resort directory unchanged')


if __name__ == '__main__':
    main()
