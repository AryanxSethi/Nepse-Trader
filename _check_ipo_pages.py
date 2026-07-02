import httpx
from bs4 import BeautifulSoup

c = httpx.Client(verify=False, timeout=15, headers={"User-Agent": "Mozilla/5.0"})

# Check /Ipo.aspx?type=upcoming
print("=== /Ipo.aspx?type=upcoming ===")
r = c.get("https://merolagani.com/Ipo.aspx?type=upcoming")
soup = BeautifulSoup(r.text, "html.parser")
print(f"Status: {r.status_code}")
print(f"Title: {soup.title.string if soup.title else 'none'}")

tables = soup.find_all("table")
print(f"Tables: {len(tables)}")
for i, t in enumerate(tables):
    rows = t.find_all("tr")
    print(f"  Table {i}: {len(rows)} rows")
    if rows:
        cells = rows[0].find_all(["th", "td"])
        print(f"    header: {[c.get_text(strip=True)[:40] for c in cells]}")
    if len(rows) > 1:
        cells = rows[1].find_all("td")
        print(f"    data 1: {[c.get_text(strip=True)[:40] for c in cells]}")
    if len(rows) > 2:
        cells = rows[2].find_all("td")
        print(f"    data 2: {[c.get_text(strip=True)[:40] for c in cells]}")

# Check /Ipo.aspx?type=past  
print("\n=== /Ipo.aspx?type=past ===")
r2 = c.get("https://merolagani.com/Ipo.aspx?type=past")
soup2 = BeautifulSoup(r2.text, "html.parser")
print(f"Status: {r2.status_code}")
tables2 = soup2.find_all("table")
print(f"Tables: {len(tables2)}")
for i, t in enumerate(tables2):
    rows = t.find_all("tr")
    print(f"  Table {i}: {len(rows)} rows")
    if rows:
        cells = rows[0].find_all(["th", "td"])
        print(f"    header: {[c.get_text(strip=True)[:40] for c in cells]}")
    if len(rows) > 1:
        cells = rows[1].find_all("td")
        print(f"    data 1: {[c.get_text(strip=True)[:40] for c in cells]}")

# Check /AnnouncementList.aspx
print("\n=== /AnnouncementList.aspx ===")
r3 = c.get("https://merolagani.com/AnnouncementList.aspx")
soup3 = BeautifulSoup(r3.text, "html.parser")
print(f"Status: {r3.status_code}")
tables3 = soup3.find_all("table")
print(f"Tables: {len(tables3)}")
for i, t in enumerate(tables3):
    rows = t.find_all("tr")
    print(f"  Table {i}: {len(rows)} rows")
    if rows:
        cells = rows[0].find_all(["th", "td"])
        print(f"    header: {[c.get_text(strip=True)[:40] for c in cells]}")
