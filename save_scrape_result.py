#!/usr/bin/env python3
"""
Save scrape results to database, output separate JSON files, and git push.
No more HTML embedding — data loads via fetch at runtime.
"""
import json, os, sys, subprocess
from collections import Counter

DB_PATH = '/root/bumn-commissioner-scraper/output/bumn_database_v9.json'
RESULT_PATH = '/tmp/scrape_result.json'
STATE_PATH = '/root/bumn-commissioner-scraper/output/scrape_state.json'
DOCS_DIR = '/root/bumn-commissioner-scraper/docs'

if not os.path.exists(RESULT_PATH):
    print("No result file found")
    sys.exit(1)

with open(DB_PATH) as f:
    db = json.load(f)

with open(RESULT_PATH) as f:
    results = json.load(f)

added = 0
updated = 0
source_type = ''

for r in results:
    bumn = r.get('bumn', '')
    source_url = r.get('source_url', '')
    source_type = r.get('source_type', '')
    commissioners = r.get('commissioners', [])
    
    for c in commissioners:
        name = c.get('name', '').strip()
        role = c.get('role', 'Komisaris')
        
        if not name or len(name) < 3:
            continue
        
        found = False
        for existing in db['commissioners']:
            if existing['name'].lower() == name.lower() and existing['bumn'].lower() == bumn.lower():
                if role and len(role) >= len(existing.get('role', '')):
                    existing['role'] = role
                existing['source_url'] = source_url
                existing['source_type'] = source_type
                existing['scrape_date'] = '2026-06-29'
                updated += 1
                found = True
                break
        
        if not found:
            db['commissioners'].append({
                'name': name,
                'bumn': bumn,
                'role': role,
                'sector': '',
                'status': 'belum_dianalisis',
                'party': '',
                'political_affiliation': '',
                'evidence': '',
                'family_connections': '',
                'legal_record': {},
                'photo_url': '',
                'sources': [],
                'source_url': source_url,
                'source_type': source_type,
                'scrape_date': '2026-06-29',
                'is_rangkap_jabatan': False,
                'is_tni_polri': False,
                'is_partai_kader': False,
                'is_relawan_politik': False,
                'is_ormas': False,
                'is_family_connection': False,
            })
            added += 1
    
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            state = json.load(f)
    else:
        state = {"done": [], "batch_num": 0}
    
    if bumn not in state['done']:
        state['done'].append(bumn)
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

status = Counter(c.get('status','belum_dianalisis') for c in db['commissioners'])
db['version'] = '10.0'

# Save DB
with open(DB_PATH, 'w') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

# Output separate JSON files for frontend (no HTML embedding)
with open(os.path.join(DOCS_DIR, 'data.json'), 'w') as f:
    json.dump(db['commissioners'], f, ensure_ascii=False)
with open(os.path.join(DOCS_DIR, 'bumn.json'), 'w') as f:
    json.dump(db.get('master_bumn', []), f, ensure_ascii=False)
with open(os.path.join(DOCS_DIR, 'bumd.json'), 'w') as f:
    json.dump(db.get('master_bumd', []), f, ensure_ascii=False)

# Git push
subprocess.run(['git', 'add', '-A'], cwd='/root/bumn-commissioner-scraper')
total = len(db['commissioners'])
bumn_count = len(set(c['bumn'] for c in db['commissioners']))
scraped_count = sum(1 for c in db['commissioners'] if c.get('scrape_date'))
commit_msg = f"Scrape batch: {added} added, {updated} updated ({total} total, {bumn_count} BUMN, {scraped_count} verified)"
subprocess.run(['git', 'commit', '-m', commit_msg], cwd='/root/bumn-commissioner-scraper')
subprocess.run(['git', 'push'], cwd='/root/bumn-commissioner-scraper')

print(f"Added: {added}, Updated: {updated}")
print(f"Total: {total} commissioners, {bumn_count} BUMN")
print(f"Verified from official: {scraped_count}")
print(f"Status: {dict(status)}")
print("JSON files updated + pushed to git")
