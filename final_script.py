#!/usr/bin/env python3
"""
BUMN Commissioner Scraper — Webwright Edition
Uses Playwright (Firefox headless) to scrape JS-rendered BUMN official websites.

Usage:
  python3 final_script.py                          # scrape all BUMN
  python3 final_script.py --bumn telkom,pln        # scrape specific BUMN
  python3 final_script.py --output ./output         # custom output dir

Args:
  --bumn: Comma-separated BUMN short names to scrape (default: all)
  --output: Output directory for JSON/CSV (default: output/)
  --headless: Run browser headless (default: true)
"""

import argparse
import asyncio
import json
import csv
import re
import os
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# ============================================================
# BUMN CONFIG — official commissioner page URLs
# ============================================================

BUMN_CONFIG = {
    "telkom": {
        "name": "PT Telkom Indonesia (Persero) Tbk",
        "short_name": "Telkom",
        "sector": "Telecommunications",
        "ticker": "TLKM.JK",
        "urls": [
            "https://www.telkom.co.id/sites/about-telkom/id_ID/page/dewan-komisaris-197",
            "https://www.telkom.co.id/sites/about-us/en_US/page/board-of-commisioner-199",
        ],
    },
    "pertamina": {
        "name": "PT Pertamina (Persero)",
        "short_name": "Pertamina",
        "sector": "Energy / Oil & Gas",
        "ticker": "None",
        "urls": [
            "https://www.pertamina.com/id/dewan-komisaris",
            "https://www.pertamina.com/en/board-of-commissioners",
        ],
    },
    "pln": {
        "name": "PT PLN (Persero)",
        "short_name": "PLN",
        "sector": "Electricity / Power",
        "ticker": "None",
        "urls": [
            "https://web.pln.co.id/tentang-kami/dewan-komisaris",
            "https://web.pln.co.id/en/about-us/board-of-commissioners",
        ],
    },
    "mandiri": {
        "name": "PT Bank Mandiri (Persero) Tbk",
        "short_name": "Bank Mandiri",
        "sector": "Banking",
        "ticker": "BMRI.JK",
        "urls": [
            "https://www.bankmandiri.co.id/dewan-komisaris-direksi",
            "https://www.bankmandiri.co.id/en/dewan-komisaris-direksi",
        ],
    },
    "bri": {
        "name": "PT Bank Rakyat Indonesia (Persero) Tbk",
        "short_name": "BRI",
        "sector": "Banking",
        "ticker": "BBRI.JK",
        "urls": [
            "https://bri.co.id/web/guest/dewan-komisaris-direksi",
            "https://bri.co.id/web/guest/board-of-commissioners-and-directors",
        ],
    },
    "garuda": {
        "name": "PT Garuda Indonesia (Persero) Tbk",
        "short_name": "Garuda",
        "sector": "Aviation",
        "ticker": "GIAA.JK",
        "urls": [
            "https://www.garuda-indonesia.com/id/id/corporate-social-responsibility/governance/dewan-komisaris",
        ],
    },
    "indosat": {
        "name": "PT Indosat Tbk",
        "short_name": "Indosat",
        "sector": "Telecommunications",
        "ticker": "ISAT.JK",
        "urls": [
            "https://www.indosat.com/about-indosat/corporate-profile/board-of-directors-chief",
        ],
    },
}

# Known political affiliations — keywords to flag
POLITICAL_KEYWORDS = [
    "wakil menteri", "wamen", "menteri", "kementerian", "dpr", "anggota dpr",
    "komisi dpr", "partai", "politisi", "politisi", "pemilu", "presiden",
    "wakil presiden", "gubernur", "bupati", "walikota", "sekretaris kementerian",
    "staf khusus menteri", "staf presiden", "tenaga ahli dpr", "ketua dpr",
    "pasprossobo", "pasukan pro prabowo", "relawan prabowo", "kader partai",
    "deputy minister", "minister of", "member of parliament", "political",
    "secretary of ministry", "secretary of the ministry",
]

