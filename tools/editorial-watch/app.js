(function () {
  "use strict";

  /* ---------- light / dark, shared with the profile page ---------- */
  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var cur = root.getAttribute("data-theme");
      if (!cur) {
        var prefersDark = window.matchMedia &&
          window.matchMedia("(prefers-color-scheme: dark)").matches;
        cur = prefersDark ? "dark" : "light";
      }
      var next = cur === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  /* ---------- scroll reveal (scroll-driven, never animation-driven) ---------- */
  var reveals = [].slice.call(document.querySelectorAll("[data-reveal]"));
  function showVisible() {
    var h = window.innerHeight || 800;
    for (var i = reveals.length - 1; i >= 0; i--) {
      if (reveals[i].getBoundingClientRect().top < h - 40) {
        reveals[i].classList.add("seen");
        reveals.splice(i, 1);
      }
    }
    if (!reveals.length) window.removeEventListener("scroll", showVisible);
  }
  showVisible();
  window.addEventListener("scroll", showVisible, { passive: true });
  window.addEventListener("resize", showVisible);
  setTimeout(function () {
    reveals.forEach(function (el) { el.classList.add("seen"); });
    reveals.length = 0;
  }, 1200);

  /* ---------- deadline countdowns ---------- */
  var today = new Date();
  today.setHours(0, 0, 0, 0);
  document.querySelectorAll("[data-due]").forEach(function (el) {
    var p = el.getAttribute("data-due").split("-");
    var d = new Date(+p[0], +p[1] - 1, +p[2]);
    var days = Math.round((d - today) / 86400000);
    if (isNaN(days)) return;
    var out = el.querySelector(".cd");
    if (!out) return;
    if (days < 0) { out.textContent = "Deadline has passed."; return; }
    out.textContent = days === 0 ? "Due today."
      : days === 1 ? "1 day left."
      : days + " days left (" + (days / 7 | 0) + " weeks).";
    if (days <= 45) {
      var due = el.querySelector(".due");
      if (due) due.classList.add("soon");
    }
  });

  /* ---------- the one filter state everything shares ---------- */
  var state = { theme: "", journal: "", q: "" };
  var items = [].slice.call(document.querySelectorAll(".item"));
  var list = document.getElementById("item-list");
  var countLine = document.getElementById("count-line");
  var chipBox = document.getElementById("active-chips");
  var search = document.getElementById("search");
  var chartCard = document.getElementById("slope-card");

  var THEME_LABEL = {};
  document.querySelectorAll(".dir").forEach(function (b) {
    THEME_LABEL[b.getAttribute("data-theme")] =
      b.querySelector("h3").textContent.trim();
  });

  function matches(el) {
    if (state.theme &&
        (" " + el.getAttribute("data-themes") + " ").indexOf(" " + state.theme + " ") < 0) return false;
    if (state.journal && el.getAttribute("data-journal") !== state.journal) return false;
    if (state.q && el.getAttribute("data-text").indexOf(state.q) < 0) return false;
    return true;
  }

  function chip(label, kind) {
    var s = document.createElement("span");
    s.className = "fchip";
    s.appendChild(document.createTextNode(label));
    var b = document.createElement("button");
    b.type = "button";
    b.setAttribute("aria-label", "Remove filter: " + label);
    b.textContent = "×";
    b.addEventListener("click", function () { set(kind, ""); });
    s.appendChild(b);
    return s;
  }

  function render() {
    var n = 0;
    items.forEach(function (el) {
      var ok = matches(el);
      el.hidden = !ok;
      if (ok) n++;
    });
    list.classList.toggle("is-empty", n === 0);
    countLine.textContent = n === items.length
      ? "Showing all " + items.length + " editorials, newest first."
      : "Showing " + n + " of " + items.length + " editorials.";

    chipBox.textContent = "";
    if (state.theme) chipBox.appendChild(chip(THEME_LABEL[state.theme] || state.theme, "theme"));
    if (state.journal) chipBox.appendChild(chip(state.journal, "journal"));

    document.querySelectorAll(".dir").forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-theme") === state.theme ? "true" : "false");
    });
    if (chartCard) {
      chartCard.classList.toggle("has-sel", !!state.theme);
      chartCard.querySelectorAll(".slope-g").forEach(function (g) {
        g.classList.toggle("on", g.getAttribute("data-theme") === state.theme);
      });
    }
    var clear = document.getElementById("clear-all");
    clear.hidden = !(state.theme || state.journal || state.q);
  }

  function set(kind, value, scroll) {
    state[kind] = state[kind] === value ? "" : value;
    render();
    if (scroll) {
      var top = document.getElementById("all").getBoundingClientRect().top + window.pageYOffset - 70;
      window.scrollTo({ top: top, behavior: "smooth" });
    }
  }

  document.querySelectorAll(".dir").forEach(function (b) {
    b.addEventListener("click", function () { set("theme", b.getAttribute("data-theme"), true); });
  });
  document.querySelectorAll("[data-pick-theme]").forEach(function (b) {
    b.addEventListener("click", function () { set("theme", b.getAttribute("data-pick-theme"), true); });
  });
  document.querySelectorAll("[data-pick-journal]").forEach(function (b) {
    b.addEventListener("click", function () { set("journal", b.getAttribute("data-pick-journal"), true); });
  });
  document.querySelectorAll(".cell").forEach(function (b) {
    if (b.getAttribute("data-v") === "0") return;
    b.addEventListener("click", function () {
      state.theme = b.getAttribute("data-theme");
      state.journal = b.getAttribute("data-journal");
      render();
      var top = document.getElementById("all").getBoundingClientRect().top + window.pageYOffset - 70;
      window.scrollTo({ top: top, behavior: "smooth" });
    });
  });
  if (chartCard) {
    chartCard.querySelectorAll(".slope-g").forEach(function (g) {
      g.addEventListener("click", function () { set("theme", g.getAttribute("data-theme"), true); });
    });
  }

  var t;
  search.addEventListener("input", function () {
    clearTimeout(t);
    t = setTimeout(function () {
      state.q = search.value.trim().toLowerCase();
      render();
    }, 140);
  });

  document.getElementById("clear-all").addEventListener("click", function () {
    state.theme = state.journal = state.q = "";
    search.value = "";
    render();
  });

  /* a ?theme= or ?journal= link lands pre-filtered */
  var qs = location.search;
  var mt = qs.match(/[?&]theme=([a-z]+)/);
  var mj = qs.match(/[?&]journal=([A-Za-z&]+)/);
  if (mt && THEME_LABEL[mt[1]]) state.theme = mt[1];
  if (mj) state.journal = decodeURIComponent(mj[1]);
  render();
})();
