import json
from bs4 import BeautifulSoup
import glob
import requests
from typing import Dict, Any, List
import ast

class Parser:
    def __init__(self):
        pass

    def _save_json(self, data: Dict[str, Any], filename: str):
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    def parse_lammps(self):
        docs = []
        html_files = glob.glob("docs.lammps.org/*.html")  # adjust path
        html_files.sort()

        for file in html_files:
            soup = BeautifulSoup(open(file), "html.parser")
            heading_section = soup.find("h1")
            restriction_section = soup.find("section", {"id": "restrictions"})
            description_section = (
                soup.find("section", {"id": "description"})
                or soup.find("div", {"id": "description"})
                or soup.find("h2", string=lambda t: t and "Description" in t)
            )
            
            if restriction_section and description_section:
                restriction_paragraphs = restriction_section.find_all("p")
                restriction_text = " ".join([p.get_text(strip=True) for p in restriction_paragraphs])

                description_paragraphs = description_section.find_all("p")
                description_text = " ".join([p.get_text(strip=True) for p in description_paragraphs])
                
                command_text = heading_section.get_text(strip=True) if heading_section else "Unknown Command"
                
                docs.append({
                    "command": command_text,
                    "restriction": restriction_text,
                    "description": description_text
                })

        self._save_json(docs, "./data/LAMMPSData/lammps_data.json")

    def parse_nist(self, element: str):
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


if __name__ == "__main__":
    parser = Parser()
    parser.parse_lammps()