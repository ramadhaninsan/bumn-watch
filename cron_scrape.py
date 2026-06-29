#!/usr/bin/env python3
"""
Self-contained BUMN scraper — no LLM needed.
Uses Brave Search API directly, extracts commissioners, saves to DB, pushes to git.
Runs as cron script (no_agent=True).
"""
import json, os, sys, subprocess, re, time
import urllib.request, urllib.parse

# Config
DB_PATH = '/root/bumn-commissioner-scraper/output/bumn_database_v9.json'
STATE_PATH = '/root/bumn-commissioner-scraper/output/scrape_state.json'
DOCS_DIR = '/root/bumn-commissioner-scraper/docs'
REPO_DIR = '/root/bumn-commissioner-scraper'

# Load API key
# Load API key
API_KEY = ''
for env_file in ['/root/.hermes/.env', os.path.expanduser('~/.hermes/.env')]:
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith('OPENROUTER_API_KEY=') and '***' not in line:
                    API_KEY = line.strip().split('=', 1)[1]
                    break
        if API_KEY:
            break

if not API_KEY:
    API_KEY = os.environ.get('OPENROUTER_API_KEY', '')

if not API_KEY:
    print("ERROR: No API key found")
    sys.exit(1)

BATCH_SIZE = 3

BUMN_TO_SCRAPE = [
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
    {"name": "Perum Peruri", "query": "Peruri Percetakan Uang dewan komisaris dewan pengawas 2025 2026 site:peruri.co.id"},
    {"name": "BULOG", "query": "BULOG dewan pengawas komisaris 2025 2026 site:bulog.co.id"},
    {"name": "PTPN", "query": "PTPN Perkebunan Nusantara dewan komisaris 2025 2026 site:ptpn.co.id"},
    {"name": "Krakatau Steel", "query": "Krakatau Steel dewan komisaris 2025 2026 site:krakatausteel.com"},
    {"name": "ID FOOD", "query": "ID FOOD dewan komisaris 2025 2026 site:idfood.co.id"},
    {"name": "InJourney", "query": "InJourney dewan komisaris 2025 2026 site:injourney.com"},
    {"name": "Indosat", "query": "Indosat Ooredoo Hutchison dewan komisaris 2025 2026"},
    {"name": "BSI", "query": "Bank Syariah Indonesia BSI dewan komisaris 2025 2026 site:bankbsi.co.id"},
    {"name": "BTN", "query": "BTN Bank Tabungan Negara dewan komisaris 2025 2026 site:btn.co.id"},
    {"name": "Bank Mandiri", "query": "Bank Mandiri dewan komisaris 2025 2026 site:bankmandiri.co.id"},
    {"name": "BRI", "query": "BRI Bank Rakyat Indonesia dewan komisaris 2025 2026 site:bri.co.id"},
    {"name": "BNI", "query": "BNI Bank Negara Indonesia dewan komisaris 2025 2026 site:bni.co.id"},
]

