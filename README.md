# Figure Skating Competition Registration Alert (`skating-competition-alert`)

Automated real-time monitoring and alerting engine for Danish figure skating (**Dansk Skøjte Union / DSU**) competitions, focused strictly on 4 target events and delivering instant alerts via **WhatsApp** (CallMeBot).

---

## 🎯 Target Competitions Tracked

The engine monitors registration availability and sold-out slot reopenings exclusively for:

1. 🌸 **Forårskonkurrence Øst** (FKO / Rødovre Skøjtehal, 09–10 Jan 2027) — *Currently announced on Terminsplan; registration not open yet.*
2. ❄️ **Isblomsten** (Herlev Skøjtehal, 30–31 Jan 2027) — *Currently announced on Terminsplan; registration not open yet.*
3. 🐧 **Pingvin Cup** (Gladsaxe Skøjtehal / GSF, 03–04 Apr 2027) — *Portal active; registration not open yet.*
4. ✈️ **Flyver Cup** (Tårnby Skøjtehal / TSK, 12–14 Feb 2027) — *Currently **SOLD OUT** (200/200 participants reached on Holdsport), but **NOT CLOSED** (deadline 15 Nov 2026 kl. 16:45). Alerts immediately if any spot reopens!*

---

## 🚨 Core Alert Capabilities

- ⛸️ **Instant Registration Open Alerts**: Fires immediately when any of the 4 competitions officially opens for signups.
- 🚨 **Sold-Out Slot Reopening Alerts (Primary Feature)**: Because Flyver Cup is capped at 200/200 participants but registration closes on 15 Nov 2026, the scraper monitors for cancellations. The instant a slot reopens (`spots_available > 0`), an urgent WhatsApp message is dispatched with direct registration links.
- 💬 **WhatsApp Dispatch (Zero Cost)**: Uses the CallMeBot API (shared with `electricity-price-notification`).

---

## ⚙️ Dual Configuration Files (`config/`)

The configuration is partitioned into two dedicated JSON files:

1. **`config/watchlist.json`**:
   Declares the 4 watched competitions, keyword aliases, and alert transition rules (`alert_on_open`, `alert_on_sold_out`, `alert_on_reopened`).

2. **`config/sources.json`**:
   Declares the exact external portals and URLs where the scraper checks each competition:
   - `hiku_klubmodul`: Herlev IF Kunstskøjteafdeling (HIKU) dedicated Klubmodul portal (`https://hiku.dk/cms/EventOverview.aspx` & JSON feed `https://hiku.dk/cms/include/api/json/events.aspx`) for **Isblomsten**.
   - `dsu_klubmodul`: Central DSU registration list (`https://dsu.klub-modul.dk/cms/EventOverviewList.aspx`)
   - `dsu_calendar`: DSU Official Terminsplan / Calendar (`https://www.danskate.dk/events/`)
   - `holdsport_flyver_cup`: Dedicated Flyver Cup Holdsport ticket portal (`https://www.holdsport.dk/public_ticket_events/flyver-cup-20276`)
   - `gsf_pingvin_cup`: Dedicated GSF Pingvin Cup portal (`https://gsf-kunst.dk/klub/gladsaxe-skojtelober-forening/sider/pingvin-cup-2027`)

---

## 📁 Project Architecture

```text
skating-competition-alert/
├── .github/
│   └── workflows/
│       └── competition-alert.yml   # Twice-daily GitHub Actions runner (07:09 & 19:09 CET)
├── config/
│   ├── watchlist.json              # The 4 target competitions & alert rules
│   └── sources.json                # Scraper URLs & monitored endpoints
├── data/
│   └── state.json                  # Persistent registration snapshot across runs
├── src/
│   ├── config.py                   # App configuration and .env parser
│   ├── models.py                   # Competition & AlertEvent data models
│   ├── scraper.py                  # Multi-source scraper (DSU, Holdsport, GSF, Terminsplan)
│   ├── monitor.py                  # State transition engine & change detector
│   ├── notifiers/                  # Clean notification dispatchers
│   │   ├── base.py                 # Base notifier abstract interface
│   │   ├── whatsapp.py             # WhatsApp CallMeBot dispatcher
│   │   ├── console.py              # Pretty terminal logger
│   │   └── __init__.py             # Notifier registry
│   └── main.py                     # CLI entrypoint (--check, --status, --test-alert)
├── tests/                          # 13 automated unit tests (100% passing)
│   ├── test_monitor.py             # Reopened spots & transition detection tests
│   ├── test_notifiers.py           # WhatsApp dispatch & CallMeBot tests
│   ├── test_scraper.py             # HTML table parsing tests
│   └── test_sources.py             # Dual config & 4-competition targeting tests
├── .env.example                    # Sample WhatsApp credentials
├── requirements.txt                # Python dependencies (requests, beautifulsoup4)
└── README.md
```

---

## ⏰ Automation Schedule (GitHub Actions)

The runner runs automatically 3 times daily on GitHub Actions:
- **06:09 Danish Time** (05:09 UTC CET)
- **13:09 Danish Time** (12:09 UTC CET)
- **19:09 Danish Time** (18:09 UTC CET)
- **Cron**: `'9 5,12,18 * * *'`
- **Zero Spam**: If there are no registration status changes, **no WhatsApp alert is sent**. Alerts are strictly dispatched when a spot reopens or registration opens.

### GitHub Secrets Required:
| Secret Name | Description | Example |
|---|---|---|
| `CALLMEBOT_PHONE` | Phone number with country code (no `+` or spaces) | `4512345678` |
| `CALLMEBOT_API_KEY` | CallMeBot WhatsApp API key | `1234567` |

---

## 💻 CLI Commands

### 1. View Current Status of the 4 Competitions
```powershell
python -m src.main --status
```

### 2. Run a Single Check & Dispatch Alert if Changed
```powershell
python -m src.main --check
```

### 3. Send a Test WhatsApp Alert
```powershell
python -m src.main --test-alert
```

### 4. Run Automated Tests
```powershell
python -m unittest discover tests
```
