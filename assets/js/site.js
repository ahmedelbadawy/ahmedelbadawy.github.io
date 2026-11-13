/* =====================================================================
   Shared site script: theme, navigation bar, footer/contact.
   Loaded in <head> on every page. To change a profile link or a nav item,
   edit PROFILE / NAV below — every page picks it up.
   ===================================================================== */

var PROFILE = {
  name: "Ahmed Elbadawy Mohamed",
  email: "aelbada@uwo.ca",
  scholar: "https://scholar.google.ca/citations?user=GBvaTfAAAAAJ&hl=en",
  orcid: "https://orcid.org/0009-0002-9824-7951",
  researchgate: "https://www.researchgate.net/profile/Ahmed-Mohamed-835",
  github: "https://github.com/ahmedelbadawy",
  linkedin: "https://www.linkedin.com/in/ahmed-elbadawy-m-0b6984180/"
};

var NAV = [
  { key: "home",         label: "Home",           href: "index.html" },
  { key: "research",     label: "Research",       href: "research.html" },
  { key: "publications", label: "Publications",   href: "publications.html" },
  { key: "talks",        label: "Talks &amp; Awards", href: "talks.html" },
  { key: "cv",           label: "CV",             href: "cv.html" },
  { key: "projects",     label: "Projects",       href: "projects.html" },
  { key: "contact",      label: "Contact",        href: "#contact" }
];

/* ---- Theme: apply before first paint to avoid a flash ---- */
(function () {
  var saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) {}
  if (saved === "light" || saved === "dark") {
    document.documentElement.setAttribute("data-theme", saved);
  }
})();

function currentTheme() {
  var t = document.documentElement.getAttribute("data-theme");
  if (t) return t;
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function socialLinksHTML() {
  return [
    ['<i class="ai ai-google-scholar"></i>', PROFILE.scholar, "Google Scholar"],
    ['<i class="ai ai-orcid"></i>', PROFILE.orcid, "ORCID"],
    ['<i class="ai ai-researchgate"></i>', PROFILE.researchgate, "ResearchGate"],
    ['<i class="fa-brands fa-github"></i>', PROFILE.github, "GitHub"],
    ['<i class="fa-brands fa-linkedin-in"></i>', PROFILE.linkedin, "LinkedIn"],
    ['<i class="fa-solid fa-envelope"></i>', "mailto:" + PROFILE.email, "Email"]
  ].map(function (s) {
    var ext = s[1].indexOf("mailto:") === 0 ? "" : ' target="_blank" rel="noopener"';
    return '<a href="' + s[1] + '"' + ext + ' aria-label="' + s[2] + '" title="' + s[2] + '">' + s[0] + "</a>";
  }).join("");
}

function buildHeader(root, page) {
  var links = NAV.map(function (n) {
    var href = n.href.charAt(0) === "#" ? n.href : root + n.href;
    var cur = n.key === page ? ' aria-current="page"' : "";
    return '<li><a href="' + href + '"' + cur + ">" + n.label + "</a></li>";
  }).join("");
  return (
    '<a class="skip-link" href="#main">Skip to content</a>' +
    '<nav class="site-nav" aria-label="Main">' +
      '<div class="wrap">' +
        '<a class="logo" href="' + root + 'index.html">Ahmed E. Mohamed</a>' +
        '<div class="nav-right">' +
          '<ul class="nav-links" id="nav-links">' + links + "</ul>" +
          '<button class="icon-btn theme-toggle" type="button" aria-label="Toggle light/dark theme"></button>' +
          '<button class="icon-btn menu-toggle" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="nav-links"><i class="fa-solid fa-bars"></i></button>' +
        "</div>" +
      "</div>" +
    "</nav>"
  );
}

function buildFooter(root) {
  var year = new Date().getFullYear();
  return (
    '<div class="wrap" id="contact">' +
      '<div class="footer-grid">' +
        "<div>" +
          '<div class="section-label">contact</div>' +
          "<h2>Get in touch</h2>" +
          "<p>I'm happy to hear about research collaborations, speaking opportunities, or questions about my work. " +
          "Email is the best way to reach me.</p>" +
          '<div class="contact-links">' +
            '<a class="btn primary" href="mailto:' + PROFILE.email + '"><i class="fa-solid fa-envelope"></i> ' + PROFILE.email + "</a>" +
          "</div>" +
        "</div>" +
        "<div>" +
          '<p class="affil"><strong>' + PROFILE.name + "</strong><br>" +
          "PhD Candidate, Medical Biophysics<br>" +
          "Robarts Research Institute<br>" +
          "Western University, London, ON, Canada</p>" +
          '<div class="social" style="margin-top:18px">' + socialLinksHTML() + "</div>" +
        "</div>" +
      "</div>" +
      '<div class="footer-meta">' +
        "<span>© " + year + " " + PROFILE.name + ".</span>" +
        '<span><a href="' + root + 'cv.html">CV</a> · <a href="' + PROFILE.scholar + '" target="_blank" rel="noopener">Google Scholar</a></span>' +
      "</div>" +
    "</div>"
  );
}

function setThemeIcon(btn) {
  var t = currentTheme();
  btn.innerHTML = t === "light" ? '<i class="fa-solid fa-moon"></i>' : '<i class="fa-solid fa-sun"></i>';
  btn.setAttribute("aria-label", t === "light" ? "Switch to dark theme" : "Switch to light theme");
  btn.title = btn.getAttribute("aria-label");
}

document.addEventListener("DOMContentLoaded", function () {
  var root = document.documentElement.getAttribute("data-root") || "";
  var page = document.body.getAttribute("data-page") || "";

  var header = document.getElementById("site-header");
  if (header) header.innerHTML = buildHeader(root, page);
  var footer = document.getElementById("site-footer");
  if (footer) footer.innerHTML = buildFooter(root);

  // Any element with data-social gets the icon row (e.g. on the home page)
  Array.prototype.forEach.call(document.querySelectorAll("[data-social]"), function (el) {
    el.innerHTML = socialLinksHTML();
  });

  // Theme toggle
  var tbtn = document.querySelector(".theme-toggle");
  if (tbtn) {
    setThemeIcon(tbtn);
    tbtn.addEventListener("click", function () {
      var next = currentTheme() === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
      setThemeIcon(tbtn);
    });
  }

  // Mobile menu
  var mbtn = document.querySelector(".menu-toggle");
  var list = document.getElementById("nav-links");
  if (mbtn && list) {
    var setOpen = function (open) {
      list.classList.toggle("open", open);
      mbtn.setAttribute("aria-expanded", open ? "true" : "false");
      mbtn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      mbtn.innerHTML = open ? '<i class="fa-solid fa-xmark"></i>' : '<i class="fa-solid fa-bars"></i>';
    };
    mbtn.addEventListener("click", function () { setOpen(!list.classList.contains("open")); });
    list.addEventListener("click", function (e) { if (e.target.tagName === "A") setOpen(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") setOpen(false); });
  }
});
