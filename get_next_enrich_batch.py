#!/usr/bin/env python3
"""Get next batch of commissioners to enrich."""
import json, os, sys

DB_PATH = '/root/bumn-commissioner-scraper/output/bumn_database_v9.json'
STATE_PATH = '/root/bumn-commissioner-scraper/output/enrich_state.json'
BATCH_SIZE = 10

with open(DB_PATH) as f:
    db = json.load(f)

if os.path.exists(STATE_PATH):
    with open(STATE_PATH) as f:
        state = json.load(f)
else:
    state = {"done": [], "batch_num": 0}

done_set = set(tuple(x) for x in state['done'])
candidates = [(c['name'], c['bumn']) for c in db['commissioners'] 
              if c.get('scrape_date') and c.get('status','belum_dianalisis') == 'belum_dianalisis'
              and (c['name'], c['bumn']) not in done_set]

if not candidates:
    print("ALL DONE")
    sys.exit(0)

batch = candidates[:BATCH_SIZE]
state['batch_num'] += 1
with open(STATE_PATH, 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print(json.dumps([{"name": n, "bumn": b} for n, b in batch], ensure_ascii=False))
