/* Zaheen's Cake — site script (no dependencies) */
(function () {
  "use strict";

  var PHONE_WA = "8801670236621";
  var data = Array.isArray(window.ZH_GALLERY) ? window.ZH_GALLERY : [];
  var CAT_LABEL = { custom: "Custom", birthday: "Birthday", event: "Event" };
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Year ---------- */
  var y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();

  /* ---------- Header shadow + mobile menu ---------- */
  var header = document.querySelector(".site-header");
  var menuBtn = document.getElementById("menuBtn");
  var nav = document.getElementById("nav");

  function onScroll() { header.classList.toggle("scrolled", window.scrollY > 8); }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  function setMenu(open) {
    nav.classList.toggle("open", open);
    menuBtn.setAttribute("aria-expanded", String(open));
    menuBtn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  }
  menuBtn.addEventListener("click", function () { setMenu(!nav.classList.contains("open")); });
  nav.addEventListener("click", function (e) { if (e.target.tagName === "A") setMenu(false); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") setMenu(false); });

  /* Highlight the nav link for the section in view */
  if ("IntersectionObserver" in window) {
    var links = Array.prototype.slice.call(nav.querySelectorAll("a"));
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        links.forEach(function (a) { a.classList.toggle("active", a.getAttribute("href") === "#" + en.target.id); });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    ["cakes", "order", "about", "contact"].forEach(function (id) {
      var el = document.getElementById(id); if (el) io.observe(el);
    });
  }

  /* ---------- Helpers ---------- */
  function byCat(cat) { return data.filter(function (d) { return d.cat === cat; }); }
  function bgUrl(el, item) { if (el && item) el.style.backgroundImage = "url('" + (item.thumb || item.src) + "')"; }

  /* ---------- Hero dome slideshow ---------- */
  var dome = document.getElementById("heroDome");
  var featured = data.filter(function (d) { return d.featured; });
  if (!featured.length) featured = data.slice(0, 4);
  featured.forEach(function (d, i) {
    var img = new Image();
    img.src = d.src; img.alt = ""; img.decoding = "async";
    if (i === 0) img.className = "on"; else img.loading = "lazy";
    dome.appendChild(img);
  });
  if (featured.length > 1 && !reduceMotion) {
    var cur = 0, imgs = dome.querySelectorAll("img");
    setInterval(function () {
      if (document.hidden) return;
      imgs[cur].classList.remove("on");
      cur = (cur + 1) % imgs.length;
      imgs[cur].classList.add("on");
    }, 4500);
  }

  /* ---------- Category circles + about photo ---------- */
  document.querySelectorAll(".kind-img").forEach(function (el) {
    var list = byCat(el.dataset.cat).filter(function (d) { return !d.about; });
    bgUrl(el, list.filter(function (d) { return d.featured; })[0] || list[0]);
  });
  var aboutPick = data.filter(function (d) { return d.about; })[0] || data[data.length - 1];
  bgUrl(document.getElementById("aboutImg"), aboutPick);

  /* ---------- Gallery ---------- */
  var gallery = document.getElementById("gallery");
  var empty = document.getElementById("galleryEmpty");
  var visible = [];

  data.forEach(function (d, i) {
    var li = document.createElement("li");
    li.dataset.cat = d.cat;
    var btn = document.createElement("button");
    btn.className = "g-item";
    btn.type = "button";
    btn.dataset.index = i;
    btn.setAttribute("aria-label", "View larger: " + (d.title || "cake photo"));
    var img = document.createElement("img");
    img.src = d.thumb || d.src;
    img.alt = d.title || "Cake by Zaheen's Cake";
    img.loading = "lazy";
    img.decoding = "async";
    if (d.w && d.h) { img.width = d.w; img.height = d.h; }
    var cap = document.createElement("span");
    cap.className = "g-cap";
    cap.textContent = CAT_LABEL[d.cat] || "";
    btn.appendChild(img);
    btn.appendChild(cap);
    li.appendChild(btn);
    gallery.appendChild(li);
  });

  var chips = document.querySelectorAll(".chip");
  function applyFilter(cat) {
    visible = [];
    gallery.querySelectorAll("li").forEach(function (li) {
      var show = cat === "all" || li.dataset.cat === cat;
      li.hidden = !show;
      if (show) visible.push(+li.firstChild.dataset.index);
    });
    chips.forEach(function (c) {
      var on = c.dataset.filter === cat;
      c.classList.toggle("is-active", on);
      c.setAttribute("aria-pressed", String(on));
    });
    empty.hidden = visible.length > 0;
  }
  chips.forEach(function (c) { c.addEventListener("click", function () { applyFilter(c.dataset.filter); }); });
  applyFilter("all");

  /* "What we bake" circles jump to the filtered gallery */
  document.querySelectorAll(".kind").forEach(function (k) {
    k.addEventListener("click", function () {
      applyFilter(k.dataset.filter);
      document.getElementById("cakes").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
    });
  });

  /* ---------- Lightbox ---------- */
  var lb = document.getElementById("lightbox");
  var lbImg = document.getElementById("lbImg");
  var lbCap = document.getElementById("lbCaption");
  var lbOrder = document.getElementById("lbOrder");
  var pos = 0, lastFocus = null;

  function show(p) {
    pos = (p + visible.length) % visible.length;
    var d = data[visible[pos]];
    lbImg.src = d.src;
    lbImg.alt = d.title || "Cake by Zaheen's Cake";
    lbCap.textContent = (d.title || CAT_LABEL[d.cat] || "") + "  (" + (pos + 1) + " / " + visible.length + ")";
    var msg = "Hi Zaheen's Cake, I'd like to order a cake like this one: " +
      new URL(d.src, location.href).href;
    lbOrder.href = "https://wa.me/" + PHONE_WA + "?text=" + encodeURIComponent(msg);
  }
  function open(index) {
    lastFocus = document.activeElement;
    lb.hidden = false;
    document.body.style.overflow = "hidden";
    show(visible.indexOf(index));
    document.getElementById("lbClose").focus();
  }
  function close() {
    lb.hidden = true;
    document.body.style.overflow = "";
    if (lastFocus) lastFocus.focus();
  }

  gallery.addEventListener("click", function (e) {
    var b = e.target.closest(".g-item");
    if (b) open(+b.dataset.index);
  });
  document.getElementById("lbClose").addEventListener("click", close);
  document.getElementById("lbPrev").addEventListener("click", function () { show(pos - 1); });
  document.getElementById("lbNext").addEventListener("click", function () { show(pos + 1); });
  lb.addEventListener("click", function (e) { if (e.target === lb) close(); });
  document.addEventListener("keydown", function (e) {
    if (lb.hidden) return;
    if (e.key === "Escape") close();
    else if (e.key === "ArrowLeft") show(pos - 1);
    else if (e.key === "ArrowRight") show(pos + 1);
    else if (e.key === "Tab") {           // keep focus inside the dialog
      var f = lb.querySelectorAll("button, a");
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
      else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
    }
  });

  /* Swipe on touch screens */
  var sx = null, sy = null;
  lb.addEventListener("touchstart", function (e) { sx = e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
  lb.addEventListener("touchend", function (e) {
    if (sx === null) return;
    var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) show(pos + (dx < 0 ? 1 : -1));
    else if (dy > 90 && Math.abs(dy) > Math.abs(dx)) close();
    sx = sy = null;
  });

  /* Discourage casual saving of photos (watermark is the real protection) */
  document.addEventListener("contextmenu", function (e) {
    if (e.target.tagName === "IMG" && e.target.closest(".gallery, .lightbox, .dome")) e.preventDefault();
  });
  document.addEventListener("dragstart", function (e) {
    if (e.target.tagName === "IMG") e.preventDefault();
  });
})();
