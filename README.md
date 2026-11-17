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
