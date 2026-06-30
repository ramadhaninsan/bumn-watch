#!/usr/bin/env python3
"""Save enrich results to DB + output JSON + git push."""
import json, os, sys, subprocess
from collections import Counter

DB_PATH = '/root/bumn-commissioner-scraper/output/bumn_database_v9.json'
RESULT_PATH = '/tmp/enrich_result.json'
STATE_PATH = '/root/bumn-commissioner-scraper/output/enrich_state.json'
DOCS_DIR = '/root/bumn-commissioner-scraper/docs'
REPO_DIR = '/root/bumn-commissioner-scraper'

if not os.path.exists(RESULT_PATH):
    print("No result file")
    sys.exit(1)

with open(DB_PATH) as f:
    db = json.load(f)
with open(RESULT_PATH) as f:
    results = json.load(f)

updated = 0
for r in results:
    name = r.get('name', '')
    bumn = r.get('bumn', '')
    for c in db['commissioners']:
        if c['name'].lower() == name.lower() and c['bumn'].lower() == bumn.lower():
            c['status'] = r.get('status', 'profesional')
            c['party'] = r.get('party', '')
            c['political_affiliation'] = r.get('political_affiliation', '')
            c['evidence'] = r.get('evidence', '')
            c['family_connections'] = r.get('family_connections', '')
            c['is_rangkap_jabatan'] = r.get('is_rangkap_jabatan', False)
            c['rangkap_position'] = r.get('rangkap_position', '')
            c['is_tni_polri'] = r.get('is_tni_polri', False)
            c['military_rank'] = r.get('military_rank', '')
            c['military_branch'] = r.get('military_branch', '')
            c['is_partai_kader'] = r.get('is_partai_kader', False)
            c['party_position'] = r.get('party_position', '')
            c['is_relawan_politik'] = r.get('is_relawan_politik', False)
            c['relawan_for'] = r.get('relawan_for', '')
            c['tkn_role'] = r.get('tkn_role', '')
            c['is_ormas'] = r.get('is_ormas', False)
            c['ormas_name'] = r.get('ormas_name', '')
            c['is_family_connection'] = r.get('is_family_connection', False)
            c['family_detail'] = r.get('family_detail', '')
            c['family_type'] = r.get('family_type', '')
            if 'legal_record' in r:
                c['legal_record'] = r['legal_record']
            if 'career_history' in r:
                c['career_history'] = r['career_history']
            if 'education_history' in r:
                c['education_history'] = r['education_history']
            if 'sources' in r and r['sources']:
                existing_urls = {s.get('url') for s in c.get('sources', []) if isinstance(s, dict)}
                for s in r['sources']:
                    if isinstance(s, dict) and s.get('url') not in existing_urls:
                        c.setdefault('sources', []).append(s)
            updated += 1
            break

# Update state
if os.path.exists(STATE_PATH):
    with open(STATE_PATH) as f:
        state = json.load(f)
else:
    state = {"done": [], "batch_num": 0}
for r in results:
    state['done'].append([r.get('name',''), r.get('bumn','')])
with open(STATE_PATH, 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

status = Counter(c.get('status','belum_dianalisis') for c in db['commissioners'])
with open(DB_PATH, 'w') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

# Output JSON files
with open(os.path.join(DOCS_DIR, 'data.json'), 'w') as f:
    json.dump(db['commissioners'], f, ensure_ascii=False)
with open(os.path.join(DOCS_DIR, 'bumn.json'), 'w') as f:
    json.dump(db.get('master_bumn', []), f, ensure_ascii=False)
with open(os.path.join(DOCS_DIR, 'bumd.json'), 'w') as f:
    json.dump(db.get('master_bumd', []), f, ensure_ascii=False)

# Git push
subprocess.run(['git', 'add', '-A'], cwd=REPO_DIR, capture_output=True)
total = len(db['commissioners'])
analyzed = total - status.get('belum_dianalisis', 0)
msg = f"Enrich batch: {updated} updated ({analyzed}/{total} analyzed, {dict(status)})"
subprocess.run(['git', 'commit', '-m', msg], cwd=REPO_DIR, capture_output=True)
subprocess.run(['git', 'push'], cwd=REPO_DIR, capture_output=True)

print(f"Updated: {updated}")
print(f"Status: {dict(status)}")
print(f"Analyzed: {analyzed}/{total}")
print("JSON updated + pushed")
