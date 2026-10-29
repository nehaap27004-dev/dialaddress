(function () {
  var cat = document.getElementById("id_category");
  var sub = document.getElementById("id_subcategory");
  if (!cat || !sub || !window.SUBCATEGORY_URL) return;

  function fill(rows, keep) {
    sub.innerHTML = '<option value="">---------</option>';
    rows.forEach(function (r) {
      var o = document.createElement("option");
      o.value = r.id;
      o.textContent = r.name;
      if (String(r.id) === String(keep)) o.selected = true;
      sub.appendChild(o);
    });
  }

  function load(keep) {
    if (!cat.value) { fill([], ""); return; }
    fetch(window.SUBCATEGORY_URL + "?category=" + encodeURIComponent(cat.value))
      .then(function (r) { return r.json(); })
      .then(function (d) { fill(d.results, keep); });
  }

  cat.addEventListener("change", function () { load(""); });
  load(sub.value);
})();