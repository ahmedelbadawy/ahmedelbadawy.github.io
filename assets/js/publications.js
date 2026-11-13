/* Renders publications.json into #pub-list on publications.html. */
(function () {
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function authorsHTML(list, me) {
    return list.map(function (a) {
      var bare = a.replace(/\*+$/, "");
      return me.indexOf(bare) !== -1 ? "<strong>" + esc(a) + "</strong>" : esc(a);
    }).join(", ");
  }

  function venueHTML(p) {
    if (!p.venue) return "";
    var s = "<em>" + esc(p.venue) + "</em>";
    if (p.volume) s += " " + esc(p.volume) + (p.issue ? "(" + esc(p.issue) + ")" : "");
    if (p.article) s += (p.volume ? ": " : ", ") + esc(p.article);
    if (p.year) s += " (" + esc(p.year) + ")";
    return s;
  }

  function pubHTML(p, me) {
    var h = '<article class="pub" id="' + esc(p.id) + '">';
    h += '<div class="pub-title">' + esc(p.title) + "</div>";
    if (p.authors && p.authors.length) h += '<div class="pub-authors">' + authorsHTML(p.authors, me) + "</div>";
    var v = venueHTML(p);
    if (v) h += '<div class="pub-venue">' + v + "</div>";
    if (p.note) h += '<div class="pub-note">' + esc(p.note) + "</div>";

    var links = [];
    if (p.doi) links.push('<a href="https://doi.org/' + esc(p.doi) + '" target="_blank" rel="noopener"><i class="ai ai-doi"></i> ' + esc(p.doi) + "</a>");
    if (p.url && (!p.doi || p.url.indexOf(p.doi) === -1)) {
      var isPdf = /\.pdf($|\?)/i.test(p.url);
      links.push('<a href="' + esc(p.url) + '" target="_blank" rel="noopener"><i class="fa-solid ' + (isPdf ? "fa-file-pdf" : "fa-arrow-up-right-from-square") + '"></i> ' + (isPdf ? "PDF" : "Publisher") + "</a>");
    }
    if (p.page) links.push('<a href="' + esc(p.page) + '"><i class="fa-regular fa-file-lines"></i> Paper page</a>');
    (p.links || []).forEach(function (l) {
      links.push('<a href="' + esc(l.url) + '" target="_blank" rel="noopener"><i class="fa-solid fa-arrow-up-right-from-square"></i> ' + esc(l.label) + "</a>");
    });

    var abs = "";
    if (p.abstract) {
      abs = '<details class="abstract"><summary>Abstract</summary><div class="abstract-body">' + esc(p.abstract) + "</div></details>";
    } else if (p.type !== "preparation") {
      abs = "<!-- TODO: paste abstract for " + esc(p.id) + " in publications.json -->";
    }

    if (links.length || p.abstract) h += '<div class="pub-links">' + links.join("") + abs + "</div>";
    else h += abs;
    return h + "</article>";
  }

  function render(data) {
    var me = data.me || [];
    var out = "";
    (data.sections || []).forEach(function (sec) {
      var items = (data.publications || []).filter(function (p) { return p.type === sec.key; });
      if (!items.length) return;
      items.sort(function (a, b) {
        var da = String(a.date || a.year || ""), db = String(b.date || b.year || "");
        return da < db ? 1 : da > db ? -1 : 0;
      });
      out += '<h3 class="sub" id="sec-' + esc(sec.key) + '">' + esc(sec.title) + "</h3>";
      out += '<div class="timeline">' + items.map(function (p) { return pubHTML(p, me); }).join("") + "</div>";
    });
    return out;
  }

  function focusHash() {
    if (!location.hash) return;
    var el = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!el) return;
    el.classList.add("target");
    var d = el.querySelector("details.abstract");
    if (d) d.open = true;
    el.scrollIntoView();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var box = document.getElementById("pub-list");
    if (!box) return;
    var root = document.documentElement.getAttribute("data-root") || "";
    var show = function (data) { box.innerHTML = render(data); focusHash(); };
    var fallback = function () {
      // Embedded copy (assets/js/publications-data.js), used when fetch is unavailable, e.g. file://
      if (window.PUBLICATIONS_DATA) return show(window.PUBLICATIONS_DATA);
      box.innerHTML = '<p class="pub-empty">The publication list could not be loaded. ' +
        'See the <a class="inline" href="' + (window.PROFILE ? PROFILE.scholar : "#") + '" target="_blank" rel="noopener">full list on Google Scholar</a>.</p>';
    };
    if (location.protocol === "file:") return fallback();
    fetch(root + "publications.json", { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(show)
      .catch(fallback);
  });
})();
