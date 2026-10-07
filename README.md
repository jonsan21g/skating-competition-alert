# Figure Skating Competition Registration Alert (`skating-competition-alert`)

Automated real-time monitoring and alerting engine for **Dansk Skøjte Union (DSU)** figure skating competition registrations.

Detects the exact moment a competition opens for registration, and alerts immediately if a **sold-out competition frees up a slot** before the registration deadline so you can register Joanne before slots vanish.

---

## 🎯 Key Capabilities

1. ⛸️ **Instant Registration Open Alerts**:
   - Dispatches a notification the moment any watched competition (or any newly announced competition) transitions to `Åben` (Open) status.
   - Provides direct one-click enrollment links to DSU Klubmodul.
2. 🚨 **Sold-Out Slot Reopened Alerts (Primary Feature)**:
   - When a competition reaches capacity (e.g. `200/200` skaters), the system flags it as sold out and begins high-frequency monitoring.
   - The instant a skater withdraws or cancels (e.g. dropping to `199/200`) while registration is still not officially closed (`Lukket`), the system sends an urgent **"SPOT REOPENED!"** alert with direct signup links.
3. 📈 **Capacity Expansion Detection**:
   - Alerts when organizers expand the maximum quota (e.g. from 200 to 250 skaters).
4. ⚡ **Low Spots Remaining Warning**:
   - Warns when fewer than 5 spots remain so you can register before it caps out.
5. 📲 **Multi-Channel Dispatch**:
   - **WhatsApp** via CallMeBot API (zero-config, matches `electricity-price-notification`).
   - **Telegram** via Telegram Bot API.
   - **Discord** via Webhooks.
   - **Email** via standard SMTP.
   - **Console / Terminal** for live interactive viewing.

---

## 📁 Project Structure

```text
skating-competition-alert/
├── .github/
│   └── workflows/
│       └── competition-alert.yml   # Automated GitHub Actions runner (every 30m)
├── config/
│   └── watchlist.json              # Targeted competitions, keywords, and alert rules
├── data/
│   └── state.json                  # Persistent state snapshot across runs
├── src/
│   ├── config.py                   # App configuration and .env parser
│   ├── models.py                   # Competition and AlertEvent data models
│   ├── scraper.py                  # DSU Klubmodul HTML scraper and parser
│   ├── monitor.py                  # State diffing & transition detector
│   ├── notifiers/                  # Notification dispatchers
│   │   ├── whatsapp.py             # CallMeBot WhatsApp dispatcher
│   │   ├── telegram.py             # Telegram bot dispatcher
│   │   ├── discord.py              # Discord webhook dispatcher
│   │   ├── email_notifier.py       # SMTP email dispatcher
│   │   └── console.py              # Pretty terminal dispatcher
│   └── main.py                     # CLI entrypoint and daemon runner
├── tests/                          # 100% automated test suite
├── .env.example                    # Sample environment variables
├── requirements.txt                # Python dependencies (requests, beautifulsoup4)
└── README.md
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure Notifications

Copy `.env.example` to `.env`:

```powershell
cp .env.example .env
```

To enable **WhatsApp** alerts via CallMeBot (same gateway as your electricity notifications):

```ini
NOTIFIERS_ENABLED=console,whatsapp
CALLMEBOT_PHONE=45XXXXXXXX
CALLMEBOT_API_KEY=your_callmebot_api_key
```

### 3. Verify Alert Dispatch

Send a test alert across your active channels:

```powershell
python -m src.main --test-alert
```

---

## 💻 CLI Commands

### 📊 View Live Competition Table
Fetches live data from DSU Klubmodul and displays current spots, deadlines, and registration status:

```powershell
python -m src.main --status
```

Example Output:
```text
=========================================================================================================
               DANISH FIGURE SKATING (DSU) COMPETITION REGISTRATION STATUS
=========================================================================================================
ID     | COMPETITION                         | STATUS    | SPOTS     | DEADLINE    | VENUE                    
---------------------------------------------------------------------------------------------------------
69     | Sjællands Cup  2026                 | OPEN      | 29/200    | 08.10.2026  | Skøjteklub København     
68     | Sjællands Mesterskaberne  2026      | OPEN      | 30/200    | 08.10.2026  | Skøjteklub København     
75     | FunSkate 1 VEST (Element & Free)    | OPEN      | 33/350    | 15.10.2026  | SE Arena                 
84     | NTG Samling                         | OPEN      | 8/100     | 06.11.2026  | Tårnby Skøjtehal         
67     | Jysk-Fynsk Cup  2026                | CLOSED    | 32/200    | 24.09.2026  | Frederikshavn Skøjtefo...
=========================================================================================================
```

### 🔍 Run a Single Check
Scrapes DSU, compares with previous snapshot, sends alerts if changes occurred, and updates `data/state.json`:

```powershell
python -m src.main --check
```

### 🔁 Run Background Monitoring Daemon
Keeps running continuously, checking every 300 seconds (5 minutes) or custom interval:

```powershell
python -m src.main --daemon --interval 180
```

### 🎯 Manage Watched Competitions
Add or remove competitions from `config/watchlist.json` directly from CLI:

```powershell
python -m src.main --watch "Isblomsten"
python -m src.main --unwatch "Isblomsten"
```

---

## ⚙️ Customizing the Watchlist (`config/watchlist.json`)

You can customize keyword rules and per-competition triggers:

```json
{
  "global_settings": {
    "alert_on_any_new_open": true,
    "warn_low_spots_threshold": 5,
    "check_interval_seconds": 300
  },
  "watched_competitions": [
    {
      "name": "Sjællands Cup",
      "keywords": ["Sjællands Cup", "Sjaellands Cup"],
      "alert_on_open": true,
      "alert_on_sold_out": true,
      "alert_on_reopened": true,
      "alert_deadline_hours": [48, 24]
    },
    {
      "name": "Isblomsten",
      "keywords": ["Isblomsten"],
      "alert_on_open": true,
      "alert_on_sold_out": true,
      "alert_on_reopened": true
    }
  ]
}
```

---

## 🧪 Automated Tests

Run the test suite:

```powershell
python -m unittest discover tests
```
