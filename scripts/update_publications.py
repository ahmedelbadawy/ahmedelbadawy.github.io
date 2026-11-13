#!/usr/bin/env python3
"""
Refresh publications.json from Crossref, and (optionally) build one static page per
paper with Google Scholar <meta name="citation_*"> tags.

Standard library only. Run from the repository root:

    python scripts/update_publications.py               # fill missing metadata/abstracts from Crossref
    python scripts/update_publications.py --find-dois   # also look up DOIs by title for entries without one
    python scripts/update_publications.py --pages       # also (re)build papers/<id>.html and sitemap.xml
    python scripts/update_publications.py --dry-run     # show what would change, write nothing

Other options:
    --force           overwrite existing fields with Crossref values (default: only fill empty fields)
    --openalex        if Crossref has no abstract, store OpenAlex's text in "abstract_unverified"
                      (never in "abstract"): check it against the publisher page before promoting it
    --mailto ADDRESS  identify yourself to Crossref's "polite pool" (optional, recommended)

Rules the script follows:
  * Entries with "skip_crossref": true are never looked up (e.g. a DOI that points to a whole
    abstract supplement rather than the individual abstract).
  * Abstracts are only ever taken verbatim from the source; nothing is generated.
  * Keys you set by hand (title, authors, venue, ...) are kept unless you pass --force.
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "publications.json"
PAPERS_DIR = ROOT / "papers"
SITE_URL = "https://ahmedelbadawy.engineer"
STATIC_PAGES = ["", "research.html", "publications.html", "talks.html", "cv.html", "projects.html"]
PAGE_TYPES = {"journal", "proceedings"}  # types that get their own Scholar-indexable page

USER_AGENT = "academic-site-publications-updater/1.0 (+https://github.com/ahmedelbadawy/ahmedelbadawy.github.io)"


# --------------------------------------------------------------------------- HTTP helpers

def get_json(url, mailto=None, retries=3):
    if mailto:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}mailto={urllib.parse.quote(mailto)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    return None


def crossref_work(doi, mailto=None):
    data = get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/"), mailto)
    return data.get("message") if data else None


def crossref_search_title(title, mailto=None, rows=5):
    q = urllib.parse.urlencode({"query.bibliographic": title, "rows": rows,
                                "select": "DOI,title,container-title,issued,type,author"})
    data = get_json("https://api.crossref.org/works?" + q, mailto)
    return (data or {}).get("message", {}).get("items", [])


def openalex_abstract(doi, mailto=None):
    data = get_json("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/"), mailto)
    if not data or not data.get("abstract_inverted_index"):
        return None, None
    pos = {}
    for word, idxs in data["abstract_inverted_index"].items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos)), data.get("id")


# --------------------------------------------------------------------------- formatting helpers

def norm_title(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def clean_jats(s):
    """Crossref abstracts are JATS XML; strip tags and the leading 'Abstract' heading."""
    if not s:
        return ""
    s = re.sub(r"<jats:title>\s*Abstract\s*</jats:title>", "", s, flags=re.I)
    s = re.sub(r"</jats:p>\s*<jats:p>", "\n\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n\s*\n\s*", "\n\n", s)
    return s.strip()


def initials(given):
    parts = re.split(r"[\s\-\.]+", given or "")
    return "".join(p[0].upper() for p in parts if p)


def format_author(a):
    family = a.get("family") or a.get("name") or ""
    return f"{family} {initials(a.get('given', ''))}".strip()


def date_from(msg):
    for key in ("published-print", "published-online", "issued", "published"):
        parts = (msg.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            p = parts[0]
            return "-".join([str(p[0])] + [f"{x:02d}" for x in p[1:3]]), p[0]
    return None, None


# --------------------------------------------------------------------------- update logic

def apply_crossref(pub, msg, force):
    """Fill fields on `pub` from a Crossref record. Returns list of changed keys."""
    changed = []

    def put(key, value):
        if value in (None, "", []):
            return
        if force or not pub.get(key):
            if pub.get(key) != value:
                pub[key] = value
                changed.append(key)

    title = (msg.get("title") or [None])[0]
    put("title", title)
    if msg.get("author"):
        put("authors", [format_author(a) for a in msg["author"]])
    put("venue", (msg.get("container-title") or [None])[0])
    put("volume", msg.get("volume"))
    put("issue", msg.get("issue"))
    put("article", msg.get("article-number") or msg.get("page"))
    date, year = date_from(msg)
    put("date", date)
    put("year", year)
    abstract = clean_jats(msg.get("abstract"))
    if abstract and (force or not pub.get("abstract")):
        if pub.get("abstract") != abstract:
            pub["abstract"] = abstract
            pub["abstract_source"] = "Crossref"
            changed.append("abstract")
    return changed


def update(data, args):
    pubs = data.get("publications", [])
    for pub in pubs:
        pid = pub.get("id", "?")
        if pub.get("type") == "preparation":
            continue

        if not pub.get("doi") and args.find_dois and pub.get("title"):
            print(f"[{pid}] searching Crossref by title…")
            hits = crossref_search_title(pub["title"], args.mailto)
            exact = [h for h in hits if norm_title((h.get("title") or [""])[0]) == norm_title(pub["title"])]
            if len(exact) == 1:
                pub["doi"] = exact[0]["DOI"]
                print(f"    exact title match → doi {pub['doi']}")
            else:
                print("    no unique exact match; candidates (add the right DOI by hand):")
                for h in hits[:5]:
                    t = " ".join((h.get("title") or [""])[0].split())
                    c = " ".join((h.get("container-title") or [""])[0].split())
                    print(f"      {h.get('DOI')}  {t}  [{c}]")

        doi = pub.get("doi")
        if not doi:
            print(f"[{pid}] no DOI, skipped")
            continue
        if pub.get("skip_crossref"):
            print(f"[{pid}] skip_crossref is set, skipped")
            continue

        msg = crossref_work(doi, args.mailto)
        if not msg:
            print(f"[{pid}] DOI {doi} not found on Crossref")
            continue
        cr_title = (msg.get("title") or [""])[0]
        if pub.get("title") and norm_title(cr_title) != norm_title(pub["title"]):
            print(f"[{pid}] WARNING: Crossref title differs: {cr_title!r}")
        changed = apply_crossref(pub, msg, args.force)

        if not pub.get("abstract"):
            if args.openalex and not pub.get("abstract_unverified"):
                text, oa_id = openalex_abstract(doi, args.mailto)
                if text:
                    pub["abstract_unverified"] = text
                    pub["abstract_unverified_source"] = f"OpenAlex ({oa_id}), not checked against the publisher page"
                    changed.append("abstract_unverified")
            if not pub.get("abstract"):
                print(f"[{pid}] no abstract available from Crossref; paste it by hand (\"abstract\")")

        print(f"[{pid}] updated: {', '.join(changed)}" if changed else f"[{pid}] up to date")
        time.sleep(0.3)  # be gentle with the API


# --------------------------------------------------------------------------- paper pages

def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def scholar_author(a):
    """'Mohamed AE*' -> 'Mohamed, A. E.'"""
    a = a.rstrip("*").strip()
    m = re.match(r"^(.*\S)\s+([A-Z]{1,4})$", a)
    if not m:
        return a
    return f"{m.group(1)}, {' '.join(c + '.' for c in m.group(2))}"


def bibtex(pub):
    kind = "article" if pub.get("type") == "journal" else "inproceedings"
    authors = " and ".join(scholar_author(a) for a in pub.get("authors", []))
    fields = [("title", pub.get("title")), ("author", authors)]
    fields.append(("journal" if kind == "article" else "booktitle", pub.get("venue")))
    for k in ("volume", "issue"):
        if pub.get(k):
            fields.append(("number" if k == "issue" else k, pub[k]))
    if pub.get("article"):
        fields.append(("pages", pub["article"]))
    fields += [("year", pub.get("year")), ("doi", pub.get("doi"))]
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields if v)
    return f"@{kind}{{{pub['id']},\n{body}\n}}"


def paper_page(pub, me):
    title = pub["title"]
    authors = pub.get("authors", [])
    url = f"{SITE_URL}/papers/{pub['id']}.html"
    date = str(pub.get("date") or pub.get("year") or "")
    meta = [f'<meta name="citation_title" content="{esc(title)}" />']
    meta += [f'<meta name="citation_author" content="{esc(scholar_author(a))}" />' for a in authors]
    if date:
        meta.append(f'<meta name="citation_publication_date" content="{esc(date.replace("-", "/"))}" />')
    venue_key = "citation_journal_title" if pub.get("type") == "journal" else "citation_conference_title"
    if pub.get("venue"):
        meta.append(f'<meta name="{venue_key}" content="{esc(pub["venue"])}" />')
    for key, field in (("citation_volume", "volume"), ("citation_issue", "issue"), ("citation_firstpage", "article"), ("citation_doi", "doi")):
        if pub.get(field):
            meta.append(f'<meta name="{key}" content="{esc(pub[field])}" />')
    if pub.get("url") and re.search(r"\.pdf($|\?)", pub["url"], re.I):
        meta.append(f'<meta name="citation_pdf_url" content="{esc(pub["url"])}" />')
    meta.append(f'<meta name="citation_abstract_html_url" content="{esc(url)}" />')

    def author_html(a):
        return f"<strong>{esc(a)}</strong>" if a.rstrip("*") in me else esc(a)

    venue = f"<em>{esc(pub.get('venue', ''))}</em>"
    if pub.get("volume"):
        venue += f" {esc(pub['volume'])}" + (f"({esc(pub['issue'])})" if pub.get("issue") else "")
    if pub.get("article"):
        venue += (": " if pub.get("volume") else ", ") + esc(pub["article"])
    if pub.get("year"):
        venue += f" ({esc(pub['year'])})"

    links = []
    if pub.get("doi"):
        links.append(f'<a href="https://doi.org/{esc(pub["doi"])}" target="_blank" rel="noopener"><i class="ai ai-doi"></i> {esc(pub["doi"])}</a>')
    if pub.get("url") and (not pub.get("doi") or pub["doi"] not in pub["url"]):
        links.append(f'<a href="{esc(pub["url"])}" target="_blank" rel="noopener"><i class="fa-solid fa-arrow-up-right-from-square"></i> Publisher</a>')
    links.append(f'<a href="../publications.html#{esc(pub["id"])}"><i class="fa-solid fa-list"></i> All publications</a>')

    abstract = (f'<h3 class="sub">Abstract</h3><div class="abstract-body">{esc(pub["abstract"])}</div>'
                if pub.get("abstract") else "<!-- TODO: paste abstract in publications.json and re-run --pages -->")
    description = pub.get("abstract") or title
    if len(description) > 300:
        description = description[:300].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    note = f'<div class="pub-note">{esc(pub["note"])}</div>' if pub.get("note") else ""

    return f"""<!DOCTYPE html>
