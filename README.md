# BUMN Watch — Database Komisaris BUMN Indonesia

Transparansi tata kelola BUMN: lacak afiliasi politik, kekayaan (LHKPN), dan rekam jejak hukum komisaris BUMN Indonesia.

## 📊 Data
- 37 komisaris dari 6 BUMN terbesar (Telkom, Pertamina, PLN, Bank Mandiri, BRI, Indosat)
- Afiliasi politik: kader partai, relawan pemenangan, pejabat
- Demografi: usia, pendidikan, riwayat karir
- Kekayaan: data LHKPN dari KPK
- Rekam jejak hukum: kasus KPK, vonis, status tersangka
- 150+ source links yang dapat diverifikasi

## 🗂️ Struktur Repo
```
bumn-watch/
├── dashboard/
│   └── index.html          # Interactive dashboard (single HTML file)
├── scraper/
│   └── final_script.py     # Playwright scraper untuk website BUMN
├── data/
│   ├── bumn_database_final.json   # Database lengkap (rich)
│   └── bumn_commissioners.csv     # Export CSV
├── docs/
│   ├── methodology.md      # Metodologi riset & klasifikasi
│   └── sources.md           # Daftar semua sumber
├── README.md
└── LICENSE                  # MIT
```

## 🚀 Cara Pakai
1. Buka `dashboard/index.html` di browser, atau deploy ke Netlify/Vercel/GitHub Pages
2. Pilih BUMN → lihat komisaris → klik untuk profil lengkap
3. Data mentah: `data/bumn_database_final.json`

## ⚠️ Disclaimer
Semua data dari sumber publik (Kompas, Tempo, CNN Indonesia, Detik, KPK e-LHKPN, website resmi BUMN). Setiap klaim memiliki link sumber yang dapat diverifikasi. Tujuan: transparansi tata kelola BUMN, bukan tuduhan kriminal.

## 📅 Data per
Juni 2026

## License
MIT