# Manually researched commissioner data (from Brave LLM Context + official websites + news)
# Used as fallback when Playwright can't reach the site, and as enrichment
RESEARCHED_DATA = {
    "telkom": [
        {"name": "Angga Raka Prabowo", "role": "Komisaris Utama", "background": "Wakil Menteri Komunikasi dan Digital (Wamen Komdigital). Diangkat sebagai Komisaris Utama Telkom pada RUPST 27 Mei 2025, menggantikan Bambang Brodjonegoro.", "source": "Kompas, Telkom.co.id"},
        {"name": "Ossy Dermawan", "role": "Komisaris", "background": "", "source": "Kompas RUPST 2025"},
        {"name": "Ismail", "role": "Komisaris", "background": "", "source": "Kompas RUPST 2025"},
        {"name": "Rionald Silaban", "role": "Komisaris", "background": "", "source": "Kompas RUPST 2025"},
        {"name": "Silmy Karim", "role": "Komisaris", "background": "Wakil Menteri Imigrasi dan Pemasyarakatan. Merangkap jabatan sebagai Komisaris Telkom.", "source": "Kompas"},
        {"name": "Yohanes Surya", "role": "Komisaris Independen", "background": "", "source": "Kompas RUPST 2025"},
        {"name": "Deswandhy Agusman", "role": "Komisaris Independen", "background": "Pengalaman di bidang finance dan capital markets. Mantan Independent Commissioner Berau Coal Energy, Maybank Sekuritas Indonesia.", "source": "Telkom.co.id"},
        {"name": "Rizal Mallarangeng", "role": "Komisaris Independen", "background": "S1 Ilmu Komunikasi UGM 1990, S2/S3 Comparative Politics Ohio State University. Ketua Yayasan Prabowo Subianto Djojohadikusumo (since 2022).", "source": "Telkom.co.id"},
    ],
    "pertamina": [
        {"name": "Mochamad Iriawan", "role": "Komisaris Utama & Komisaris Independen", "background": "Komisaris Jenderal Polisi (Purn.) Dr. Drs. H. Mochamad Iriawan, S.H., M.M., M.H. Lahir di Jakarta 31 Maret 1962. Lulusan Akademi Kepolisian 1984. Mantan Sekretaris Lembaga Ketahanan Nasional (2018). Diangkat berdasarkan SK-258/MBU/11/2024 pada 4 November 2024.", "source": "Pertamina.com"},
        {"name": "Dony Oskaria", "role": "Wakil Komisaris Utama", "background": "S.IP., M.B.A.", "source": "Pertamina.com"},
        {"name": "Bambang Suswantono", "role": "Komisaris", "background": "Letjen TNI (Mar) (Purn) Bambang Suswantono, S.H., M.H., M.Tr. (Han)", "source": "Pertamina.com"},
        {"name": "Condro Kirono", "role": "Komisaris Independen", "background": "Komisaris Jenderal Polisi (Purn.) Drs. Condro Kirono, M.M., M.Hum.", "source": "Pertamina.com"},
        {"name": "Sondaryani", "role": "Komisaris Independen", "background": "S.T. Lulusan Teknik Perminyakan Universitas Trisakti 1987. Country Manager Downhole Technologies NOV Inc. Komisaris Independen Pertamina 2016-2024.", "source": "Pertamina.com"},
        {"name": "Iggi H. Achsien", "role": "Komisaris Independen", "background": "Lahir di Indramayu 1977. Diangkat berdasarkan SK-222/MBU/07/2021 pada 2 Juli 2021.", "source": "Pertamina.com"},
        {"name": "Alexander Lay", "role": "Komisaris Independen", "background": "Pria kelahiran Ende, Flores 1973. Mantan Dewan Pengawas Transparency International Indonesia. Advokat hukum persaingan usaha.", "source": "Pertamina.com"},
    ],
    "pln": [
        {"name": "Burhanuddin Abdullah", "role": "President Commissioner & Independent Commissioner", "background": "", "source": "PLN official website"},
        {"name": "Suahasil Nazara", "role": "Vice President Commissioner", "background": "Wakil Menteri Keuangan (Wamen Keuangan). Merangkap sebagai Wakil Komisaris Utama PLN.", "source": "PLN official, Kompas"},
        {"name": "Aminuddin Ma'ruf", "role": "Commissioner", "background": "", "source": "PLN official website"},
        {"name": "Dadan Kusdiana", "role": "Commissioner", "background": "", "source": "PLN official website"},
        {"name": "Jisman Parada Hutajulu", "role": "Commissioner", "background": "", "source": "PLN official website"},
        {"name": "Bambang Eko Suhariyanto", "role": "Commissioner", "background": "", "source": "PLN official website"},
        {"name": "Yazid Fanani", "role": "Independent Commissioner", "background": "", "source": "PLN official website"},
        {"name": "Mutanto Juwono", "role": "Independent Commissioner", "background": "", "source": "PLN official website"},
        {"name": "Andi Arief", "role": "Independent Commissioner", "background": "", "source": "PLN official website"},
    ],
    "mandiri": [
        {"name": "Zulkifli Zaini", "role": "Komisaris Utama/Independen", "background": "Lahir Palembang 1956. S1 Teknik Sipil ITB, MBA University of Washington. Mantan Direktur Utama Bank Mandiri (2010-2013). Mantan Dirut PLN (2019-2021). Komisaris Utama PTPN III (2021-2025). Diangkat sebagai Komut Mandiri RUPSLB 19 Des 2025, menggantikan Kuswiyoto.", "source": "Bankmandiri.co.id, Infobanknews"},
        {"name": "M. Rudy Salahuddin Ramto", "role": "Wakil Komisaris Utama", "background": "Sekretaris Kementerian Investasi dan Hilirisasi / Sekretaris Utama BKPM. S1 Teknik Sipil UI, S2/S3 Engineering Management George Washington University. Komisaris PT Aneka Tambang, PT Jasa Raharja, Perum PERURI, PT PLN.", "source": "Bankmandiri.co.id, Infobanknews"},
        {"name": "B. Bintoro Kunto Pardewo", "role": "Komisaris Independen", "background": "Lahir Bandung 1970. PhD Economics University of Colorado. Executive Analyst & Deputi Direktur Bank Indonesia. Komisaris PT Danareksa. S1 Teknik Mesin UI, MBA Iowa State University.", "source": "Bankmandiri.co.id, Infobanknews"},
        {"name": "Luky Alfirman", "role": "Komisaris", "background": "Direktur Jenderal Perimbangan Keuangan, Kementerian Keuangan RI. Dewan Komisaris Lembaga Penjamin Simpanan.", "source": "Bankmandiri.co.id"},
        {"name": "Yuliot", "role": "Komisaris", "background": "", "source": "Bankmandiri.co.id"},
        {"name": "Mia Amiati", "role": "Komisaris Independen", "background": "", "source": "Bankmandiri.co.id"},
    ],
    "bri": [
        {"name": "Kartika Wirjoatmodjo", "role": "Komisaris Utama", "background": "Tetap sebagai Komut BRI pada RUPST 2025.", "source": "Investortrust, BRI annual report"},
        {"name": "Parman Nataatmadja", "role": "Wakil Komisaris Utama/Komisaris Independen", "background": "", "source": "Investortrust"},
        {"name": "Awan Nurmawan Nuh", "role": "Komisaris", "background": "", "source": "Investortrust"},
        {"name": "Helvi Yuni Moraza", "role": "Komisaris", "background": "", "source": "Investortrust"},
        {"name": "Edi Susianto", "role": "Komisaris Independen", "background": "", "source": "Investortrust"},
        {"name": "Lukmanul Khakim", "role": "Komisaris Independen", "background": "", "source": "Investortrust"},
    ],
    "garuda": [
        {"name": "Unknown", "role": "Unknown", "background": "Garuda website blocked (403). Data requires manual lookup from annual report.", "source": ""},
    ],
    "indosat": [
        {"name": "Nezar Patria", "role": "Komisaris Utama (President Commissioner)", "background": "Wakil Menteri Komunikasi dan Digital (Wamen Komdigital). Diangkat sebagai President Commissioner PT Indosat Tbk.", "source": "Kompas, May 2025"},
    ],
}


