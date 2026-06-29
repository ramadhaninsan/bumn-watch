#!/usr/bin/env python3
"""
Schema migration: add new structured fields to all commissioners.
- Parse existing political_affiliation/evidence into boolean flags
- Add demografi, career, education, flags, sources fields
- Preserve all existing data
"""
import json, re, os

DB_PATH = '/root/bumn-commissioner-scraper/output/bumn_database_v9.json'

with open(DB_PATH) as f:
    db = json.load(f)

# Keywords for parsing political_affiliation → flags
PARTY_KEYWORDS = {
    'gerindra': 'Gerindra',
    'pdi-p': 'PDI-P', 'pdip': 'PDI-P', 'pdi perjuangan': 'PDI-P',
    'golkar': 'Golkar',
    'demokrat': 'Demokrat',
    'nasdem': 'Nasdem',
    'pkb': 'PKB',
    'pkS': 'PKS', 'pk s': 'PKS',
    'pan': 'PAN',
    'psi': 'PSI',
    'gelora': 'Gelora',
    'perindo': 'Perindo',
    'ppp': 'PPP',
    'hanura': 'Hanura',
}

RELAWAN_KEYWORDS = ['tkn', 'tim kampanye', 'relawan', 'tim sukses', 'samawi', 'pemenangan']
TNI_KEYWORDS = ['tni', 'purnawirawan', 'jenderal', 'letjen', 'mayjen', 'brigjen', 'marsdya', 'laksamana', 'kolonel', 'kapolda', 'kabaharkam', 'danpussenif', 'pangdam', 'kopassus', 'irjen tni']
POLRI_KEYWORDS = ['polri', 'komjen', 'inspektur jenderal polisi', 'kapolda', 'kapolri', 'baharkam', 'kakorlantas', 'perwira polri', 'irjen pol']
RANGKAP_KEYWORDS = ['wakil menteri', 'wamen', 'menteri', 'staf khusus', 'stafsus', 'kepala staf', 'sekretaris jenderal', 'sekjen', 'dirjen', 'direktur jenderal', 'kepala badan', 'wakil ketua pcO']
ORMAS_KEYWORDS = ['igmp', 'ppri', 'gp ansor', 'ansor', 'ormas', 'purnawirawan pejuang', 'muhammadiyah', 'nahdlatul ulama', 'nu ', 'pbnu']
FAMILY_KEYWORDS = ['putra', 'putri', 'anak', 'adik', 'kakak', 'keponakan', 'menantu', 'sepupu', 'kemenakan']

def parse_political_flags(comm):
    """Parse existing political_affiliation and evidence into structured flags."""
    text = (comm.get('political_affiliation', '') + ' ' + comm.get('evidence', '')).lower()
    party = comm.get('party', '').lower()
    
    # is_partai_kader
    is_partai = False
    detected_party = comm.get('party', '')
    if not detected_party or detected_party == 'Non-Partisan':
        for kw, pname in PARTY_KEYWORDS.items():
            if kw in text:
                detected_party = pname
                is_partai = True
                break
    else:
        if detected_party.lower() not in ['non-partisan', '', 'no party']:
            is_partai = True
    
    # is_relawan_politik
    is_relawan = any(kw in text for kw in RELAWAN_KEYWORDS)
    relawan_for = ''
    if 'prabowo' in text or 'tkn' in text:
        relawan_for = 'Prabowo-Gibran'
    elif 'jokowi' in text or 'samawi' in text:
        relawan_for = 'Jokowi'
    
    # is_tni_polri
    is_tni = any(kw in text for kw in TNI_KEYWORDS)
    is_polri = any(kw in text for kw in POLRI_KEYWORDS)
    
    # is_rangkap_jabatan
    is_rangkap = any(kw in text for kw in RANGKAP_KEYWORDS)
    
    # is_ormas
    is_ormas = any(kw in text for kw in ORMAS_KEYWORDS)
    
    # is_family_connection
    is_family = any(kw in text for kw in FAMILY_KEYWORDS)
    
    return {
        'is_rangkap_jabatan': is_rangkap,
        'is_tni_polri': is_tni or is_polri,
        'is_partai_kader': is_partai,
        'is_relawan_politik': is_relawan,
        'is_ormas': is_ormas,
        'is_family_connection': is_family,
        '_detected_party': detected_party if is_partai else '',
        '_relawan_for': relawan_for,
        '_is_tni': is_tni,
        '_is_polri': is_polri,
    }


