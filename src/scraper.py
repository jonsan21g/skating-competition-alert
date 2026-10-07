"""Web scraper for Dansk Skøjte Union (DSU) Klubmodul competition portal."""

import logging
import re
from typing import List, Optional
import requests
from bs4 import BeautifulSoup

from .config import AppConfig
from .models import Competition

logger = logging.getLogger(__name__)


class DsuCompetitionScraper:
    """Scrapes official DSU competition registrations from Klubmodul."""

    def __init__(self, url: Optional[str] = None):
        self.url = url or AppConfig.DSU_OVERVIEW_LIST_URL
        self.base_url = AppConfig.DSU_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "da-DK,da;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    def fetch_competitions(self) -> List[Competition]:
        """
        Fetches competitions across DSU sources:
        1. Official DSU Klubmodul registration portal (active signups, spots, status)
        2. DSU official calendar (terminsplan) for upcoming scheduled competitions (Isblomsten, Forårskonkurrence, etc.)
        3. Tårnby Skøjteklub dedicated Flyver Cup portal
        """
        competitions: List[Competition] = []

        # 1. Active DSU Klubmodul registrations
        logger.info(f"Fetching active DSU registrations from {self.url}...")
        try:
            resp = self.session.get(self.url, timeout=30)
            resp.raise_for_status()

            content = resp.content
            html = ""
            for encoding in ("utf-8", "utf-8-sig", "iso-8859-1", "windows-1252"):
                try:
                    html = content.decode(encoding)
                    if "Sjælland" in html or "København" in html or "Åben" in html:
                        break
                except UnicodeDecodeError:
                    continue

            if not html:
                html = resp.text

            competitions.extend(self._parse_html(html))
        except requests.RequestException as e:
            logger.error(f"Failed to fetch DSU registrations from Klubmodul: {e}")

        # 2. Upcoming competitions from DSU Official Calendar (Terminsplan)
        try:
            cal_comps = self._fetch_dsu_calendar_competitions(existing=competitions)
            competitions.extend(cal_comps)
        except Exception as e:
            logger.warning(f"Failed to fetch DSU calendar competitions: {e}")

        # 3. Dedicated TSK Flyver Cup portal
        try:
            flyver_comp = self._check_tsk_flyver_cup()
            if flyver_comp and not any("flyver" in c.title.lower() for c in competitions):
                competitions.append(flyver_comp)
        except Exception as e:
            logger.warning(f"Failed to check TSK Flyver Cup portal: {e}")

        return competitions

    def _parse_html(self, html: str) -> List[Competition]:
        """Parses HTML content from DSU EventOverviewList.aspx."""
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            logger.warning("No table found on EventOverviewList page.")
            return []

        rows = table.find_all("tr")
        if len(rows) <= 1:
            logger.warning("No data rows found in competitions table.")
            return []

        competitions: List[Competition] = []

        for tr in rows[1:]:
            tds = tr.find_all("td")
            if len(tds) < 7:
                continue

            title = tds[0].get_text(strip=True)
            dates = tds[1].get_text(strip=True)
            deadline = tds[2].get_text(strip=True)
            venue = tds[3].get_text(strip=True)
            price = tds[4].get_text(strip=True)
            status_text = tds[5].get_text(strip=True)
            spots_str = tds[6].get_text(strip=True)

            # Parse spots: e.g. "29/200"
            spots_taken = 0
            spots_max = 0
            spots_match = re.search(r"(\d+)\s*/\s*(\d+)", spots_str)
            if spots_match:
                spots_taken = int(spots_match.group(1))
                spots_max = int(spots_match.group(2))

            spots_available = max(0, spots_max - spots_taken) if spots_max > 0 else 0

            # Extract EventID and Links
            event_id = ""
            reg_url = ""
            part_url = ""

            for a in tr.find_all("a"):
                href = a.get("href", "")
                id_match = re.search(r"EventID=(\d+)", href, re.IGNORECASE)
                if id_match:
                    event_id = id_match.group(1)
                    if "ProfileEventEnrollment" in href and not reg_url:
                        reg_url = href if href.startswith("http") else f"{self.base_url}{href.lstrip('/')}"
                    elif "EventShowParticipants" in href and not part_url:
                        part_url = href if href.startswith("http") else f"{self.base_url}{href.lstrip('/')}"

            if not reg_url and event_id:
                reg_url = f"{self.base_url}ProfileEventEnrollment.aspx?EventID={event_id}"

            # Fallback event ID from title if missing
            if not event_id:
                event_id = re.sub(r"[^a-zA-Z0-9]", "_", title.lower())

            # Determine registration states
            status_lower = status_text.lower()
            is_closed = any(term in status_lower for term in ("lukket", "closed", "slut"))
            
            # Determine sold out state:
            # An event is sold out if spots_max is defined and taken >= max, or text specifies it,
            # BUT it is not yet past the deadline / officially closed.
            is_sold_out = False
            if spots_max > 0 and spots_taken >= spots_max:
                is_sold_out = True
            elif any(term in status_lower for term in ("udsolgt", "venteliste")):
                is_sold_out = True

            # Open state: status says Åben and spots are available, or not closed
            is_open = (
                any(term in status_lower for term in ("åben", "aaben", "open"))
                and not is_sold_out
                and not is_closed
            )

            # Extract category chips from detail column (td 7)
            categories = []
            if len(tds) >= 8:
                detail_text = tds[7].get_text(separator="\n", strip=True)
                for line in detail_text.splitlines():
                    line_clean = line.strip()
                    if any(k in line_clean.lower() for k in [
                        "novice", "springs", "junior", "senior", "cubs", "debs", "fun", "sololøb", "isdans"
                    ]):
                        if len(line_clean) < 50:
                            categories.append(line_clean)

            comp = Competition(
                event_id=event_id,
                title=title,
                dates=dates,
                deadline=deadline,
                venue=venue,
                price=price,
                status=status_text,
                spots_taken=spots_taken,
                spots_max=spots_max,
                spots_available=spots_available,
                is_open=is_open,
                is_sold_out=is_sold_out,
                is_closed=is_closed,
                categories=categories,
                registration_url=reg_url,
                participants_url=part_url,
            )
            competitions.append(comp)

        logger.info(f"Successfully scraped {len(competitions)} competitions from Klubmodul.")
        return competitions

    def _fetch_dsu_calendar_competitions(self, existing: List[Competition]) -> List[Competition]:
        """
        Fetches upcoming scheduled competitions announced on DSU official Terminsplan
        (https://www.danskate.dk/events/) that have not yet opened for registration on Klubmodul.
        """
        calendar_url = "https://www.danskate.dk/events/"
        logger.info(f"Checking DSU official event calendar from {calendar_url}...")
        resp = self.session.get(calendar_url, timeout=25)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.content.decode("utf-8", errors="ignore"), "html.parser")
        cal_comps: List[Competition] = []

        for a in soup.find_all("a", class_="event-block"):
            txt = a.get_text(separator=" ", strip=True)
            if any(skip in txt.lower() for skip in ["uddannelse", "træner", "ungleder", "bestyrelse"]):
                continue

            href = a.get("href", "")
            match = re.search(r"(\d{1,2}\s+[a-zæøå]{3}\s+[a-zæøå]+)\s+(.+)", txt, re.IGNORECASE)
            if not match:
                continue

            date_raw = match.group(1).strip()
            body_text = match.group(2).strip()

            title = body_text
            venue = ""
            for city in ["Herlev", "Rødovre", "Aalborg", "Hørsholm", "Gentofte", "Frederikshavn", "Vojens", "Gladsaxe", "København"]:
                if city in body_text:
                    venue = f"{city} Skøjtehal"
                    parts = body_text.split(city, 1)
                    title = parts[0].strip()
                    break

            if not title:
                title = body_text

            # Normalize title
            title_clean = re.sub(r"\s+", " ", title).strip()

            # Avoid duplicating competitions already live on Klubmodul
            title_lower = title_clean.lower()
            if any(title_lower in c.title.lower() or c.title.lower() in title_lower for c in existing):
                continue
            if any(title_lower == c.title.lower() for c in cal_comps):
                continue

            comp_id = "dsu_cal_" + re.sub(r"[^a-zA-Z0-9]", "_", title_clean.lower()).strip("_")
            cal_comps.append(
                Competition(
                    event_id=comp_id,
                    title=f"{title_clean} (Terminsplan)",
                    dates=date_raw,
                    deadline="Ikke åbnet endnu",
                    venue=venue,
                    price="-",
                    status="Kommende",
                    spots_taken=0,
                    spots_max=0,
                    spots_available=0,
                    is_open=False,
                    is_sold_out=False,
                    is_closed=False,
                    registration_url=href,
                )
            )

        logger.info(f"Found {len(cal_comps)} scheduled upcoming competitions on DSU calendar.")
        return cal_comps

    def _check_tsk_flyver_cup(self) -> Optional[Competition]:
        """
        Checks Tårnby Skøjteklub's dedicated Flyver Cup portal
        (https://taarnbyskojteklub.dk/klub/tarnby-skojteklub/sider/flyver-cup-2027)
        for published invitation and registration links.
        """
        tsk_url = "https://taarnbyskojteklub.dk/klub/tarnby-skojteklub/sider/flyver-cup-2027"
        try:
            resp = self.session.get(tsk_url, timeout=20)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.content.decode("utf-8", errors="ignore"), "html.parser")
            content_div = soup.find("div", class_="content") or soup.body
            content_text = content_div.get_text().lower() if content_div else ""

            has_invitation = any(k in content_text for k in ["invitation", "tilmelding", "forms.gle", "google.com/forms", "klubmodul", "sportity"])

            return Competition(
                event_id="tsk_flyver_cup_2027",
                title="Flyver Cup 2027 (Tårnby Skøjteklub)",
                dates="Vinter 2027",
                deadline="Ikke åbnet endnu" if not has_invitation else "Se portal",
                venue="Tårnby Skøjtehal",
                price="Valg",
                status="Åben" if has_invitation else "Kommende",
                spots_taken=0,
                spots_max=0,
                spots_available=0,
                is_open=has_invitation,
                is_sold_out=False,
                is_closed=False,
                registration_url=tsk_url,
            )
        except Exception as e:
            logger.warning(f"Error checking Flyver Cup page: {e}")
            return None