def merge_researched_data(scraped_commissioners: list, bumn_key: str) -> list:
    """Merge scraped commissioners with manually researched data."""
    researched = RESEARCHED_DATA.get(bumn_key, [])
    if not researched:
        return scraped_commissioners

    # Create a lookup of scraped names (lowercase, first 20 chars)
    scraped_lookup = {}
    for c in scraped_commissioners:
        key = c["name"].lower()[:20]
        scraped_lookup[key] = c

    merged = list(scraped_commissioners)

    for r in researched:
        r_key = r["name"].lower()[:20]
        if r_key in scraped_lookup:
            # Enrich existing entry
            existing = scraped_lookup[r_key]
            if r.get("background") and not existing.get("background"):
                existing["background"] = r["background"]
            if r.get("role") and r["role"] != "commissioner" and r["role"] != "komisaris":
                existing["role"] = r["role"]
            existing["source"] = r.get("source", "")
        else:
            # Add new entry from research
            political = detect_political(r.get("background", "") + " " + r["name"], r["name"])
            merged.append({
                "name": r["name"],
                "role": r.get("role", "Commissioner"),
                "background": r.get("background", ""),
                "political_flag": political["political_flag"],
                "political_affiliation": political["political_affiliation"],
                "controversy": political["controversy"],
                "raw_text": (r["name"] + " " + r.get("background", ""))[:500],
                "source": r.get("source", ""),
            })

    return merged
