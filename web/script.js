const revealItems = document.querySelectorAll(".reveal");
const currentYear = document.getElementById("current-year");
const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

if (currentYear) {
  currentYear.textContent = String(new Date().getFullYear());
}

if ("IntersectionObserver" in window && !reducedMotionQuery.matches) {
  const revealObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return;
        }

        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    {
      threshold: 0.18,
      rootMargin: "0px 0px -10% 0px",
    },
  );

  revealItems.forEach((item) => {
    if (!item.classList.contains("is-visible")) {
      revealObserver.observe(item);
    }
  });
} else {
  revealItems.forEach((item) => item.classList.add("is-visible"));
}

if (!reducedMotionQuery.matches) {
  let pointerFrame = 0;
  let pendingX = window.innerWidth * 0.65;
  let pendingY = window.innerHeight * 0.12;

  const paintPointer = () => {
    document.documentElement.style.setProperty("--pointer-x", `${pendingX}px`);
    document.documentElement.style.setProperty("--pointer-y", `${pendingY}px`);
    pointerFrame = 0;
  };

  window.addEventListener("pointermove", (event) => {
    pendingX = event.clientX;
    pendingY = event.clientY;

    if (!pointerFrame) {
      pointerFrame = window.requestAnimationFrame(paintPointer);
    }
  });
}
