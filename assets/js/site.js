/* peaty.scot — age notice + client-side explore filtering. No dependencies. */
(function () {
  "use strict";

  /* ---- age notice: dismissible, stored locally, never blocks content ---- */
  var notice = document.getElementById("age-notice");
  if (notice) {
    var KEY = "peaty.age-ack";
    var acked = false;
    try { acked = localStorage.getItem(KEY) === "1"; } catch (e) { acked = false; }
    if (!acked) {
      notice.hidden = false;
      var ok = document.getElementById("age-notice-ok");
      if (ok) {
        ok.addEventListener("click", function () {
          notice.hidden = true;
          try { localStorage.setItem(KEY, "1"); } catch (e) { /* private mode */ }
        });
      }
    }
  }

  /* ---- explore ---- */
  var root = document.querySelector("[data-explore]");
  if (!root) return;

  var q = document.getElementById("q");
  var results = document.getElementById("results");
  var count = document.getElementById("result-count");
  var reset = document.getElementById("f-reset");
  var selects = {
    kind: document.getElementById("f-kind"),
    country: document.getElementById("f-country"),
    region: document.getElementById("f-region"),
    flavour: document.getElementById("f-flavour")
  };
  var items = [];

  function titleCase(s) {
    return String(s).replace(/-/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function fillSelect(el, values) {
    values.sort().forEach(function (v) {
      var o = document.createElement("option");
      o.value = v;
      o.textContent = titleCase(v);
      el.appendChild(o);
    });
  }

  function buildFilters() {
    var sets = { kind: {}, country: {}, region: {}, flavour: {} };
    items.forEach(function (it) {
      if (it.kind) sets.kind[it.kind] = 1;
      if (it.country) sets.country[it.country] = 1;
      if (it.region) sets.region[it.region] = 1;
      (it.flavours || []).forEach(function (f) { sets.flavour[f] = 1; });
    });
    Object.keys(selects).forEach(function (k) {
      fillSelect(selects[k], Object.keys(sets[k]));
    });
  }

  function matches(it, term) {
    if (selects.kind.value && it.kind !== selects.kind.value) return false;
    if (selects.country.value && it.country !== selects.country.value) return false;
    if (selects.region.value && it.region !== selects.region.value) return false;
    if (selects.flavour.value && (it.flavours || []).indexOf(selects.flavour.value) === -1) return false;
    if (!term) return true;
    var hay = [it.title, it.desc, it.distillery, it.region, it.country]
      .concat(it.flavours || []).join(" ").toLowerCase();
    return term.split(/\s+/).every(function (t) { return hay.indexOf(t) !== -1; });
  }

  function render() {
    var term = (q.value || "").trim().toLowerCase();
    var hits = items.filter(function (it) { return matches(it, term); });

    results.textContent = "";
    var frag = document.createDocumentFragment();
    hits.forEach(function (it) {
      var li = document.createElement("li");
      li.className = "card";
      var a = document.createElement("a");
      a.href = it.url;

      var kind = document.createElement("span");
      kind.className = "card-kind";
      kind.textContent = it.kind;

      var title = document.createElement("span");
      title.className = "card-title";
      title.textContent = it.title;

      a.appendChild(kind);
      a.appendChild(title);

      var bits = [];
      if (it.abv) bits.push(it.abv + "% ABV");
      if (it.age) bits.push(it.age + " yo");
      if (it.region) bits.push(titleCase(it.region));
      if (bits.length) {
        var meta = document.createElement("span");
        meta.className = "card-meta";
        meta.textContent = bits.join(" · ");
        a.appendChild(meta);
      }
      if (it.desc) {
        var d = document.createElement("span");
        d.className = "card-desc";
        d.textContent = it.desc;
        a.appendChild(d);
      }
      li.appendChild(a);
      frag.appendChild(li);
    });
    results.appendChild(frag);
    count.textContent = hits.length + (hits.length === 1 ? " result" : " results");
  }

  fetch("/index.json")
    .then(function (r) {
      if (!r.ok) throw new Error("index " + r.status);
      return r.json();
    })
    .then(function (data) {
      items = data;
      buildFilters();
      render();
      q.addEventListener("input", render);
      Object.keys(selects).forEach(function (k) { selects[k].addEventListener("change", render); });
      reset.addEventListener("click", function () {
        q.value = "";
        Object.keys(selects).forEach(function (k) { selects[k].value = ""; });
        render();
      });
    })
    .catch(function () {
      count.textContent = "Could not load the index. Try browsing by section instead.";
    });
})();
