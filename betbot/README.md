# 🎰 BetBot — Virtual Betting Telegram Bot

Bot game betting virtual untuk grup Telegram. Main bareng, taruhan koin virtual, tidak ada uang nyata!

---

## 🎮 Mode Game

| Mode | Deskripsi | Pemain |
|------|-----------|--------|
| `coinflip` | Tebak Heads/Tails | 1-10 |
| `dadu` | Roll dadu, nilai tertinggi menang | 2-8 |
| `tebak_angka` | Tebak angka 1-10 | 1-10 |
| `roulette` | Pilih Merah/Hitam/Hijau (Hijau = 5x!) | 1-10 |
| `suit` | Gajah-Orang-Semut, khusus PvP | 2 |

---

## ⚙️ Setup

### 1. Buat Bot di Telegram
1. Chat [@BotFather](https://t.me/BotFather)
2. `/newbot` → isi nama & username
3. Salin **token** yang diberikan

### 2. Clone & Install
```bash
git clone <repo-url>
cd betbot
pip install -r requirements.txt
```

### 3. Konfigurasi
```bash
cp .env.example .env
# Edit .env, isi BOT_TOKEN dan ADMIN_IDS
```

### 4. Jalankan Lokal
```bash
python bot.py
```

---

## 🚀 Deploy Gratis

### Railway (Recommended)
1. Push ke GitHub
2. Buka [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Tambahkan **Environment Variables**:
   - `BOT_TOKEN` = token dari BotFather
   - `ADMIN_IDS` = Telegram user ID kamu
4. Deploy otomatis ✅

> ⚠️ **Catatan Railway**: Data JSON tersimpan di container, akan reset jika redeploy. Untuk data permanen, upgrade ke Railway Pro atau gunakan Railway's PostgreSQL (gratis $5/bulan kredit).

### Render
1. Push ke GitHub
2. [render.com](https://render.com) → New → Background Worker
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python bot.py`
5. Tambahkan Environment Variables sama seperti di atas

### Replit
1. Buat Repl baru, upload semua file
2. Tambahkan Secrets: `BOT_TOKEN` dan `ADMIN_IDS`
3. Klik Run

---

## 📋 Daftar Command

### Pemain
| Command | Fungsi |
|---------|--------|
| `/start` | Daftar & sambutan |
| `/saldo` atau `/balance` | Cek saldo koin |
| `/daily` | Ambil reward harian (200 🪙) |
| `/leaderboard` atau `/top` | Top 10 terkaya |
| `/transfer @user jumlah` | Transfer koin |
| `/game [mode] [bet]` | Buka game di grup |
| `/join` | Ikut game aktif |
| `/startgame` | Mulai game (host only) |
| `/cancel` | Batalkan game |
| `/duel @user [mode] [bet]` | Tantang PvP |

### Admin
| Command | Fungsi |
|---------|--------|
| `/admin` | Panel admin |

---

## 💡 Sistem Reward

- **Saldo awal**: 1,000 🪙
- **Daily reward**: 200 🪙 (sekali per 24 jam)
- **Menang**: Dapat 2x bet (kecuali Roulette Hijau = 5x)
- **Kalah**: Kehilangan bet
- **Seri (Dadu)**: Koin dikembalikan
- **P2P Duel**: Menang dapat koin lawan, kalah koin berkurang

---

## 🏗️ Struktur File

```
betbot/
├── bot.py              # Entry point
├── database.py         # Manajemen data JSON
├── session.py          # State game aktif (in-memory)
├── handlers/
│   ├── commands.py     # /start, /saldo, /daily, dll
│   ├── game_handler.py # Game grup
│   ├── pvp_handler.py  # Duel 1v1
│   └── admin_handler.py
├── games/
│   └── logic.py        # Logika semua game
├── requirements.txt
├── Procfile
└── railway.toml
```
