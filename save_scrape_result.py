#!/usr/bin/env python3
"""
Save scrape results to database and update state file.
"""
import json, os, sys, re, subprocess
from collections import Counter

DB_PATH = '/root/bumn-commissioner-scraper/output/bumn_database_v9.json'
RESULT_PATH = '/tmp/scrape_result.json'
STATE_PATH = '/root/bumn-commissioner-scraper/output/scrape_state.json'

if not os.path.exists(RESULT_PATH):
    print("No result file found")
    sys.exit(1)

with open(DB_PATH) as f:
    db = json.load(f)

with open(RESULT_PATH) as f:
    results = json.load(f)

added = 0
updated = 0

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
        
        # Check if already exists
        found = False
        for existing in db['commissioners']:
            if existing['name'].lower() == name.lower() and existing['bumn'].lower() == bumn.lower():
                # Update role if better
                if role and len(role) > len(existing.get('role', '')):
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
                'scrape_date': '2026-06-29'
            })
            added += 1
    
    # Update state
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            state = json.load(f)
    else:
        state = {"done": [], "batch_num": 0}
    
    if bumn not in state['done']:
        state['done'].append(bumn)
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# Update version
status = Counter(c.get('status','belum_dianalisis') for c in db['commissioners'])
db['version'] = '10.0'

with open(DB_PATH, 'w') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

# Embed into dashboard
DASHBOARD_PATH = '/root/bumn-commissioner-scraper/dashboard/index.html'
DOCS_PATH = '/root/bumn-commissioner-scraper/docs/index.html'

with open(DASHBOARD_PATH) as f:
    html = f.read()

comm_js = json.dumps(db['commissioners'], ensure_ascii=False, indent=2)
bumn_js = json.dumps(db.get('master_bumn', []), ensure_ascii=False, indent=2)
bumd_js = json.dumps(db.get('master_bumd', []), ensure_ascii=False, indent=2)

html = re.sub(r'const D=\[.*?\];', f'const D={comm_js};', html, count=1, flags=re.DOTALL)
html = re.sub(r'const BUMN_MASTER=\[.*?\];', f'const BUMN_MASTER={bumn_js};', html, count=1, flags=re.DOTALL)
html = re.sub(r'const BUMD_MASTER=\[.*?\];', f'const BUMD_MASTER={bumd_js};', html, count=1, flags=re.DOTALL)
html = re.sub(r'const SUBS=\[.*?\];', f'const SUBS={bumn_js};', html, count=1, flags=re.DOTALL)
html = re.sub(r'const BUMD=\[.*?\];', f'const BUMD={bumd_js};', html, count=1, flags=re.DOTALL)

with open(DASHBOARD_PATH, 'w') as f:
    f.write(html)
with open(DOCS_PATH, 'w') as f:
    f.write(html)

# Git push
subprocess.run(['git', 'add', '-A'], cwd='/root/bumn-commissioner-scraper')
total = len(db['commissioners'])
bumn_count = len(set(c['bumn'] for c in db['commissioners']))
commit_msg = f"v10.0: Official scrape batch — {added} added, {updated} updated ({total} total, {bumn_count} BUMN)\nSource: {source_type}"
subprocess.run(['git', 'commit', '-m', commit_msg], cwd='/root/bumn-commissioner-scraper')
subprocess.run(['git', 'push'], cwd='/root/bumn-commissioner-scraper')

print(f"Added: {added}, Updated: {updated}")
print(f"Total: {total} commissioners, {bumn_count} BUMN")
print(f"Status: {dict(status)}")
print("Dashboard updated + pushed to git")