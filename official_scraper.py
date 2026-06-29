#!/usr/bin/env python3
"""
Scrape commissioner lists from official BUMN websites — v2 with correct URLs.
"""
import httpx, re, json, sys

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

BUMN_URLS = {
    "MIND ID": ["https://mind.id/pages/board-of-commisioner"],
    "Pertamina": ["https://www2.pertamina.com/id/Dewan-Komisaris"],
    "PLN": ["https://web.pln.co.id/tentang-kami/dewan-komisaris"],
    "Telkom": ["https://www.telkom.co.id/sites/profil-telkom/id_ID/page/dewan-komisaris-197"],
    "BNI": [
        "https://www.bni.co.id/id-id/perseroan/tentang-bni/sekr-dewan-komisaris",
        "https://www.bni.co.id/id-id/perseroan/tata-kelola/dewan-komisaris",
    ],
    "BRI": [
        "https://bri.co.id/web/guest/komite-tata-kelola-terintegrasi",
        "https://bri.co.id/web/guest/dewan-komisaris",
        "https://bri.co.id/web/guest/about-bri/dewan-komisaris",
    ],
    "Bank Mandiri": [
        "https://www.bankmandiri.co.id/tentang-kami/dewan-komisaris.html",
        "https://www.bankmandiri.co.id/about-us/board-of-commissioners.html",
    ],
    "BSI": [
        "https://www.bankbsi.co.id/id/tentang-kami/dewan-komisaris",
        "https://www.bankbsi.co.id/id/about-us/board-of-commissioners",
    ],
    "BTN": [
        "https://www.btn.co.id/id/tentang-kami/profil/dewan-komisaris",
        "https://www.btn.co.id/en/about-us/company-profile/board-of-commissioners",
    ],
    "Garuda Indonesia": [
        "https://www.garuda-indonesia.com/id/id/company-profile/board-of-commissioners",
        "https://www.garuda-indonesia.com/id/id/about-us/dewan-komisaris",
    ],
    "KAI": [
        "https://kai.id/dewan-komisaris",
        "https://kai.id/tentang-kami/dewan-komisaris",
    ],
    "Pelindo": [
        "https://www.pelindo.co.id/id/tentang-kami/dewan-komisaris",
        "https://www.pelindo.co.id/en/about-us/board-of-commissioners",
    ],
    "Jasa Marga": [
        "https://www.jasamarga.com/id/korporat/tentang-jasa-marga/dewan-komisaris",
        "https://www.jasamarga.com/en/corporate/about-jasa-marga/board-of-commissioners",
    ],
    "Pupuk Indonesia": [
        "https://www.pupuk-indonesia.com/id/tentang-kami/dewan-komisaris",
        "https://www.pupuk-indonesia.com/en/about-us/board-of-commissioners",
    ],
    "Semen Indonesia": [
        "https://www.sig.id/id/tentang-kami/dewan-komisaris",
        "https://www.sig.id/en/about-us/board-of-commissioners",
    ],
    "Aneka Tambang (Antam)": [
        "https://www.antam.com/id/tentang-kami/dewan-komisaris",
        "https://www.antam.com/en/about-us/board-of-commissioners",
    ],
    "Bukit Asam (PTBA)": [
        "https://www.ptba.co.id/id/tentang-kami/dewan-komisaris",
        "https://www.ptba.co.id/en/about-us/board-of-commissioners",
    ],
    "Timah": [
        "https://www.timah.com/id/tentang-kami/dewan-komisaris",
        "https://www.timah.com/en/about-us/board-of-commissioners",
    ],
    "Inalum": [
        "https://www.inalum.id/id/tentang-kami/dewan-komisaris",
        "https://www.inalum.id/en/about-us/board-of-commissioners",
    ],
    "Wijaya Karya": [
        "https://www.wijayakarya.co.id/id/tentang-kami/dewan-komisaris",
        "https://www.wijayakarya.co.id/en/about-us/board-of-commissioners",
    ],
    "Adhi Karya": [
        "https://www.adhi.co.id/id/tentang-kami/dewan-komisaris",
        "https://www.adhi.co.id/en/about-us/board-of-commissioners",
    ],
    "Waskita Karya": [
        "https://www.waskita.co.id/id/tentang-kami/dewan-komisaris",
        "https://www.waskita.co.id/en/about-us/board-of-commissioners",
    ],
    "Hutama Karya": [
        "https://www.hutamakarya.com/id/tentang-kami/dewan-komisaris",
        "https://www.hutamakarya.com/en/about-us/board-of-commissioners",
    ],
    "Kimia Farma": [
        "https://www.kimiafarma.co.id/id/tentang-kami/dewan-komisaris",
        "https://www.kimiafarma.co.id/en/about-us/board-of-commissioners",
    ],
    "Bio Farma": [
        "https://www.biofarma.co.id/id/tentang-kami/dewan-komisaris",
        "https://www.biofarma.co.id/en/about-us/board-of-commissioners",
    ],
    "LEN Industri": [
        "https://www.len.co.id/id/tentang-kami/dewan-komisaris",
        "https://www.len.co.id/en/about-us/board-of-commissioners",
    ],
    "Pos Indonesia": [
        "https://www.posindonesia.co.id/id/tentang-kami/dewan-komisaris",
        "https://www.posindonesia.co.id/en/about-us/board-of-commissioners",
    ],
    "Krakatau Steel": [
        "https://www.krakatausteel.com/id/about-us/board-of-commissioners",
        "https://www.krakatausteel.com/id/tentang-kami/dewan-komisaris",
        "https://www.krakatausteel.com/management",
    ],
    "ID FOOD": [
        "https://www.idfood.co.id/id/tentang-kami/dewan-komisaris",
        "https://www.idfood.co.id/en/about-us/board-of-commissioners",
    ],
    "InJourney": [
        "https://www.injourney.com/id/tentang-kami/dewan-komisaris",
        "https://www.injourney.com/en/about-us/board-of-commissioners",
    ],
}

