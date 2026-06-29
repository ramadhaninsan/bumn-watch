#!/usr/bin/env python3
"""
Get next batch of 10 unanalyzed commissioners.
Outputs JSON array of {name, bumn} for the next batch.
Tracks progress via a state file.
"""
import json, os, sys

DB_PATH = '/root/bumn-commissioner-scraper/output/bumn_database_v9.json'
STATE_PATH = '/root/bumn-commissioner-scraper/output/analysis_state.json'
BATCH_SIZE = 10

# Load DB
with open(DB_PATH) as f:
    db = json.load(f)

# Load state (which batch we're on)
if os.path.exists(STATE_PATH):
    with open(STATE_PATH) as f:
        state = json.load(f)
else:
    state = {"done": [], "batch_num": 0}

# Get all unanalyzed commissioners
unanalyzed = [(c['name'], c['bumn']) for c in db['commissioners'] 
              if c.get('status','belum_dianalisis') == 'belum_dianalisis']

# Filter out already-done ones
done_set = set(tuple(x) for x in state['done'])
remaining = [(n, b) for n, b in unanalyzed if (n, b) not in done_set]

if not remaining:
    print("ALL DONE")
    sys.exit(0)

# Get next batch
batch = remaining[:BATCH_SIZE]
state['batch_num'] += 1

# Output the batch as JSON
batch_json = json.dumps([{"name": n, "bumn": b} for n, b in batch], ensure_ascii=False)
print(batch_json)

# Save state
with open(STATE_PATH, 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
