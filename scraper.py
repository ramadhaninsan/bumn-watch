#!/usr/bin/env python3
"""
BUMN Commissioner Scraper - POC
Scrapes Board of Commissioners (Dewan Komisaris) data from major Indonesian BUMN
using Wikipedia API + public web sources, then enriches with background/political affiliation data.

Output: JSON + CSV database of commissioners with their backgrounds.
"""

import requests
import json
import csv
import re
import time
from datetime import datetime
from pathlib import Path

# Wikipedia requires proper User-Agent
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "BUMN-Commissioner-Scraper/1.0 (research project; contact@research.org)",
    "Accept": "application/json",
})

# ============================================================
# BUMN LIST - POC (6 major BUMN for initial testing)
# ============================================================

BUMN_LIST = [
    {
        "name": "PT Pertamina (Persero)",
        "short_name": "Pertamina",
        "wikipedia_title": "Pertamina",
        "sector": "Energy / Oil & Gas",
        "ticker": "None (not listed)",
        "website": "https://www.pertamina.com",
    },
    {
        "name": "PT Telkom Indonesia (Persero) Tbk",
        "short_name": "Telkom",
        "wikipedia_title": "Telkom Indonesia",
        "sector": "Telecommunications",
        "ticker": "TLKM.JK",
        "website": "https://www.telkom.co.id",
    },
    {
        "name": "PT PLN (Persero)",
        "short_name": "PLN",
        "wikipedia_title": "PLN (company)",
        "sector": "Electricity / Power",
        "ticker": "None (not listed)",
        "website": "https://www.pln.co.id",
    },
    {
        "name": "PT Bank Mandiri (Persero) Tbk",
        "short_name": "Bank Mandiri",
        "wikipedia_title": "Bank Mandiri",
        "sector": "Banking",
        "ticker": "BMRI.JK",
        "website": "https://www.bankmandiri.co.id",
    },
    {
        "name": "PT Bank Rakyat Indonesia (Persero) Tbk",
        "short_name": "BRI",
        "wikipedia_title": "Bank Rakyat Indonesia",
        "sector": "Banking",
        "ticker": "BBRI.JK",
        "website": "https://www.bri.co.id",
    },
    {
        "name": "PT Garuda Indonesia (Persero) Tbk",
        "short_name": "Garuda",
        "wikipedia_title": "Garuda Indonesia",
        "sector": "Aviation",
        "ticker": "GIAA.JK",
        "website": "https://www.garuda-indonesia.com",
    },
    {
        "name": "PT Indosat Tbk",
        "short_name": "Indosat",
        "wikipedia_title": "Indosat",
        "sector": "Telecommunications",
        "ticker": "ISAT.JK",
        "website": "https://www.indosat.com",
    },
    ]

# Known controversial commissioners (from research) to seed the DB
# This will be merged with scraped data
KNOWN_POLITICAL_COMMISSIONERS = {
    "Telkom": [
        {
            "name": "Angga Raka Prabowo",
            "role": "President Commissioner (Komisaris Utama)",
            "political_affiliation": "Deputy Minister of Communication and Digital (Wamen Komdigital)",
            "background": "Appointed as President Commissioner of Telkom on 27 May 2025. Replaced Bambang Brodjonegoro who resigned April 2025.",
            "controversy": "Dual position: deputy minister + BUMN commissioner. Violates spirit of Constitutional Court Decision No. 80/PUU-XXII/2019 prohibiting dual positions for deputy ministers.",
            "source": "Kompas.id, 27 May 2025",
        },
        {
            "name": "Silmy Karim",
            "role": "Commissioner",
            "political_affiliation": "Deputy Minister of Immigration and Corrections (Wamen Imigrasi dan Pemasyarakatan)",
            "background": "Concurrently holds position as Commissioner at PT Telkom Indonesia.",
            "controversy": "Dual position: deputy minister + BUMN commissioner.",
            "source": "Kompas.id, June 2025",
        },
    ],
    "Telkomsel": [
        {
            "name": "Diaz FM Hendropriyono",
            "role": "President Commissioner (Komisaris Utama)",
            "political_affiliation": "Deputy Minister of Environment (Wamen Lingkungan Hidup)",
            "background": "Appointed as President Commissioner of PT Telkomsel on 28 May 2025.",
            "controversy": "Dual position: deputy minister + BUMN commissioner at Telkom subsidiary.",
            "source": "Kompas.id, 28 May 2025",
        },
    ],
    "Indosat": [
        {
            "name": "Nezar Patria",
            "role": "President Commissioner (Komisaris Utama)",
            "political_affiliation": "Deputy Minister of Communication and Digital (Wamen Komdigital)",
            "background": "Appointed as President Commissioner of PT Indosat Tbk.",
            "controversy": "Dual position: deputy minister + BUMN commissioner.",
            "source": "Kompas.id, May 2025",
        },
    ],
    "PLN": [
        {
            "name": "Suahasil Nazara",
            "role": "Vice President Commissioner (Wakil Komisaris Utama)",
            "political_affiliation": "Deputy Minister of Finance (Wamen Keuangan)",
            "background": "Serves as Vice President Commissioner of PT PLN (Persero).",
            "controversy": "Dual position: deputy minister of finance + BUMN commissioner at PLN.",
            "source": "Kompas.id, June 2025",
        },
    ],
    "Bulog": [
        {
            "name": "Sudaryono",
            "role": "Chairman of Supervisory Board (Ketua Dewan Pengawas)",
            "political_affiliation": "Deputy Minister of Agriculture (Wamen Pertanian)",
            "background": "Concurrently serves as Chairman of Supervisory Board of Perum Bulog.",
            "controversy": "Dual position: deputy minister + BUMN supervisory board.",
            "source": "Kompas.id, March 2025",
        },
    ],
}