def clean_html(html):
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<noscript[^>]*>.*?</noscript>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', '\n', clean)
    clean = re.sub(r'&amp;', '&', clean)
    clean = re.sub(r'&nbsp;', ' ', clean)
    lines = [l.strip() for l in clean.split('\n') if l.strip() and len(l.strip()) > 2]
    return lines

def extract_commissioners_v2(lines):
    """Extract commissioner names and roles using multiple strategies."""
    commissioners = []
    
    # Strategy 1: Look for "Name" followed by "Komisaris [role]" pattern
    for i, line in enumerate(lines):
        if re.match(r'^(Komisaris\s+Utama|Wakil\s+Komisaris\s+Utama|Komisaris\s+Independen|Komisaris\s+Utama\s*/\s*Independen|Komisaris)$', line):
            # Name should be before this line
            for j in range(i-1, max(i-5, -1), -1):
                prev = lines[j]
                if (prev and len(prev) > 3 and len(prev) < 60 and 
                    prev[0].isupper() and 
                    not prev.startswith('PT') and not prev.startswith('http') and
                    not any(kw in prev.lower() for kw in ['komisaris', 'direksi', 'dewan', 'tentang', 'profil', 'lihat', 'hubungi', 'beranda', 'karir', 'berita', 'siaran', 'keberlanjutan', 'menu', 'search', 'close'])):
                    commissioners.append({"name": prev, "role": line})
                    break
    
    # Strategy 2: Look for "Name — Komisaris [role]" in single line
    for line in lines:
        m = re.match(r'^([A-Z][a-zA-Z\'\.\-\s]+?)\s+(?:—|–|-|:)\s+(Komisaris\s+Utama|Wakil\s+Komisaris\s+Utama|Komisaris\s+Independen|Komisaris\s+Utama\s*/\s*Independen|Komisaris)$', line)
        if m:
            commissioners.append({"name": m.group(1).strip(), "role": m.group(2)})
    
    # Strategy 3: Look for "Komisaris Utama: Name" or "Name Komisaris Utama" patterns
    for line in lines:
        m = re.match(r'^(?:Komisaris\s+Utama|Wakil\s+Komisaris\s+Utama|Komisaris\s+Independen|Komisaris)\s*[:\-]?\s*([A-Z][a-zA-Z\'\.\-\s]+)$', line)
        if m:
            name = m.group(1).strip()
            if len(name) > 3 and not name.startswith('PT'):
                role = re.match(r'^(Komisaris\s+Utama|Wakil\s+Komisaris\s+Utama|Komisaris\s+Independen|Komisaris)', line).group(1)
                commissioners.append({"name": name, "role": role})
    
    # Also extract from snippets (for SPA sites that return data in JS)
    # Pattern: "Name resmi diangkat menjadi Komisaris..."
    for line in lines:
        m = re.match(r'^([A-Z][a-zA-Z\'\.\-\s]+?)\s+(?:resmi\s+)?(?:diangkat\s+)?menjadi\s+(Komisaris\s+Utama|Wakil\s+Komisaris\s+Utama|Komisaris\s+Independen|Komisaris\s+Utama\s*/\s*Independen|Komisaris)', line)
        if m:
            name = m.group(1).strip()
            role = m.group(2) if m.group(2).startswith('Kom') else 'Komisaris'
            commissioners.append({"name": name, "role": role})
    
    # Deduplicate by name
    seen = set()
    unique = []
    for c in commissioners:
        key = c["name"].lower()
        if key not in seen and len(c["name"]) > 5:
            seen.add(key)
            unique.append(c)
    
    return unique

def scrape_bumn(name, urls):
    for url in urls:
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
            if resp.status_code == 200 and len(resp.text) > 500:
                lines = clean_html(resp.text)
                commissioners = extract_commissioners_v2(lines)
                if commissioners:
                    return {"bumn": name, "url": url, "commissioners": commissioners, "status": "ok", "html_len": len(resp.text)}
        except Exception as e:
            pass
    return {"bumn": name, "url": urls[0] if urls else "", "commissioners": [], "status": "failed"}

# Scrape all
results = []
for name, urls in BUMN_URLS.items():
    print(f"Scraping {name}...", end=" ", flush=True)
    result = scrape_bumn(name, urls)
    print(f"{result['status']} — {len(result['commissioners'])} commissioners")
    if result['commissioners']:
        for c in result['commissioners']:
            print(f"  {c['name']} — {c['role']}")
    results.append(result)

# Save
with open('/root/bumn-commissioner-scraper/output/official_scrape.json', 'w') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

total = sum(len(r['commissioners']) for r in results)
ok = sum(1 for r in results if r['status'] == 'ok')
print(f"\n=== SUMMARY ===")
print(f"Scraped: {ok}/{len(results)} BUMN")
print(f"Total commissioners: {total}")
