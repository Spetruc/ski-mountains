# SnowScope — US Ski Mountain Explorer

A free GitHub Pages ski resort dashboard, built with React, Vite, Leaflet, Python, and GitHub Actions.

## Publish using GitHub's website (no terminal required)

1. Sign in to https://github.com and click **New repository**.
2. Name it `ski-mountains`, choose **Public**, and click **Create repository**.
3. Choose **uploading an existing file** on the new repository page.
4. Extract the downloaded ZIP **first**. Upload the **contents** of `ski-mountain-pages`, not the outer folder. **Important:** GitHub's web upload may not preserve hidden `.github` directories or nested folders reliably. If the `.github/workflows/` files do not appear after uploading, use GitHub's **Add file → Create new file** and enter `.github/workflows/deploy.yml`, then paste its contents; repeat for `weather.yml`. The easiest reliable method for all files is GitHub Desktop (see below).
5. In repository **Settings → Pages**, set **Source: GitHub Actions**.
6. In **Actions**, select **Update daily weather → Run workflow**. Wait for it to finish. This will write weather JSON and deploy the refreshed website.
7. In **Actions**, check **Deploy website**. Once green, visit `https://YOUR-USERNAME.github.io/ski-mountains/`.

### Easier upload: GitHub Desktop (recommended)

1. Install https://desktop.github.com/ and sign in.
2. Extract the ZIP, then in GitHub Desktop choose **File → Add local repository → Choose** the extracted folder. If it is not yet a Git repository, select **create a repository here**.
3. Commit the files and click **Publish repository**. Choose **Public** and repository name `ski-mountains`.
4. Follow steps 5–7 above.

## Important GitHub setting for automated updates

Under **Settings → Actions → General → Workflow permissions**, choose **Read and write permissions** if the weather job cannot push changes. The weather workflow also builds and deploys the website, because GitHub Actions pushes made with `GITHUB_TOKEN` do not trigger another push-based workflow run.

## Run locally (optional)

Install Node.js 22+ and Python 3.12+. In the extracted folder:

```sh
npm install
python scripts/update_weather.py
npm run dev
```

Open the URL printed by Vite (usually http://localhost:5173).

## What the data means

- The initial list is 41 manually seeded US resorts with approximate coordinates/elevations. It is **not** a complete or independently verified national directory.
- Weather is Open-Meteo **modeled** data, not station observations or resort-reported snow.
- `recent_snowfall_24h_in` uses Open-Meteo hourly modeled snowfall (cm) converted to inches. It is not measured accumulation.
- `base_depth_in`, `trails_open`, `lifts_open` and their totals are intentionally `null` until verified sources are integrated.
- Open-Meteo free noncommercial API is subject to its terms and usage limits: https://open-meteo.com/en/terms
- Map tiles are provided by OpenStreetMap; follow its tile usage policy: https://operations.osmfoundation.org/policies/tiles/

## Project structure

- `src/`: React website and styles
- `data/resorts.json`: resort directory
- `scripts/update_weather.py`: weather ingestion
- `public/weather.json`: generated weather snapshot
- `.github/workflows/`: deployment and scheduled weather jobs

## Next milestones

1. Import a validated, openly licensed US ski area directory.
2. Connect openly licensed resort operational reports with source timestamps.
3. Add source freshness and quality indicators.
4. Introduce weather history and regional JSON shards when the directory grows.

## Expand US resort coverage (new)

A manual GitHub Actions workflow, **Expand US resort directory (OpenStreetMap)**,
queries OpenStreetMap for named winter-sports areas in the United States.
It does **not** assume every mapped area is a verified operating downhill resort.
New entries are marked `needs_review: true`; some may be duplicates, closed,
Nordic-only, or missing their state/elevation. `Unverified` means the state was
not provided by OSM, not that it is a US state.

1. In **Actions**, open **Expand US resort directory (OpenStreetMap)**.
2. Click **Run workflow**, leave **apply_changes** unchecked, and run it.
3. Download the `osm-candidates` artifact from the completed workflow and
   inspect `osm_import_report.json`.
4. If the candidates look acceptable, run again with **apply_changes** checked.
   The workflow commits the expanded `data/resorts.json` directory to `main`.
5. **Deploy website** should run automatically from that commit.
6. Run **Update daily weather** to begin fetching new weather reports.

**Important:** Overpass is a community-operated public API and may time out or
rate-limit queries. If it fails, retry later rather than running frequent jobs.
OpenStreetMap data is licensed ODbL; preserve attribution and review obligations
before redistributing a modified database. Details: https://www.openstreetmap.org/copyright

Daily weather collection now updates up to **100 resorts per run**, prioritizing
resorts without weather. Larger directories take multiple days to fill in, and
existing snapshots remain available. A missing elevation uses Open-Meteo's
inferred model elevation; do not display it as a verified resort base elevation.


### Timeout-resistant importer (v0.3)
The importer now queries 14 smaller, overlapping geographic boxes intersected with the US OSM area, sequentially with retries and alternate Overpass endpoints. It writes checkpoint files under `data/osm_batches/` and deduplicates overlapping results by OSM object ID. These are still **unverified candidates**; preview before applying. GitHub Actions uploads batch checkpoints even when a later region fails. Public Overpass services can still be unavailable or rate-limited; retries are not a guarantee.