<html lang="en" data-root="../">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<!-- Generated by scripts/update_publications.py --pages. Edit publications.json, not this file. -->
<title>{esc(title)} · Ahmed Elbadawy Mohamed</title>
<meta name="description" content="{esc(description)}" />
<link rel="canonical" href="{esc(url)}" />
{chr(10).join(meta)}
<meta property="og:type" content="article" />
<meta property="og:title" content="{esc(title)}" />
<meta property="og:description" content="{esc(description)}" />
<meta property="og:url" content="{esc(url)}" />
<meta property="og:image" content="{SITE_URL}/figs/me.jpg" />
<meta name="theme-color" content="#0a0c11" />
<link rel="icon" href="../favicon.svg" type="image/svg+xml" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/academicons/1.9.4/css/academicons.min.css" />
<link rel="stylesheet" href="../assets/css/style.css" />
<script src="../assets/js/site.js"></script>
</head>
<body data-page="publications">
<header id="site-header"></header>
<main id="main">
  <div class="page-head">
    <div class="wrap">
      <div class="eyebrow">publication</div>
      <h1 style="font-size:clamp(28px,4.5vw,44px)">{esc(title)}</h1>
      <p class="pub-authors" style="font-size:15px">{", ".join(author_html(a) for a in authors)}</p>
      <p class="pub-venue" style="font-size:15px">{venue}</p>
      {note}
      <div class="pub-links" style="margin-top:16px">{"".join(links)}</div>
    </div>
  </div>
  <section>
    <div class="wrap">
      {abstract}
      <h3 class="sub">Cite</h3>
      <pre class="abstract-body" style="white-space:pre-wrap;font-family:var(--mono);font-size:13px">{esc(bibtex(pub))}</pre>
    </div>
  </section>