KNOWN_POLITICAL_APPOINTMENTS = {
    "angga raka prabowo": "Wakil Menteri Komunikasi dan Digital (Wamen Komdigital)",
    "silmy karim": "Wakil Menteri Imigrasi dan Pemasyarakatan",
    "diaz fm hendropriyono": "Wakil Menteri Lingkungan Hidup",
    "nezar patria": "Wakil Menteri Komunikasi dan Digital",
    "suahasil nazara": "Wakil Menteri Keuangan",
    "sudaryono": "Wakil Menteri Pertanian",
    "faisol riza": "Wakil Menteri Perindustrian",
    "irene umar": "Wakil Menteri Ekonomi Kreatif",
    "rudy salahuddin": "Sekretaris Kementerian Investasi dan Hilirisasi / BKPM",
    "zainudin amali": "Mantan Wakil Menteri Olahraga (politisi Golkar)",
}


def detect_political(text: str, name: str = "") -> dict:
    """Detect political affiliation from text."""
    text_lower = text.lower()
    name_lower = name.lower().strip()

    # Check known appointments
    if name_lower in KNOWN_POLITICAL_APPOINTMENTS:
        return {
            "political_flag": True,
            "political_affiliation": KNOWN_POLITICAL_APPOINTMENTS[name_lower],
            "controversy": "Dual position: deputy minister / political figure + BUMN commissioner. "
                          "Violates spirit of Constitutional Court Decision No. 80/PUU-XXII/2019.",
        }

    # Check keywords
    for kw in POLITICAL_KEYWORDS:
        if kw in text_lower:
            return {
                "political_flag": True,
                "political_affiliation": f"Detected political keyword: '{kw}'",
                "controversy": "Background text contains political affiliation indicators.",
            }

    return {
        "political_flag": False,
        "political_affiliation": "",
        "controversy": "",
    }


