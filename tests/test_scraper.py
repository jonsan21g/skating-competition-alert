"""Unit tests for DSU competition scraper."""

import unittest
from src.scraper import DsuCompetitionScraper

MOCK_HTML = """
<!DOCTYPE html>
<html>
<body>
<table>
  <tr>
    <th>Event</th><th>Dato</th><th>Frist</th><th>Sted</th><th>Pris</th><th>Tilmeld</th><th>Spots</th><th>Details</th>
  </tr>
  <tr>
    <td>Sjællands Cup 2026</td>
    <td>13.11.2026-15.11.2026</td>
    <td>08.10.2026</td>
    <td>Skøjteklub København</td>
    <td>Valg</td>
    <td>Åben</td>
    <td>29/200</td>
    <td>
      <a href="ProfileEventEnrollment.aspx?EventID=69">Tilmeld - Læs mere</a>
      <p>Novice A2 Girls</p>
      <p>Springs A2 Mixed</p>
    </td>
  </tr>
  <tr>
    <td>Isblomsten 2026</td>
    <td>20.01.2026-22.01.2026</td>
    <td>10.01.2026</td>
    <td>Herlev Skøjtehal</td>
    <td>500kr.</td>
    <td>Åben</td>
    <td>200/200</td>
    <td>
      <a href="ProfileEventEnrollment.aspx?EventID=101">Venteliste</a>
    </td>
  </tr>
  <tr>
    <td>Jysk-Fynsk Cup 2026</td>
    <td>30.10.2026-01.11.2026</td>
    <td>24.09.2026</td>
    <td>Frederikshavn Skøjteforening</td>
    <td>Valg</td>
    <td>Lukket</td>
    <td>32/200</td>
    <td>
      <a href="ProfileEventEnrollment.aspx?EventID=67">Tilmelding slut</a>
    </td>
  </tr>
</table>
</body>
</html>
"""


class TestDsuCompetitionScraper(unittest.TestCase):

    def setUp(self):
        self.scraper = DsuCompetitionScraper()

    def test_parse_html(self):
        comps = self.scraper._parse_html(MOCK_HTML)
        self.assertEqual(len(comps), 3)

        # Comp 1: Open with spots available
        c1 = comps[0]
        self.assertEqual(c1.event_id, "69")
        self.assertEqual(c1.title, "Sjællands Cup 2026")
        self.assertEqual(c1.spots_taken, 29)
        self.assertEqual(c1.spots_max, 200)
        self.assertEqual(c1.spots_available, 171)
        self.assertTrue(c1.is_open)
        self.assertFalse(c1.is_sold_out)
        self.assertFalse(c1.is_closed)
        self.assertIn("Novice A2 Girls", c1.categories)

        # Comp 2: Sold out (200/200 capacity reached)
        c2 = comps[1]
        self.assertEqual(c2.event_id, "101")
        self.assertEqual(c2.title, "Isblomsten 2026")
        self.assertEqual(c2.spots_taken, 200)
        self.assertEqual(c2.spots_max, 200)
        self.assertEqual(c2.spots_available, 0)
        self.assertTrue(c2.is_sold_out)
        self.assertFalse(c2.is_open)
        self.assertFalse(c2.is_closed)

        # Comp 3: Closed
        c3 = comps[2]
        self.assertEqual(c3.event_id, "67")
        self.assertEqual(c3.title, "Jysk-Fynsk Cup 2026")
        self.assertTrue(c3.is_closed)
        self.assertFalse(c3.is_open)


if __name__ == "__main__":
    unittest.main()
