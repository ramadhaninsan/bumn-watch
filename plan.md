# BUMN Commissioner Scraper — Webwright Plan

## Goal
Scrape Board of Commissioners (Dewan Komisaris) from official BUMN websites using Playwright (Firefox headless) to handle JS-rendered pages. Extract commissioner names, roles, backgrounds, and detect political affiliations.

## BUMN Targets (POC — 5 major BUMN)
1. **Telkom** — https://www.telkom.co.id/sites/about-telkom/id_ID/page/dewan-komisaris-197
2. **Pertamina** — https://www.pertamina.com/id/dewan-komisaris
3. **PLN** — https://web.pln.co.id/tentang-kami/dewan-komisaris
4. **Bank Mandiri** — https://www.bankmandiri.co.id/dewan-komisaris-direksi
5. **BRI** — https://bri.co.id/web/guest/dewan-komisaris-direksi

## Critical Points
- [ ] CP1: Script launches headless Firefox and navigates to each BUMN commissioner page
- [ ] CP2: Waits for page content to fully render (JS-heavy SPA pages)
- [ ] CP3: Extracts commissioner names and roles from rendered DOM
- [ ] CP4: Extracts background/profile text for each commissioner where available
- [ ] CP5: Saves structured JSON + CSV output with all commissioner data
- [ ] CP6: Handles pages that fail to load gracefully (timeout, 403, DNS) with fallback
- [ ] CP7: CLI tool mode — reusable with `--bumn` flag to scrape specific BUMN

## Parameters
| Flag | Default | Description |
|------|---------|-------------|
| `--bumn` | `all` | Comma-separated BUMN names to scrape (e.g. `telkom,pln`) |
| `--output` | `output/` | Output directory for JSON/CSV |
| `--headless` | `true` | Run browser headless |

## Output Schema
```json
{
  "bumn_name": "PT Telkom Indonesia (Persero) Tbk",
  "short_name": "Telkom",
  "sector": "Telecommunications",
  "source_url": "https://...",
  "scrape_date": "2026-06-26T...",
  "commissioners": [
    {
      "name": "Angga Raka Prabowo",
      "role": "Komisaris Utama",
      "background": "...",
      "political_flag": true,
      "political_affiliation": "Wakil Menteri Komunikasi dan Digital",
      "raw_text": "..."
    }
  ]
}
```