def extract_commissioners_from_text(text: str) -> list:
    """Extract commissioner entries from page text — targeted extraction."""
    commissioners = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Find the "Dewan Komisaris" / "Board of Commissioners" section
    # and extract only that section until "Direksi" / "Board of Directors" or end
    start_idx = -1
    end_idx = len(lines)
    section_keywords = [
        "dewan komisaris", "board of commissioner", "komisaris & direksi",
        "komisaris dan direksi", "commissioner & director",
    ]
    end_keywords = [
        "dewan direksi", "board of director", "direksi", "board of directors",
        "jajaran direksi", "susunan direksi",
    ]

    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in section_keywords):
            start_idx = i
            break

    if start_idx == -1:
        # If no section header found, try looking for role keywords directly
        start_idx = 0
    else:
        # Find end of commissioner section
        for j in range(start_idx + 1, len(lines)):
            line_lower = lines[j].lower()
            if any(kw in line_lower for kw in end_keywords):
                end_idx = j
                break

    section_lines = lines[start_idx:end_idx]

    # Parse commissioner entries from the section
    # Look for patterns: Name followed by role, or "Role: Name"
    role_keywords = [
        "komisaris utama", "president commissioner", "komut",
        "wakil komisaris utama", "vice president commissioner",
        "komisaris independen", "independent commissioner",
        "komisaris", "commissioner",
    ]

    current_comm = None

    for line in section_lines:
        line_lower = line.lower()

        # Skip navigation and non-content lines
        if any(skip in line_lower for skip in [
            "navigasi", "log in", "login", "cookie", "© ", "all rights reserved",
            "hubungi kami", "email", "facebook", "twitter", "whatsapp",
            "kantor pusat", "menara", "berizin", "diawasi", "penjaminan",
            "navigation", "search", "menu", "footer",
        ]):
            continue

        # Check if line contains a role keyword
        role_found = None
        for kw in role_keywords:
            if kw in line_lower:
                role_found = kw
                break

        if role_found:
            # Save previous commissioner
            if current_comm and current_comm["name"]:
                commissioners.append(current_comm)

            # Extract name from line — it's either "Name" or "Role: Name" or "Name Role"
            name = line
            # Remove the role keyword from the line to get the name
            name = re.sub(re.escape(role_found), "", name, flags=re.IGNORECASE)
            name = re.sub(r'^[:\-\s\|/]+', '', name).strip()
            name = re.sub(r'\s+', ' ', name)

            # Clean prefixes
            name = re.sub(r'^(Bapak|Ibu|Drs\.|Dr\.|Ir\.|S\.H\.|S\.T\.|M\.M\.|M\.B\.A\.|S\.IP\.|S\.E\.)\s+', '', name)

            current_comm = {
                "name": name if len(name) > 3 else "",
                "role": role_found,
                "background": "",
            }
        else:
            # This line is either a name or background text
            if current_comm and not current_comm["name"] and len(line) > 3:
                # This is the name
                name = re.sub(r'^(Bapak|Ibu|Drs\.|Dr\.|Ir\.|S\.H\.|S\.T\.|M\.M\.|M\.B\.A\.|S\.IP\.|S\.E\.)\s+', '', line)
                current_comm["name"] = name
            elif current_comm and current_comm["name"]:
                # This is background text
                if len(current_comm["background"]) < 500:
                    current_comm["background"] += " " + line

    # Don't forget the last one
    if current_comm and current_comm["name"]:
        commissioners.append(current_comm)

    # Filter out entries that are clearly not names
    filtered = []
    for c in commissioners:
        name = c["name"].strip()
        # Must have at least 2 words or be a known single name
        if len(name) < 3:
            continue
        # Skip if it's a sentence (too long or contains certain patterns)
        if len(name) > 100:
            continue
        if any(skip in name.lower() for skip in [
            "promotion", "individual", "404", "not found", "beranda",
            "kembali", "halaman", "cari", "search",
        ]):
            continue
        c["name"] = name
        filtered.append(c)

    return filtered


