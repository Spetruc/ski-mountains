"""Conservative OpenStreetMap resort candidate importer.

Runs on demand, not daily. Keeps existing records and flags imported records for review.
Usage: python scripts/import_osm_resorts.py --preview
       python scripts/import_osm_resorts.py --apply
"""
import argparse
import json
import math
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data' / 'resorts.json'
REPORT = ROOT / 'data' / 'osm_import_report.json'
ENDPOINT = 'https://overpass.kumi.systems/api/interpreter'
# Areas explicitly tagged as winter-sports destinations or piste sites.
QUERY = '''[out:json][timeout:180];
area["ISO3166-1"="US"][admin_level=2]->.usa;
(
 nwr["landuse"="winter_sports"]["name"](area.usa);
 nwr["site"="piste"]["name"](area.usa);
 nwr["sport"="skiing"]["name"]["leisure"="sports_centre"](area.usa);
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
    request = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode({'data': QUERY}).encode(), headers={'User-Agent': 'SnowScope/0.2 (noncommercial resort directory importer)'})
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.load(response)['elements']


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