# ============================================================
# WIKIPEDIA API - Fetch company + person pages
# ============================================================

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_API_ID = "https://id.wikipedia.org/w/api.php"

def wiki_get_page(title, lang="en"):
    """Fetch Wikipedia article content as plain text via API."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "explaintext": "1",
        "format": "json",
    }
    url = WIKI_API if lang == "en" else WIKI_API_ID
    try:
        r = SESSION.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for pid, page in pages.items():
            if pid == "-1":
                return None
            return page.get("extract", "")
        return None
    except Exception as e:
        print(f"  [WARN] Wikipedia fetch failed for '{title}' ({lang}): {e}")
        return None

def wiki_get_html(title, lang="en"):
    """Fetch Wikipedia article HTML via REST API (for infobox parsing)."""
    title_url = title.replace(" ", "_")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/html/{title_url}"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  [WARN] Wikipedia REST fetch failed for '{title}' ({lang}): {e}")
        return None

def wiki_search(query, lang="en", limit=5):
    """Search Wikipedia for article titles."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
    }
    url = WIKI_API if lang == "en" else WIKI_API_ID
    try:
        r = SESSION.get(url, params=params, timeout=15)
        r.raise_for_status()
        results = r.json().get("query", {}).get("search", [])
        return [(item["title"], item["snippet"]) for item in results]
    except Exception as e:
        print(f"  [WARN] Wiki search failed: {e}")
        return []

def parse_commissioners_from_text(text):
    """Extract commissioner/director names from Wikipedia plain text extract."""
    if not text:
        return []

    commissioners = []
    
    # Find sections about commissioners/governance
    lines = text.split("\n")
    in_section = False
    section_keywords = [
        "commissioner", "board of commission", "dewan komisaris",
        "board of director", "direksi", "governance", "management",
        "key people", "key personnel", "leadership",
    ]
    
    for i, line in enumerate(lines):
        line_lower = line.strip().lower()
        if any(kw in line_lower for kw in section_keywords):
            in_section = True
            continue
        if in_section:
            if line.strip() == "" or line.startswith("="):
                in_section = False
                continue
            line = line.strip()
            if len(line) > 3 and not line.startswith("=="):
                # Clean up
                line = re.sub(r"\s+", " ", line)
                commissioners.append(line)
    
    # Also look for patterns like "Name (role)" or bullet-point lists
    # in the governance section
    return commissioners

def parse_commissioners_from_html(html):
    """Extract commissioner names from Wikipedia HTML infobox."""
    if not html:
        return []
    
    commissioners = []
    
    try:
        from html.parser import HTMLParser
        from html import unescape
        
        class InfoboxParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_infobox = False
                self.in_th = False
                self.in_td = False
                self.current_key = ""
                self.current_val = ""
                self.capture = False
                self.commissioner_text = ""
                
            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                cls = attrs_dict.get("class", "")
                if tag == "table" and "infobox" in cls:
                    self.in_infobox = True
                elif self.in_infobox:
                    if tag == "th":
                        self.in_th = True
                        self.current_key = ""
                    elif tag == "td":
                        self.in_td = True
                        self.current_val = ""
                    elif tag == "br" and self.in_td:
                        self.current_val += "\n"
                        
            def handle_endtag(self, tag):
                if tag == "table" and self.in_infobox:
                    self.in_infobox = False
                elif self.in_infobox:
                    if tag == "th":
                        self.in_th = False
                        if any(kw in self.current_key.lower() for kw in 
                               ["commissioner", "key people", "board of", "dewan komisaris", "direksi"]):
                            self.capture = True
                    elif tag == "td":
                        self.in_td = False
                        if self.capture:
                            self.commissioner_text += self.current_val + "\n"
                            self.capture = False
                        
            def handle_data(self, data):
                if self.in_th:
                    self.current_key += data
                elif self.in_td:
                    self.current_val += data
        
        parser = InfoboxParser()
        parser.feed(html)
        if parser.commissioner_text:
            lines = parser.commissioner_text.strip().split("\n")
            for line in lines:
                line = line.strip()
                line = unescape(line)
                line = re.sub(r"\s+", " ", line)
                if line and len(line) > 3:
                    commissioners.append(line)
    except Exception as e:
        print(f"  [WARN] HTML parsing error: {e}")
    
    return commissioners