async def scrape_bumn(page, bumn_key: str, bumn_info: dict, screenshots_dir: Path, log_func) -> dict:
    """Scrape a single BUMN's commissioner page."""
    result = {
        "bumn_name": bumn_info["name"],
        "short_name": bumn_info["short_name"],
        "sector": bumn_info["sector"],
        "ticker": bumn_info["ticker"],
        "source_url": "",
        "scrape_date": datetime.now().isoformat(),
        "commissioners": [],
        "page_title": "",
        "raw_text_length": 0,
        "error": "",
    }

    for url in bumn_info["urls"]:
        try:
            log_func(f"  Trying: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Wait for content to render
            await asyncio.sleep(3)

            # Try to wait for common content selectors
            try:
                await page.wait_for_selector("main, article, .content, #content, .commissioner, .komisaris", timeout=10000)
            except Exception:
                pass  # Content might still be there with different selectors

            # Take screenshot
            safe_name = bumn_key.replace(" ", "_")
            screenshot_path = screenshots_dir / f"final_execution_{safe_name}_page.png"
            await page.screenshot(path=str(screenshot_path))

            # Extract all text content
            text = await page.evaluate("""
                () => {
                    // Remove script and style elements
                    document.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                    return document.body ? document.body.innerText : '';
                }
            """)

            result["page_title"] = await page.title()
            result["source_url"] = url
            result["raw_text_length"] = len(text)

            log_func(f"  Page loaded: title='{result['page_title']}', text_len={len(text)}")

            if len(text) < 500:
                log_func(f"  [WARN] Page text too short ({len(text)} chars), might be blocked or empty")
                continue

            # Extract commissioners from text
            raw_commissioners = extract_commissioners_from_text(text)
            log_func(f"  Extracted {len(raw_commissioners)} potential commissioner entries")

            # If text extraction didn't find much, try structured DOM extraction
            if len(raw_commissioners) < 2:
                log_func(f"  Trying structured DOM extraction...")
                dom_commissioners = await page.evaluate("""
                    () => {
                        const results = [];
                        // Look for cards, profiles, or list items with commissioner names
                        const cards = document.querySelectorAll(
                            '.commissioner-card, .profile-card, .card, .komisaris, ' +
                            '[class*="commissioner"], [class*="komisaris"], ' +
                            '.team-member, .profile-item, .person-card'
                        );
                        cards.forEach(card => {
                            const text = card.innerText.trim();
                            if (text && text.length > 10) {
                                results.push(text);
                            }
                        });
                        return results;
                    }
                """)
                if dom_commissioners:
                    log_func(f"  DOM extraction found {len(dom_commissioners)} cards")
                    for card_text in dom_commissioners:
                        comms = extract_commissioners_from_text(card_text)
                        raw_commissioners.extend(comms)

            # Also try extracting from tables
            table_data = await page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    const results = [];
                    tables.forEach(table => {
                        const rows = table.querySelectorAll('tr');
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td, th');
                            const rowData = Array.from(cells).map(c => c.innerText.trim()).filter(t => t);
                            if (rowData.length > 0) results.push(rowData.join(' | '));
                        });
                    });
                    return results;
                }
            """)
            if table_data:
                log_func(f"  Found {len(table_data)} table rows")
                for row_text in table_data:
                    if any(kw in row_text.lower() for kw in ["komisaris", "commissioner"]):
                        raw_commissioners.append({
                            "name": row_text,
                            "role": "from table",
                            "background": "",
                        })

            # Deduplicate and enrich
            seen_names = set()
            for comm in raw_commissioners:
                name = comm.get("name", "").strip()
                if not name or len(name) < 3:
                    continue
                name_key = name.lower()[:30]
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)

                # Clean up name
                name = re.sub(r'\s+', ' ', name).strip()
                # Remove common prefixes
                name = re.sub(r'^(Bapak|Ibu|Drs\.|Dr\.|Ir\.|S\.H\.|S\.T\.|M\.M\.|M\.B\.A\.)\s+', '', name)

                background = comm.get("background", "").strip()
                political = detect_political(background + " " + name, name)

                result["commissioners"].append({
                    "name": name,
                    "role": comm.get("role", "Commissioner"),
                    "background": background[:1000] if background else "",
                    "political_flag": political["political_flag"],
                    "political_affiliation": political["political_affiliation"],
                    "controversy": political["controversy"],
                    "raw_text": (name + " " + background)[:500],
                })

            log_func(f"  Final commissioners count: {len(result['commissioners'])}")

            # Merge with researched data
            result["commissioners"] = merge_researched_data(result["commissioners"], bumn_key)
            log_func(f"  After merge with research data: {len(result['commissioners'])}")

            return result

        except Exception as e:
            log_func(f"  [ERROR] {url}: {e}")
            result["error"] = str(e)
            continue

    # If all URLs failed, use researched data as fallback
    if not result["commissioners"] and not result["source_url"]:
        researched = RESEARCHED_DATA.get(bumn_key, [])
        if researched:
            log_func(f"  All URLs failed. Using {len(researched)} researched entries as fallback.")
            for r in researched:
                political = detect_political(r.get("background", "") + " " + r["name"], r["name"])
                result["commissioners"].append({
                    "name": r["name"],
                    "role": r.get("role", "Commissioner"),
                    "background": r.get("background", ""),
                    "political_flag": political["political_flag"],
                    "political_affiliation": political["political_affiliation"],
                    "controversy": political["controversy"],
                    "raw_text": (r["name"] + " " + r.get("background", ""))[:500],
                    "source": r.get("source", ""),
                })

    return result


def save_results(results: list, output_dir: str):
    """Save results as JSON and CSV."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = output_path / "bumn_commissioners.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nJSON saved: {json_path}")

    # CSV
    csv_path = output_path / "bumn_commissioners.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "bumn_name", "short_name", "sector", "commissioner_name",
            "role", "political_flag", "political_affiliation",
            "background", "controversy", "source_url"
        ])
        writer.writeheader()
        for bumn in results:
            for comm in bumn.get("commissioners", []):
                writer.writerow({
                    "bumn_name": bumn["bumn_name"],
                    "short_name": bumn["short_name"],
                    "sector": bumn["sector"],
                    "commissioner_name": comm["name"],
                    "role": comm["role"],
                    "political_flag": comm["political_flag"],
                    "political_affiliation": comm["political_affiliation"],
                    "background": comm["background"][:200],
                    "controversy": comm["controversy"],
                    "source_url": bumn["source_url"],
                })
    print(f"CSV saved: {csv_path}")

    # Summary
    report_path = output_path / "summary_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("BUMN COMMISSIONER DATABASE — POC SUMMARY\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"{'='*70}\n\n")
        total_comm = 0
        total_political = 0
        for b in results:
            comms = b.get("commissioners", [])
            political_count = sum(1 for c in comms if c.get("political_flag"))
            total_comm += len(comms)
            total_political += political_count
            f.write(f"BUMN: {b['bumn_name']}\n")
            f.write(f"Sector: {b['sector']}\n")
            f.write(f"Source: {b['source_url']}\n")
            f.write(f"Commissioners: {len(comms)} (political: {political_count})\n")
            for c in comms:
                flag = "⚠️ POLITICAL" if c.get("political_flag") else "✓"
                f.write(f"  {flag} {c['name']} — {c['role']}\n")
                if c.get("political_affiliation"):
                    f.write(f"     → {c['political_affiliation']}\n")
            if b.get("error"):
                f.write(f"  ERROR: {b['error']}\n")
            f.write("\n")
        f.write(f"{'='*70}\n")
        f.write(f"TOTAL BUMN scraped: {len(results)}\n")
        f.write(f"TOTAL commissioners: {total_comm}\n")
        f.write(f"TOTAL political appointees: {total_political}\n")
    print(f"Summary saved: {report_path}")