</main>
<footer id="site-footer" class="site-footer"></footer>
</body>
</html>
"""


DATA_JS = ROOT / "assets" / "js" / "publications-data.js"


def write_data_js(data, dry_run):
    """Embedded copy of publications.json so publications.html also works when opened from disk
    (browsers block fetch() on file:// pages). On the live site the page reads publications.json."""
    body = json.dumps(data, ensure_ascii=False, indent=2)
    text = ("/* Generated by scripts/update_publications.py from publications.json. Do not edit by hand. */\n"
            f"window.PUBLICATIONS_DATA = {body};\n")
    old = DATA_JS.read_text(encoding="utf-8") if DATA_JS.exists() else ""
    if text != old:
        if not dry_run:
            DATA_JS.write_text(text, encoding="utf-8")
        print("assets/js/publications-data.js: " + ("would update" if dry_run else "updated"))


def build_pages(data, dry_run):
    me = data.get("me", [])
    PAPERS_DIR.mkdir(exist_ok=True)
    built = []
    for pub in data.get("publications", []):
        if pub.get("type") not in PAGE_TYPES or not pub.get("authors") or not pub.get("title"):
            if pub.get("page"):
                pub.pop("page")
            continue
        rel = f"papers/{pub['id']}.html"
        pub["page"] = rel
        built.append(rel)
        if not dry_run:
            (ROOT / rel).write_text(paper_page(pub, me), encoding="utf-8")
        print(f"[{pub['id']}] page → {rel}")

    keep = {Path(p).name for p in built}
    for f in PAPERS_DIR.glob("*.html"):
        if f.name not in keep:
            print(f"    note: {f.relative_to(ROOT)} is no longer generated (delete it if unwanted)")

    urls = [f"{SITE_URL}/{p}" for p in STATIC_PAGES] + [f"{SITE_URL}/{p}" for p in built]
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + "".join(f"  <url><loc>{esc(u)}</loc></url>\n" for u in urls)
               + "</urlset>\n")
    if not dry_run:
        (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print(f"sitemap.xml: {len(urls)} URLs")


# --------------------------------------------------------------------------- main

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--find-dois", action="store_true", help="look up DOIs by title for entries without one")
    ap.add_argument("--force", action="store_true", help="overwrite existing fields with Crossref values")
    ap.add_argument("--openalex", action="store_true", help="store OpenAlex abstract in abstract_unverified when Crossref has none")
    ap.add_argument("--pages", action="store_true", help="build papers/<id>.html and sitemap.xml")
    ap.add_argument("--offline", action="store_true", help="skip all network lookups (e.g. with --pages)")
    ap.add_argument("--mailto", help="contact email for Crossref's polite pool")
    ap.add_argument("--dry-run", action="store_true", help="print changes without writing files")
    args = ap.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))
    before = json.dumps(data, ensure_ascii=False, sort_keys=True)

    if not args.offline:
        update(data, args)
    if args.pages:
        build_pages(data, args.dry_run)

    write_data_js(data, args.dry_run)

    after = json.dumps(data, ensure_ascii=False, sort_keys=True)
    if after == before:
        print("publications.json: no changes")
    elif args.dry_run:
        print("publications.json: changes found (dry run, not written)")
    else:
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("publications.json: written")


if __name__ == "__main__":
    main()
