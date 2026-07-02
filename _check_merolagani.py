import httpx, re
from bs4 import BeautifulSoup

c = httpx.Client(verify=False, timeout=15, headers={"User-Agent": "Mozilla/5.0"})

# Check homepage for IPO links
r = c.get("https://merolagani.com")
soup = BeautifulSoup(r.text, "html.parser")
print("=== HOMEPAGE IPO LINKS ===")
for a in soup.find_all("a", href=True):
    h = a["href"]
    if "ipo" in h.lower() or "announcement" in h.lower():
        print(f"  {a.get_text(strip=True)[:60]} -> {h}")

# Check LatestNews page
print("\n=== LatestNews page ===")
r2 = c.get("https://merolagani.com/LatestNews.aspx")
soup2 = BeautifulSoup(r2.text, "html.parser")
for a in soup2.find_all("a", href=True):
    h = a["href"]
    if "ipo" in h.lower() or "announcement" in h.lower():
        print(f"  {a.get_text(strip=True)[:60]} -> {h}")

# Check Announcement page
print("\n=== Announcement page ===")
r3 = c.get("https://merolagani.com/Announcement.aspx")
soup3 = BeautifulSoup(r3.text, "html.parser")
print(f"Status: {r3.status_code}")
print(f"Title: {soup3.title.string if soup3.title else 'none'}")

# Look for tables
tables = soup3.find_all("table")
print(f"Tables: {len(tables)}")
for i, t in enumerate(tables):
    rows = t.find_all("tr")
    print(f"  Table {i}: {len(rows)} rows")
    if rows:
        cells = rows[0].find_all(["th", "td"])
        print(f"    headers: {[c.get_text(strip=True)[:30] for c in cells]}")
    if len(rows) > 1:
        cells = rows[1].find_all("td")
        print(f"    first data: {[c.get_text(strip=True)[:30] for c in cells]}")