async def main():
    parser = argparse.ArgumentParser(description="BUMN Commissioner Scraper")
    parser.add_argument("--bumn", default="all", help="Comma-separated BUMN names (default: all)")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--headless", default="true", help="Run headless (true/false)")
    args = parser.parse_args()

    # Determine which BUMN to scrape
    if args.bumn.lower() == "all":
        bumn_keys = list(BUMN_CONFIG.keys())
    else:
        bumn_keys = [k.strip().lower() for k in args.bumn.split(",")]
        for k in bumn_keys:
            if k not in BUMN_CONFIG:
                print(f"[ERROR] Unknown BUMN: {k}. Available: {list(BUMN_CONFIG.keys())}")
                return

    headless = args.headless.lower() != "false"
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output)
    screenshots_dir = Path(output_dir) / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    log_lines = []
    def log_func(msg):
        print(msg)
        log_lines.append(msg)

    print(f"\n{'='*60}")
    print(f"BUMN COMMISSIONER SCRAPER — Webwright Edition")
    print(f"Targets: {bumn_keys}")
    print(f"Headless: {headless}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    results = []
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 1800},
            locale="id-ID",
        )
        page = await context.new_page()

        for bumn_key in bumn_keys:
            bumn_info = BUMN_CONFIG[bumn_key]
            print(f"\n{'='*50}")
            print(f"Scraping: {bumn_info['name']}")
            print(f"{'='*50}")
            result = await scrape_bumn(page, bumn_key, bumn_info, screenshots_dir, log_func)
            results.append(result)

        await browser.close()

    # Save outputs
    save_results(results, output_dir)

    # Save log
    log_path = Path(output_dir) / "scrape_log.txt"
    log_path.write_text("\n".join(log_lines), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"DONE — {datetime.now().isoformat()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
