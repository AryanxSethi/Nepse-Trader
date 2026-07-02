import httpx
from bs4 import BeautifulSoup

c = httpx.Client(verify=False, timeout=15, headers={"User-Agent": "Mozilla/5.0"})

# Check the homepage for the IPO section
r = c.get("https://merolagani.com")
soup = BeautifulSoup(r.text, "html.parser")

# Find the div with id containing "IPO" or "ipo"
div = soup.find(id=lambda x: x and "ipo" in x.lower())
if div:
    print("=== IPO DIV FOUND ===")
    print(div.prettify()[:2000])
else:
    print("No IPO-specific div found")

# Look for any section with IPO-related text
print("\n=== Looking for IPO-related sections ===")
for tag in soup.find_all(["div", "section", "ul"]):
    text = tag.get_text(strip=True)
    if "ipo" in text.lower() and len(text) < 500:
        cls = tag.get("class", [])
        print(f"[{tag.name}] class={cls}")
        print(f"  text: {text[:300]}")

# Check the right panel sections
print("\n=== Right panel / sidebar sections ===")
for tag in soup.find_all("div", class_=lambda x: x and "panel" in x.lower()):
    heading = tag.find(["h3", "h4", "h5", "div"], class_=lambda x: x and "heading" in x.lower())
    h_text = heading.get_text(strip=True) if heading else ""
    body = tag.find("div", class_=lambda x: x and "body" in x.lower())
    b_text = body.get_text(strip=True)[:300] if body else ""
    if "ipo" in h_text.lower() or "announcement" in h_text.lower() or "results" in h_text.lower():
        print(f"  Panel heading: {h_text}")
        print(f"  Body: {b_text[:500]}")
        print(f"  HTML:\n{tag.prettify()[:2000]}")

# Look at AnnouncementDetail page for one IPO
print("\n=== AnnouncementDetail.aspx?id=65992 ===")
r2 = c.get("https://merolagani.com/AnnouncementDetail.aspx?id=65992")
soup2 = BeautifulSoup(r2.text, "html.parser")
print(f"Status: {r2.status_code}")
tables = soup2.find_all("table")
print(f"Tables: {len(tables)}")
for i, t in enumerate(tables):
    rows = t.find_all("tr")
    print(f"  Table {i}: {len(rows)} rows")
    if rows:
        cells = rows[0].find_all(["th", "td"])
        print(f"    first: {[c.get_text(strip=True)[:40] for c in cells]}")
        if len(rows) > 1:
            cells2 = rows[1].find_all("td")
            print(f"    second: {[c.get_text(strip=True)[:40] for c in cells2]}")

# Get the page title and body
title = soup2.title.string if soup2.title else ""
print(f"Title: {title}")
body_text = soup2.get_text()
# Search for IPO-related text in body
import re
for line in body_text.split("\n"):
    line = line.strip()
    if line and ("ipo" in line.lower() or "issue" in line.lower() or "unit" in line.lower() or "date" in line.lower()):
        print(f"  {line[:200]}")