# Migrate each commissioner
migrated = 0
for c in db['commissioners']:
    # Parse flags from existing data
    flags = parse_political_flags(c)
    
    # 1. Demografi (preserve existing, add missing)
    if 'birth_year' not in c:
        c['birth_year'] = None
    if 'birth_place' not in c:
        c['birth_place'] = ''
    if 'gender' not in c:
        # Try to detect from name
        c['gender'] = ''
    if 'age' not in c:
        c['age'] = None
    
    # 2. Flags Politik
    c['is_rangkap_jabatan'] = flags['is_rangkap_jabatan']
    c['rangkap_position'] = ''
    c['rangkap_legal_status'] = ''
    c['is_tni_polri'] = flags['is_tni_polri']
    c['military_rank'] = ''
    c['military_branch'] = ''  # TNI AD/AU/AL/Polri
    c['is_partai_kader'] = flags['is_partai_kader']
    if flags['_detected_party'] and (not c.get('party') or c.get('party') in ['', 'Non-Partisan']):
        c['party'] = flags['_detected_party']
    c['party_position'] = ''
    c['is_relawan_politik'] = flags['is_relawan_politik']
    c['relawan_for'] = flags['_relawan_for']
    c['tkn_role'] = ''
    c['is_ormas'] = flags['is_ormas']
    c['ormas_name'] = ''
    c['is_family_connection'] = flags['is_family_connection']
    c['family_detail'] = c.get('family_connections', '') if c.get('family_connections', '') != 'Tidak ditemukan' else ''
    c['family_type'] = ''
    
    # 3. Riwayat Pekerjaan (preserve existing 'career' field)
    if 'career' not in c:
        c['career'] = []
    c['career_history'] = c.get('career', [])
    c['career_relevance'] = ''  # relevant | not_relevant | partially_relevant
    
    # 4. Pendidikan
    if 'education' not in c:
        c['education'] = []
    c['education_history'] = c.get('education', [])
    
    # 5. Legal Record (enhance existing)
    if 'legal_record' not in c:
        c['legal_record'] = {}
    lr = c['legal_record']
    if 'has_kpk_case' not in lr:
        lr['has_kpk_case'] = lr.get('has_legal_issue', False) and 'kpk' in (lr.get('case_description', '') or '').lower()
    if 'has_court_case' not in lr:
        lr['has_court_case'] = lr.get('has_legal_issue', False)
    if 'mk_violation' not in lr:
        lr['mk_violation'] = flags['is_rangkap_jabatan']  # If rangkap, likely MK violation
    if 'legal_status' not in lr:
        lr['legal_status'] = lr.get('legal_status', 'cleared')
    
    # 6. Sources (preserve existing)
    if 'sources' not in c:
        c['sources'] = []
    if c.get('source_url') and c['source_url'] not in [s.get('url','') for s in c['sources'] if isinstance(s, dict)]:
        c['sources'].append({
            'url': c.get('source_url', ''),
            'source_type': c.get('source_type', ''),
            'date_accessed': c.get('scrape_date', '')
        })
    
    # 7. Wealth (preserve)
    if 'wealth' not in c:
        c['wealth'] = None
    if 'wealth_source' not in c:
        c['wealth_source'] = ''
    
    migrated += 1

# Update version
db['version'] = '10.0'

# Save
with open(DB_PATH, 'w') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

# Stats
from collections import Counter
flags_count = {
    'is_rangkap_jabatan': sum(1 for c in db['commissioners'] if c.get('is_rangkap_jabatan')),
    'is_tni_polri': sum(1 for c in db['commissioners'] if c.get('is_tni_polri')),
    'is_partai_kader': sum(1 for c in db['commissioners'] if c.get('is_partai_kader')),
    'is_relawan_politik': sum(1 for c in db['commissioners'] if c.get('is_relawan_politik')),
    'is_ormas': sum(1 for c in db['commissioners'] if c.get('is_ormas')),
    'is_family_connection': sum(1 for c in db['commissioners'] if c.get('is_family_connection')),
}

print(f"Migrated: {migrated} commissioners")
print(f"Version: {db['version']}")
print(f"\nFlags detected (from existing data):")
for k, v in flags_count.items():
    print(f"  {k}: {v}")

# Show party breakdown
party_counts = Counter(c.get('party','') for c in db['commissioners'] if c.get('is_partai_kader'))
print(f"\nParty breakdown (flagged as kader):")
for p, cnt in party_counts.most_common(15):
    print(f"  {p}: {cnt}")