def brave_search(query, count=5):
    """Search Brave API directly."""
    url = "https://api.search.brave.com/res/v1/web/search"
    params = urllib.parse.urlencode({
        "q": query,
        "count": count,
        "country": "ID",
        "search_lang": "id",
    })
    req = urllib.request.Request(f"{url}?{params}", headers={
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": API_KEY,
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            import gzip
            data = gzip.decompress(resp.read()) if resp.headers.get('Content-Encoding') == 'gzip' else resp.read()
            return json.loads(data)
    except Exception as e:
        print(f"  Search error: {e}")
        return None

def brave_llm_context(query, count=3):
    """Get LLM context from Brave."""
    url = "https://api.search.brave.com/res/v1/llm/context"
    params = urllib.parse.urlencode({
        "q": query,
        "count": count,
        "country": "ID",
    })
    req = urllib.request.Request(f"{url}?{params}", headers={
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": API_KEY,
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            import gzip
            data = gzip.decompress(resp.read()) if resp.headers.get('Content-Encoding') == 'gzip' else resp.read()
            return json.loads(data)
    except Exception as e:
        print(f"  LLM context error: {e}")
        return None

def extract_commissioners(search_result, llm_result):
    """Extract commissioner names and roles from search results."""
    commissioners = []
    
    # Combine all text from results
    texts = []
    
    if search_result and 'web' in (search_result.get('results') or {}):
        for r in search_result['results']['results'][:5]:
            texts.append(r.get('title', '') + ' ' + r.get('description', ''))
            for s in r.get('extra_snippets', []):
                texts.append(s)
    
    if llm_result:
        for g in llm_result.get('grounding', {}).get('generic', []):
            for s in g.get('snippets', []):
                texts.append(s)
    
    full_text = ' '.join(texts)
    
    # Pattern 1: "Name sebagai Komisaris Utama" or "Name — Komisaris Utama"
    patterns = [
        r'([A-Z][a-zA-Z\'\.\-\s]{4,50}?)\s+(?:sebagai|—|–|-|:)\s+(Wakil\s+)?(Komisaris\s+Utama(?:\s*/\s*Independen)?|Komisaris\s+Independen|Komisaris)',
        r'(?:Komisaris\s+Utama(?:\s*/\s*Independen)?|Komisaris\s+Independen|Komisaris)\s*[:\-]?\s*([A-Z][a-zA-Z\'\.\-\s]{4,50})',
        r'(\d+\.\s*[A-Z][a-zA-Z\'\.\-\s]{4,50}?)\s+(?:sebagai|—|–)\s+(Wakil\s+)?(Komisaris\s+Utama(?:\s*/\s*Independen)?|Komisaris\s+Independen|Komisaris)',
    ]
    
    for text in texts:
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if isinstance(m, tuple):
                    name = m[0].strip().strip('.')
                    role = m[-1].strip() if m[-1] else 'Komisaris'
                    if len(m) > 1 and m[1] and 'Wakil' in m[1]:
                        role = 'Wakil ' + role
                else:
                    name = m.strip().strip('.')
                    role = 'Komisaris'
                
                # Clean name
                name = re.sub(r'^\d+\.\s*', '', name).strip()
                name = re.sub(r'^(Bapak|Ibu|Sdr\.)\s+', '', name, flags=re.IGNORECASE).strip()
                
                # Validate
                if len(name) < 5 or name.startswith('PT ') or name.startswith('http') or 'komisaris' in name.lower():
                    continue
                if any(kw in name.lower() for kw in ['direktur', 'dewan', 'tentang', 'profil', 'beranda']):
                    continue
                
                commissioners.append({"name": name, "role": role})
    
    # Deduplicate
    seen = set()
    unique = []
    for c in commissioners:
        key = c["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    
    return unique

# Load state
if os.path.exists(STATE_PATH):
    with open(STATE_PATH) as f:
        state = json.load(f)
else:
    state = {"done": [], "batch_num": 0}

done_names = set(state['done'])
remaining = [b for b in BUMN_TO_SCRAPE if b['name'] not in done_names]

if not remaining:
    print("ALL DONE - all BUMN scraped")
    sys.exit(0)

batch = remaining[:BATCH_SIZE]
state['batch_num'] += 1

print(f"Batch {state['batch_num']}: {len(batch)} BUMN")
results = []

for bumn in batch:
    print(f"  Scraping {bumn['name']}...", end=" ", flush=True)
    search = brave_search(bumn['query'])
    llm = brave_llm_context(bumn['query'])
    commissioners = extract_commissioners(search, llm)
    print(f"{len(commissioners)} commissioners")
    for c in commissioners:
        print(f"    {c['name']} — {c['role']}")
    
    source_url = ''
    source_type = 'news_article'
    if search and 'web' in (search.get('results') or {}):
        results_list = search['results'].get('results', [])
        if results_list:
            source_url = results_list[0].get('url', '')
            hostname = ''
            try:
                from urllib.parse import urlparse
                hostname = urlparse(source_url).hostname
            except:
                pass
            if any(d in hostname for d in [bumn['name'].lower().split()[0], 'rups', 'official']):
                source_type = 'official_website'
    
    results.append({
        "bumn": bumn['name'],
        "source_url": source_url,
        "source_type": source_type,
        "scrape_date": "2026-06-29",
        "commissioners": commissioners
    })
    
    state['done'].append(bumn['name'])
    time.sleep(1)  # Rate limit

# Save state
with open(STATE_PATH, 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

# Merge into DB
with open(DB_PATH) as f:
    db = json.load(f)

added = 0
updated = 0
for r in results:
    for c in r['commissioners']:
        name = c['name'].strip()
        role = c['role']
        bumn = r['bumn']
        
        found = False
        for existing in db['commissioners']:
            if existing['name'].lower() == name.lower() and existing['bumn'].lower() == bumn.lower():
                if role and len(role) >= len(existing.get('role', '')):
                    existing['role'] = role
                existing['source_url'] = r['source_url']
                existing['source_type'] = r['source_type']
                existing['scrape_date'] = r['scrape_date']
                updated += 1
                found = True
                break
        
        if not found:
            db['commissioners'].append({
                'name': name, 'bumn': bumn, 'role': role, 'sector': '',
                'status': 'belum_dianalisis', 'party': '',
                'political_affiliation': '', 'evidence': '',
                'family_connections': '', 'legal_record': {},
                'photo_url': '', 'sources': [],
                'source_url': r['source_url'], 'source_type': r['source_type'],
                'scrape_date': r['scrape_date'],
                'is_rangkap_jabatan': False, 'is_tni_polri': False,
                'is_partai_kader': False, 'is_relawan_politik': False,
                'is_ormas': False, 'is_family_connection': False,
            })
            added += 1

db['version'] = '10.0'
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
bumn_count = len(set(c['bumn'] for c in db['commissioners']))
scraped_count = sum(1 for c in db['commissioners'] if c.get('scrape_date'))
msg = f"Scrape: {added} added, {updated} updated ({total} total, {bumn_count} BUMN, {scraped_count} verified) [{len(state['done'])}/26 done]"
subprocess.run(['git', 'commit', '-m', msg], cwd=REPO_DIR, capture_output=True)
subprocess.run(['git', 'push'], cwd=REPO_DIR, capture_output=True)

print(f"\nAdded: {added}, Updated: {updated}")
print(f"Total: {total} commissioners, {bumn_count} BUMN, {scraped_count} verified")
print(f"Progress: {len(state['done'])}/26 BUMN done")
print(msg)
