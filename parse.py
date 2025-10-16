import json
from bs4 import BeautifulSoup
import glob
import requests

def parse_lammps():    
    docs = []

    html_files = glob.glob("docs.lammps.org/*.html")  # adjust path
    html_files.sort()
    for file in html_files:
        soup = BeautifulSoup(open(file), "html.parser")
        heading_section = soup.find("h1")
        restriction_section = soup.find("section", {"id": "restrictions"})
        if restriction_section:
            # Find all <p> tags inside this section (usually one)
            paragraphs = restriction_section.find_all("p")
            restriction_text = " ".join(p.get_text(strip=True) for p in paragraphs)

            docs.append({
                "command": heading_section.get_text(strip=True),
                "restriction": restriction_text
            })

    return docs, len(docs)


def parse_nist(element: str):
    BASE_URL = "https://www.ctcms.nist.gov/potentials/system/"
    url = f"{BASE_URL}/{element}/"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    names = []
    for card in soup.select("ul.nav.nav-pills li a.nav-link"):
      span = card.find("span")
      if span:
          span.extract()
      names.append(card.get_text(strip=True))
    
    potentials = []
    for name in names:
      anchor = soup.find("a", attrs={"name": name})
      if not anchor:
          return []

      # Collect all siblings until the next <a name=...>
      for sib in anchor.find_all_next():
          if sib.name == "a" and sib.has_attr("name"):
              break  # stop when the next system starts
          if sib.name == "div" and "card" in sib.get("class", []):
              # --- ID and link ---
              header = sib.select_one("div.card-header h5 a")
              pot_id = header.text.strip() if header else None
              link = header["href"] if header else None

              # --- Citation ---
              citation = sib.select_one("div.citation")
              citation_text = citation.get_text(" ", strip=True) if citation else None

              # --- Abstract ---
              abstract = sib.select_one("div.abstract")
              abstract_text = abstract.get_text(" ", strip=True) if abstract else None

              # --- Notes ---
              notes = sib.select_one("div.description-notes")
              notes_text = notes.get_text(" ", strip=True) if notes else None

              # --- File downloads ---
              files = []
              file_links = sib.select("div.implementation-notes a[href]")
              for f in file_links:
                  href = f["href"]
                  if "Download" in href:
                      files.append(href)

              potentials.append({
                  "element": element,
                  "id": pot_id,
                  "link": link,
                  "citation": citation_text,
                  "abstract": abstract_text,
                  "notes": notes_text,
                  "files": files,
              })

    return potentials
