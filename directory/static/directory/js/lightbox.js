(function () {
  var lb = document.getElementById("lb");
  if (!lb) return;

  var $ = function (id) { return document.getElementById(id); };
  var img = $("lbImg");
  var items = [];
  var index = 0;
  var lastFocus = null;

  function setLink(el, href) {
    if (href) { el.href = href; el.hidden = false; }
    else { el.removeAttribute("href"); el.hidden = true; }
  }

  function render() {
    var d = items[index].dataset;
    img.src = d.src;
    img.alt = d.heading || d.caption || d.name;
    $("lbName").textContent = d.name;
    $("lbTick").hidden = !d.verified;
    $("lbCategory").textContent = d.category;
    $("lbRating").textContent = "\u2605 " + d.rating + " (" + d.reviews + " reviews)";
    $("lbHeading").textContent = d.heading || "";
    $("lbHeading").hidden = !d.heading;
    $("lbCaption").textContent = d.caption || "";
    $("lbCaption").hidden = !d.caption;
    $("lbAddress").textContent = d.address;
    setLink($("lbCall"), d.phone ? "tel:" + d.phone : "");
    setLink($("lbWhatsapp"), d.whatsapp);
    setLink($("lbMap"), d.maps);
    $("lbView").href = d.url;

    var many = items.length > 1;
    $("lbCount").textContent = (index + 1) + " / " + items.length;
    $("lbCount").hidden = !many;
    lb.querySelector(".lb-prev").hidden = !many;
    lb.querySelector(".lb-next").hidden = !many;
  }

  function go(step) {
    index = (index + step + items.length) % items.length;
    render();
  }

  function open(i) {
    index = i;
    render();
    lastFocus = document.activeElement;
    lb.hidden = false;
    lb.setAttribute("aria-hidden", "false");
    document.body.classList.add("lb-open");
    lb.querySelector(".lb-close").focus();
  }

  function close() {
    lb.hidden = true;
    lb.setAttribute("aria-hidden", "true");
    document.body.classList.remove("lb-open");
    img.removeAttribute("src");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  // Open: any element with data-lightbox. Photos inside the same
  // [data-lightbox-group] container become one slideshow.
  document.addEventListener("click", function (e) {
    var trigger = e.target.closest("[data-lightbox]");
    if (trigger) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return; // allow "open in new tab"
      e.preventDefault();
      var group = trigger.closest("[data-lightbox-group]") || document;
      items = Array.prototype.slice.call(group.querySelectorAll("[data-lightbox]"));
      open(items.indexOf(trigger));
      return;
    }
    if (e.target.closest("[data-lb-close]")) close();
  });

  lb.querySelector(".lb-prev").addEventListener("click", function () { go(-1); });
  lb.querySelector(".lb-next").addEventListener("click", function () { go(1); });

  // Keyboard: Esc, arrows, and keep Tab inside the window
  document.addEventListener("keydown", function (e) {
    if (lb.hidden) return;
    if (e.key === "Escape") {
      close();
    } else if (e.key === "ArrowLeft" && items.length > 1) {
      go(-1);
    } else if (e.key === "ArrowRight" && items.length > 1) {
      go(1);
    } else if (e.key === "Tab") {
      var f = Array.prototype.filter.call(
        lb.querySelectorAll("a[href], button"),
        function (el) { return !el.hidden && el.getClientRects().length; }
      );
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  // Swipe left / right on phones
  var startX = null;
  var media = lb.querySelector(".lb-media");
  media.addEventListener("touchstart", function (e) { startX = e.touches[0].clientX; }, { passive: true });
  media.addEventListener("touchend  ", function (e) {
    if (startX === null || items.length < 2) return;
    var dx = e.changedTouches[0].clientX - startX;
    startX = null;
    if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1);
  });
})();