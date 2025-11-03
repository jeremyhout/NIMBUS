// weather_app/static/help.js

// ---- Configure your slides here ----
const SLIDES = [
  "/static/tutorial/help_01.png",
  "/static/tutorial/help_02.png",
  // add more paths as needed
];

// ---- Inject FAB + Modal and wire up behavior ----
(function () {
  // If no slides configured, do nothing
  if (!Array.isArray(SLIDES) || SLIDES.length === 0) return;

  // Create FAB (floating action button)
  const fab = document.createElement("button");
  fab.className = "help-fab";
  fab.type = "button";
  fab.setAttribute("aria-label", "Open tutorial");
  fab.title = "How to use this app";
  fab.textContent = "i";

  // Modal overlay
  const overlay = document.createElement("div");
  overlay.className = "help-overlay";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-hidden", "true");
  overlay.style.display = "none";

  // Modal content
  const modal = document.createElement("div");
  modal.className = "help-modal";

  const closeBtn = document.createElement("button");
  closeBtn.className = "help-close";
  closeBtn.type = "button";
  closeBtn.setAttribute("aria-label", "Close tutorial");
  closeBtn.textContent = "×";

  const img = document.createElement("img");
  img.className = "help-slide";
  img.alt = "Tutorial slide";

  const counter = document.createElement("div");
  counter.className = "help-counter";

  const controls = document.createElement("div");
  controls.className = "help-controls";

  const prevBtn = document.createElement("button");
  prevBtn.type = "button";
  prevBtn.className = "help-prev";
  prevBtn.textContent = "◀";
  prevBtn.title = "Previous (←)";

  const nextBtn = document.createElement("button");
  nextBtn.type = "button";
  nextBtn.className = "help-next";
  nextBtn.textContent = "▶";
  nextBtn.title = "Next (→)";

  controls.appendChild(prevBtn);
  controls.appendChild(nextBtn);

  modal.appendChild(closeBtn);
  modal.appendChild(img);
  modal.appendChild(counter);
  modal.appendChild(controls);
  overlay.appendChild(modal);

  document.body.appendChild(fab);
  document.body.appendChild(overlay);

  // State
  let idx = 0;
  let lastFocused = null;

  function showSlide(i) {
    if (i < 0) i = SLIDES.length - 1;
    if (i >= SLIDES.length) i = 0;
    idx = i;
    img.src = SLIDES[idx];
    counter.textContent = `${idx + 1} / ${SLIDES.length}`;
  }

  function openModal() {
    lastFocused = document.activeElement;
    overlay.style.display = "flex";
    document.body.classList.add("no-scroll");
    overlay.setAttribute("aria-hidden", "false");
    showSlide(idx);
    // Focus close for keyboard users
    setTimeout(() => closeBtn.focus(), 0);
    document.addEventListener("keydown", onKey);
  }

  function closeModal() {
    document.body.classList.remove("no-scroll");
    overlay.style.display = "none";
    overlay.setAttribute("aria-hidden", "true");
    document.removeEventListener("keydown", onKey);
    if (lastFocused && typeof lastFocused.focus === "function") {
      lastFocused.focus();
    } else {
      fab.focus();
    }
  }

  function onKey(e) {
    if (e.key === "Escape") { e.preventDefault(); closeModal(); }
    else if (e.key === "ArrowRight") { e.preventDefault(); showSlide(idx + 1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); showSlide(idx - 1); }
  }

  // Events
  fab.addEventListener("click", openModal);
  closeBtn.addEventListener("click", closeModal);

  // Click outside modal to close
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal();
  });

  prevBtn.addEventListener("click", () => showSlide(idx - 1));
  nextBtn.addEventListener("click", () => showSlide(idx + 1));

  // Preload images (nice-to-have)
  SLIDES.forEach(src => { const p = new Image(); p.src = src; });
})();
