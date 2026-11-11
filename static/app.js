(function () {
  var MOON = '<svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';
  var SUN = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4" fill="currentColor"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';

  var btn = document.getElementById("theme-btn");
  if (!btn) return;

  function isDark() {
    return document.documentElement.getAttribute("data-bs-theme") === "dark";
  }
  function paint() {
    btn.innerHTML = isDark() ? SUN : MOON;
    btn.setAttribute("aria-label", isDark() ? "Switch to light mode" : "Switch to dark mode");
  }

  btn.onclick = function () {
    var next = isDark() ? "light" : "dark";
    document.documentElement.setAttribute("data-bs-theme", next);
    try { localStorage.setItem("theme", next); } catch (e) {}
    paint();
  };
  paint();
})();

(function () {
  var list = document.getElementById("student-list");
  if (!list) return;
  var q = document.getElementById("student-search");
  var chips = document.querySelectorAll(".chip");
  var none = document.getElementById("no-match");
  var level = "all";

  function apply() {
    var term = q.value.trim().toLowerCase();
    var shown = 0;
    list.querySelectorAll(".srow").forEach(function (row) {
      var ok = (level === "all" || row.dataset.level === level) &&
               row.dataset.name.indexOf(term) > -1;
      row.style.display = ok ? "" : "none";
      if (ok) shown++;
    });
    none.classList.toggle("d-none", shown > 0);
  }

  q.addEventListener("input", apply);
  chips.forEach(function (c) {
    c.addEventListener("click", function () {
      level = c.dataset.level;
      chips.forEach(function (x) { x.classList.toggle("on", x === c); });
      apply();
    });
  });
})();