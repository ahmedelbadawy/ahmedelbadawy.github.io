# ahmedelbadawy.engineer

Personal academic website of Ahmed Elbadawy Mohamed, served by GitHub Pages from the
`main` branch (repository root) at the custom domain in `CNAME`. It is plain HTML/CSS/JS
with no build step: push to `main` and the site updates.

## Layout

| File | What it is |
| --- | --- |
| `index.html` | Home / About |
| `research.html` | Research themes |
| `publications.html` | Publications, rendered from `publications.json` |
| `talks.html` | Talks & awards |
| `cv.html` | Education, experience, service; links to `resume.pdf` |
| `projects.html` | Side / course projects |
| `papers/*.html` | One page per paper with Google Scholar `citation_*` tags (generated) |
| `assets/css/style.css` | All styles (colour tokens for dark and light themes at the top) |
| `assets/js/site.js` | Shared nav bar, footer/contact, theme toggle, mobile menu. **Profile links and nav items are defined once at the top of this file.** |
| `assets/js/publications.js` | Renders `publications.json` on the publications page |
| `assets/js/publications-data.js` | Generated copy of `publications.json` used when a page is opened from disk |
| `publications.json` | All publications (the single source of truth) |
| `scripts/update_publications.py` | Refreshes `publications.json` from Crossref and builds `papers/` + `sitemap.xml` |
| `resume.pdf` | CV download |
| `.nojekyll` | Tells GitHub Pages to serve files as-is (no Jekyll processing) |

## Adding a publication

1. Add an object to `"publications"` in `publications.json`, at minimum:

   ```json
   {
     "id": "mohamed2027example",
     "type": "journal",
     "title": "…",
     "authors": ["Mohamed AE", "Gaede S", "Lee TY"],
     "doi": "10.xxxx/xxxxx"
   }
   ```

   `type` is one of `journal`, `proceedings`, `abstract`, `preparation`. Your name is bolded
   automatically when it matches an entry in `"me"`. Append `*` to an author for equal
   contribution and explain it in `"note"`.

2. Fill in the rest from Crossref and rebuild the per-paper pages:

   ```bash
   python scripts/update_publications.py --pages
   ```

   This fills in any missing venue, volume, issue, date and authors, and the abstract when
   Crossref has one. It never overwrites fields you already set unless you add `--force`.
   If Crossref has no abstract (common), paste it into `"abstract"` yourself from the publisher page.

Useful flags:

- `--find-dois` looks up a DOI by title for entries that don't have one.
- `--openalex` stores OpenAlex's abstract text in `abstract_unverified` when Crossref has none.
  Check it against the publisher page, then rename the key to `abstract`.
- `--dry-run` shows what would change without writing anything.
- `--offline --pages` rebuilds `papers/` and `sitemap.xml` without network access.
- `--mailto you@example.org` identifies you to Crossref's "polite pool" (faster, more reliable).

Google Scholar has no public API, so the site does not sync from it. Scholar is linked from
the publications page instead.

## Previewing locally

You can open the HTML files directly. Browsers block `fetch` on `file://` pages, so in that case
`publications.html` falls back to `assets/js/publications-data.js`, an embedded copy of
`publications.json` that the script regenerates on every run. After editing the JSON by hand, run
`python scripts/update_publications.py --offline --pages` so the local copy and paper pages stay in
sync. The live site always reads `publications.json` directly. To preview exactly as deployed:

```bash
python -m http.server 8000
# then open http://localhost:8000
```

## Editing tips

- **Profile links / nav:** edit `PROFILE` and `NAV` at the top of `assets/js/site.js`.
  The hero buttons on `index.html` and the Scholar/ORCID buttons on `publications.html`
  are plain HTML links, so update those too if a URL changes.
- **Research figures:** theme cards show a figure beside the text (`<figure class="theme-figure">`).
  The page loads a resized `figs/*-web.jpg` and links to the full-resolution original.
  The stroke theme still has a `<!-- TODO: figure -->` placeholder.
- **Colours:** the dark and light palettes are the CSS variables at the top of `style.css`.