def get_person_background(name, lang="en"):
    """Search Wikipedia for person's background and extract summary."""
    for l in [lang, "id" if lang != "id" else "en"]:
        search_results = wiki_search(name, lang=l, limit=3)
        for title, snippet in search_results:
            # Skip obvious non-person articles (companies, places)
            title_lower = title.lower()
            if any(skip in title_lower for skip in ["company", "corporation", "persero", "bank", "pt ", "agency", "ministry"]):
                continue
            # Fetch the extract
            text = wiki_get_page(title, lang=l)
            if text:
                # Get first meaningful paragraph
                paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) > 50]
                if paragraphs:
                    return {
                        "wikipedia_title": title,
                        "summary": paragraphs[0][:500],
                        "lang": l,
                    }
    return None

# ============================================================
# MAIN SCRAPE LOGIC
# ============================================================

def scrape_bumn(bumn):
    """Scrape commissioner data for a single BUMN."""
    print(f"\n{'='*60}")
    print(f"Scraping: {bumn['name']}")
    print(f"{'='*60}")
    
    result = {
        "bumn_name": bumn["name"],
        "short_name": bumn["short_name"],
        "sector": bumn["sector"],
        "ticker": bumn["ticker"],
        "website": bumn["website"],
        "scrape_date": datetime.now().isoformat(),
        "commissioners": [],
        "sources": [],
    }
    
    # 1. Fetch Wikipedia article
    print(f"  [1/3] Fetching Wikipedia: '{bumn['wikipedia_title']}'")
    text_en = wiki_get_page(bumn["wikipedia_title"], lang="en")
    text_id = wiki_get_page(bumn["wikipedia_title"], lang="id")
    html_en = wiki_get_html(bumn["wikipedia_title"], lang="en")
    html_id = wiki_get_html(bumn["wikipedia_title"], lang="id")
    
    wiki_commissioners = []
    if text_en:
        wiki_commissioners.extend(parse_commissioners_from_text(text_en))
        result["sources"].append(f"Wikipedia EN (text): {bumn['wikipedia_title']}")
    if text_id:
        wiki_commissioners.extend(parse_commissioners_from_text(text_id))
        result["sources"].append(f"Wikipedia ID (text): {bumn['wikipedia_title']}")
    if html_en:
        html_comms = parse_commissioners_from_html(html_en)
        wiki_commissioners.extend(html_comms)
        result["sources"].append(f"Wikipedia EN (HTML infobox): {bumn['wikipedia_title']}")
    if html_id:
        html_comms = parse_commissioners_from_html(html_id)
        wiki_commissioners.extend(html_comms)
        result["sources"].append(f"Wikipedia ID (HTML infobox): {bumn['wikipedia_title']}")
    
    # Deduplicate
    seen = set()
    unique_commissioners = []
    for c in wiki_commissioners:
        c_clean = c.strip().lower()
        if c_clean not in seen and len(c_clean) > 3:
            seen.add(c_clean)
            unique_commissioners.append(c.strip())
    
    print(f"  [2/3] Found {len(unique_commissioners)} potential commissioner entries from Wikipedia")
    
    # 3. Enrich each commissioner with background info
    for comm_name in unique_commissioners[:20]:  # Limit to 20 for POC
        print(f"    -> Looking up: {comm_name}")
        background = get_person_background(comm_name)
        
        commissioner_entry = {
            "name": comm_name,
            "role": "Commissioner (specific role TBD - requires manual verification)",
            "background": background["summary"] if background else "No Wikipedia article found. Manual research needed.",
            "political_affiliation": "TBD - requires cross-reference with news sources",
            "controversy": "TBD - requires cross-reference with TI Indonesia / ICW data",
            "source": background["wikipedia_title"] if background else "Wikipedia (not found)",
        }
        result["commissioners"].append(commissioner_entry)
        time.sleep(0.5)  # Be polite to Wikipedia API
    
    # 2. Merge with known political commissioners from research
    known = KNOWN_POLITICAL_COMMISSIONERS.get(bumn["short_name"], [])
    if known:
        print(f"  [2.5] Merging {len(known)} known political commissioners from research data")
        for k in known:
            # Check if already exists
            exists = any(k["name"].lower() in c["name"].lower() for c in result["commissioners"])
            if not exists:
                result["commissioners"].append(k)
            else:
                # Update existing entry with known info
                for c in result["commissioners"]:
                    if k["name"].lower() in c["name"].lower():
                        c["role"] = k["role"]
                        c["political_affiliation"] = k["political_affiliation"]
                        c["background"] = k["background"]
                        c["controversy"] = k["controversy"]
                        c["source"] = k["source"]
    
    print(f"  [3/3] Total commissioners recorded: {len(result['commissioners'])}")
    return result

