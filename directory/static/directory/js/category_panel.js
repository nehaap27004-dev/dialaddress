(function () {
  var panel = document.getElementById("catPanel");
  var backdrop = document.getElementById("catPanelBackdrop");
  if (!panel || !backdrop) return;

  var closeBtn = panel.querySelector(".cpanel-close");
  var lastFocus = null;

  function setOpen(isOpen) {
    panel.classList.toggle("is-open", isOpen);
    backdrop.classList.toggle("is-open", isOpen);
    panel.setAttribute("aria-hidden", isOpen ? "false" : "true");
    document.body.classList.toggle("cpanel-open", isOpen);

    if (isOpen) {
      lastFocus = document.activeElement;
      setTimeout(function () { closeBtn.focus(); }, 60); // wait for the slide-in to start
    } else if (lastFocus && lastFocus.focus) {
      lastFocus.focus();
    }
  }

  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-cpanel-open]")) {
      e.preventDefault();
      setOpen(true);
    } else if (e.target.closest("[data-cpanel-close]")) {
      setOpen(false);
    }
  });

  document.addEventListener("keydown", function (e) {
    if (!panel.classList.contains("is-open")) return;
    if (e.key === "Escape") {
      setOpen(false);
    } else if (e.key === "Tab") {  // keep Tab inside the panel
      var items = panel.querySelectorAll("a[href], button");
      if (!items.length) return;
      var first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
})();