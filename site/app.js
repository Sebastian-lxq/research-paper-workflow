const copyButtons = document.querySelectorAll("[data-copy]");

for (const button of copyButtons) {
  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copy);
    if (!target) return;
    const value = target.innerText.trim();
    try {
      await navigator.clipboard.writeText(value);
      const original = button.textContent;
      button.textContent = "Copied";
      setTimeout(() => { button.textContent = original; }, 1400);
    } catch {
      window.prompt("Copy this text:", value);
    }
  });
}

const observer = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) entry.target.classList.add("visible");
    }
  },
  { threshold: 0.12 }
);

for (const element of document.querySelectorAll(".reveal")) observer.observe(element);