# ============================================================
# OUTPUT - JSON + CSV
# ============================================================

def save_results(results, output_dir):
    """Save results as JSON and CSV."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSON
    json_path = output_dir / "bumn_commissioners.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nJSON saved: {json_path}")
    
    # CSV (flat table: one row per commissioner)
    csv_path = output_dir / "bumn_commissioners.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "bumn_name", "short_name", "sector", "commissioner_name", 
            "role", "political_affiliation", "background", "controversy", "source"
        ])
        writer.writeheader()
        for bumn in results:
            for comm in bumn["commissioners"]:
                writer.writerow({
                    "bumn_name": bumn["bumn_name"],
                    "short_name": bumn["short_name"],
                    "sector": bumn["sector"],
                    "commissioner_name": comm["name"],
                    "role": comm["role"],
                    "political_affiliation": comm.get("political_affiliation", ""),
                    "background": comm.get("background", ""),
                    "controversy": comm.get("controversy", ""),
                    "source": comm.get("source", ""),
                })
    print(f"CSV saved: {csv_path}")
    
    # Summary report
    report_path = output_dir / "summary_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("BUMN COMMISSIONER DATABASE - POC SUMMARY\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"{'='*60}\n\n")
        total_comm = sum(len(b["commissioners"]) for b in results)
        total_political = 0
        for b in results:
            f.write(f"BUMN: {b['bumn_name']}\n")
            f.write(f"Sector: {b['sector']}\n")
            f.write(f"Commissioners found: {len(b['commissioners'])}\n")
            for c in b["commissioners"]:
                pol = c.get("political_affiliation", "")
                if pol and pol != "TBD - requires cross-reference with news sources":
                    total_political += 1
                f.write(f"  - {c['name']} | Role: {c.get('role','?')}\n")
                if pol and "TBD" not in pol:
                    f.write(f"    POLITICAL: {pol}\n")
                controv = c.get("controversy", "")
                if controv and "TBD" not in controv:
                    f.write(f"    CONTROVERSY: {controv}\n")
            f.write("\n")
        f.write(f"{'='*60}\n")
        f.write(f"TOTAL BUMN scraped: {len(results)}\n")
        f.write(f"TOTAL commissioners: {total_comm}\n")
        f.write(f"TOTAL with political background: {total_political}\n")
    print(f"Summary saved: {report_path}")

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("BUMN COMMISSIONER SCRAPER - POC")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    results = []
    for bumn in BUMN_LIST:
        try:
            result = scrape_bumn(bumn)
            results.append(result)
            time.sleep(1)  # Be polite
        except Exception as e:
            print(f"  [ERROR] Failed to scrape {bumn['name']}: {e}")
            results.append({
                "bumn_name": bumn["name"],
                "short_name": bumn["short_name"],
                "sector": bumn["sector"],
                "commissioners": [],
                "error": str(e),
            })
    
    # Save outputs
    output_dir = "/root/bumn-commissioner-scraper/output"
    save_results(results, output_dir)
    
    print(f"\n{'='*60}")
    print(f"DONE - {datetime.now().isoformat()}")
    print(f"{'='*60}")
    print(f"\nNext steps for full version:")
    print("1. Add all ~65 BUMN from Wikipedia list")
    print("2. Integrate with TI Indonesia / ICW corruption data")
    print("3. Add BUMD (regional) commissioners")
    print("4. Auto-detect political affiliation via news scraping")
    print("5. Build SQLite database with full-text search")
    print("6. Add annual report PDF scraping for official commissioner lists")

if __name__ == "__main__":
    main()
