#!/usr/bin/env python3
"""
Merge analysis results back into the main database.
Input: reads /tmp/batch_result.json (array of commissioner updates)
Updates the main DB with political_affiliation, party, status, evidence, etc.
Then embeds into dashboard HTML and pushes to git.
"""
import json, os, sys, re, subprocess
from collections import Counter

DB_PATH = '/root/bumn-commissioner-scraper/output/bumn_database_v9.json'
RESULT_PATH = '/tmp/batch_result.json'
DASHBOARD_PATH = '/root/bumn-commissioner-scraper/dashboard/index.html'
DOCS_PATH = '/root/bumn-commissioner-scraper/docs/index.html'

if not os.path.exists(RESULT_PATH):
    print("No result file found")
    sys.exit(1)

with open(DB_PATH) as f:
    db = json.load(f)

with open(RESULT_PATH) as f:
    results = json.load(f)

updates = 0
for r in results:
    name = r.get('name', '')
    bumn = r.get('bumn', '')
    for c in db['commissioners']:
        if c['name'] == name and c['bumn'] == bumn:
            c['political_affiliation'] = r.get('political_affiliation', '')
            c['party'] = r.get('party', '')
            c['status'] = r.get('status', 'belum_dianalisis')
            c['evidence'] = r.get('evidence', '')
            c['family_connections'] = r.get('family_connections', '')
            if 'legal_record' in r:
                c['legal_record'] = r['legal_record']
            updates += 1
            break

# Update version
status_counts = Counter(c.get('status','belum_dianalisis') for c in db['commissioners'])
db['version'] = '9.5'

with open(DB_PATH, 'w') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

# Embed into dashboard HTML
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

# Git commit + push
subprocess.run(['git', 'add', '-A'], cwd='/root/bumn-commissioner-scraper')
total_analyzed = len(db['commissioners']) - status_counts.get('belum_dianalisis', 0)
commit_msg = f"v9.5: Deep search batch — {updates} commissioners updated ({total_analyzed}/{len(db['commissioners'])} analyzed)\n\nStatus: {dict(status_counts)}"
subprocess.run(['git', 'commit', '-m', commit_msg], cwd='/root/bumn-commissioner-scraper')
subprocess.run(['git', 'push'], cwd='/root/bumn-commissioner-scraper')

# Update state file
STATE_PATH = '/root/bumn-commissioner-scraper/output/analysis_state.json'
if os.path.exists(STATE_PATH):
    with open(STATE_PATH) as f:
        state = json.load(f)
    for r in results:
        state['done'].append([r['name'], r['bumn']])
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

print(f"Updated {updates} commissioners")
print(f"Status: {dict(status_counts)}")
print(f"Dashboard embedded + pushed to git")
