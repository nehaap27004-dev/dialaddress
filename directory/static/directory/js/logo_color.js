(function () {
  var input = document.querySelector('input[name="logo_bg_color"]');
  if (!input) return;

  var DEFAULT = "#ffffff";
  var nameInput = document.getElementById("id_name");

  var wrap = document.createElement("div");
  wrap.style.cssText = "display:flex;align-items:center;gap:12px;margin-top:8px;flex-wrap:wrap";

  var box = document.createElement("span");
  box.setAttribute("aria-hidden", "true");
  box.title = "Preview (initials are shown when there is no logo)";
  box.style.cssText = "display:inline-grid;place-items:center;width:56px;height:56px;" +
    "border:1px solid #d0d5dd;border-radius:10px;font-weight:700;font-size:20px;letter-spacing:.5px";

  var reset = document.createElement("button");
  reset.type = "button";
  reset.textContent = "Reset to white";
  reset.style.cssText = "border:1px solid #d0d5dd;background:#fff;color:#1b2430;border-radius:8px;" +
    "padding:8px 14px;font:inherit;font-size:14px;cursor:pointer";

  wrap.appendChild(box);
  wrap.appendChild(reset);
  input.insertAdjacentElement("afterend", wrap);

  function initials(name) {
    var words = (name || "").trim().split(/\s+/).filter(function (w) {
      return /^[\p{L}\p{N}]/u.test(w);
    });
    if (!words.length) return "?";
    if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
    return (words[0].charAt(0) + words[1].charAt(0)).toUpperCase();
  }

  function textColor(hex) {
    var n = parseInt(hex.slice(1), 16);
    var r = n >> 16, g = (n >> 8) & 255, b = n & 255;
    return (r * 299 + g * 587 + b * 114) / 1000 > 150 ? "#1b2430" : "#ffffff";
  }

  function paint() {
    var color = /^#[0-9a-f]{6}$/i.test(input.value) ? input.value : DEFAULT;
    box.style.background = color;
    box.style.color = textColor(color);
    box.textContent = initials(nameInput ? nameInput.value : "");
    var isDefault = color.toLowerCase() === DEFAULT;
    reset.disabled = isDefault;
    reset.style.opacity = isDefault ? ".45" : "1";
    reset.style.cursor = isDefault ? "default" : "pointer";
  }

  input.addEventListener("input", paint);
  if (nameInput) nameInput.addEventListener("input", paint);
  reset.addEventListener("click", function () { input.value = DEFAULT; paint(); });
  paint();
})();