#!/usr/bin/env python3
"""
Get next batch of BUMN to scrape from official sources.
Outputs JSON array of {name, search_query} for the next batch.
"""
import json, os, sys

STATE_PATH = '/root/bumn-commissioner-scraper/output/scrape_state.json'
BATCH_SIZE = 3  # 3 BUMN per run to avoid timeout

# All BUMN that need official scraping
BUMN_TO_SCRAPE = [
    {"name": "Garuda Indonesia", "query": "Garuda Indonesia dewan komisaris 2025 2026 site:garuda-indonesia.com OR site:garuda-indonesia.co.id"},
    {"name": "ASDP", "query": "ASDP Indonesia Ferry dewan komisaris 2025 2026"},
    {"name": "KAI", "query": "Kereta Api Indonesia KAI dewan komisaris 2025 2026 site:kai.id"},
    {"name": "Pelindo", "query": "Pelindo dewan komisaris 2025 2026 site:pelindo.co.id"},
    {"name": "Jasa Marga", "query": "Jasa Marga dewan komisaris 2025 2026 site:jasamarga.com"},
    {"name": "Pupuk Indonesia", "query": "Pupuk Indonesia dewan komisaris 2025 2026 site:pupuk-indonesia.com"},
    {"name": "Semen Indonesia", "query": "Semen Indonesia SIG dewan komisaris 2025 2026 site:sig.id"},
    {"name": "Aneka Tambang (Antam)", "query": "Antam Aneka Tambang dewan komisaris 2025 2026 site:antam.com"},
    {"name": "Bukit Asam (PTBA)", "query": "Bukit Asam PTBA dewan komisaris 2025 2026 site:ptba.co.id"},
    {"name": "Timah", "query": "Timah dewan komisaris 2025 2026 site:timah.com"},
    {"name": "Inalum", "query": "Inalum Indonesia Asahan Aluminium dewan komisaris 2025 2026 site:inalum.id"},
    {"name": "Wijaya Karya", "query": "Wijaya Karya WIKA dewan komisaris 2025 2026 site:wijayakarya.co.id"},
    {"name": "Adhi Karya", "query": "Adhi Karya dewan komisaris 2025 2026 site:adhi.co.id"},
    {"name": "Waskita Karya", "query": "Waskita Karya dewan komisaris 2025 2026 site:waskita.co.id"},
    {"name": "Hutama Karya", "query": "Hutama Karya dewan komisaris 2025 2026 site:hutamakarya.com"},
    {"name": "Kimia Farma", "query": "Kimia Farma dewan komisaris 2025 2026 site:kimiafarma.co.id"},
    {"name": "Bio Farma", "query": "Bio Farma dewan komisaris 2025 2026 site:biofarma.co.id"},
    {"name": "LEN Industri", "query": "LEN Industri dewan komisaris 2025 2026 site:len.co.id"},
    {"name": "Pos Indonesia", "query": "Pos Indonesia dewan komisaris 2025 2026 site:posindonesia.co.id"},
    {"name": "Perum Peruri", "query": "Peruri Percetakan Uang dewan komisaris 2025 2026 site:peruri.co.id"},
    {"name": "BULOG", "query": "BULOG dewan pengawas komisaris 2025 2026 site:bulog.co.id"},
    {"name": "PTPN", "query": "PTPN Perkebunan Nusantara dewan komisaris 2025 2026 site:ptpn.co.id"},
    {"name": "Krakatau Steel", "query": "Krakatau Steel dewan komisaris 2025 2026 site:krakatausteel.com"},
    {"name": "ID FOOD", "query": "ID FOOD dewan komisaris 2025 2026 site:idfood.co.id"},
    {"name": "InJourney", "query": "InJourney dewan komisaris 2025 2026 site:injourney.com"},
    {"name": "Indosat", "query": "Indosat Ooredoo Hutchison dewan komisaris 2025 2026 site:indosatooredoo.com"},
]

# Load state
if os.path.exists(STATE_PATH):
    with open(STATE_PATH) as f:
        state = json.load(f)
else:
    state = {"done": [], "batch_num": 0}

# Filter out done BUMN
done_names = set(state['done'])
remaining = [b for b in BUMN_TO_SCRAPE if b['name'] not in done_names]

if not remaining:
    print("ALL DONE")
    sys.exit(0)

# Get next batch
batch = remaining[:BATCH_SIZE]
state['batch_num'] += 1

# Output
batch_json = json.dumps(batch, ensure_ascii=False)
print(batch_json)

# Save state
with open(STATE_PATH, 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
