const header = document.querySelector(".site-header");
const mobileMenu = document.querySelector(".mobile-nav");
const contactForm = document.querySelector("#contact-form");
const phoneInput = document.querySelector("#contact-phone");
const nameInput = document.querySelector("#contact-name");
const interestInput = document.querySelector("#contact-interest");
const formError = document.querySelector("#contact-error");
const formStatus = document.querySelector("#contact-status");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (!reducedMotion) {
  document.documentElement.classList.add("motion-ready");
}

const markPageLoaded = () => document.body.classList.add("is-loaded");
if (document.readyState === "complete") {
  markPageLoaded();
} else {
  window.addEventListener("load", markPageLoaded, { once: true });
}

if ("IntersectionObserver" in window && !reducedMotion) {
  const revealObserver = new IntersectionObserver((entries, observer) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    }
  }, { threshold: 0.12, rootMargin: "0px 0px -7% 0px" });

  document.querySelectorAll(".reveal").forEach((element) => revealObserver.observe(element));
} else {
  document.querySelectorAll(".reveal").forEach((element) => element.classList.add("is-visible"));
}

let scrollScheduled = false;
const updateHeader = () => {
  if (header) header.classList.toggle("is-scrolled", window.scrollY > 34);
  scrollScheduled = false;
};

window.addEventListener("scroll", () => {
  if (!scrollScheduled) {
    window.requestAnimationFrame(updateHeader);
    scrollScheduled = true;
  }
}, { passive: true });
updateHeader();

mobileMenu?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => mobileMenu.removeAttribute("open"));
});

document.querySelectorAll("[data-interest]").forEach((link) => {
  link.addEventListener("click", () => {
    if (interestInput) interestInput.value = link.dataset.interest ?? "";
  });
});

contactForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const digits = phoneInput?.value.replace(/\D/g, "") ?? "";
  const validName = Boolean(nameInput?.value.trim());
  const validPhone = digits.length >= 10;

  nameInput?.setAttribute("aria-invalid", String(!validName));
  phoneInput?.setAttribute("aria-invalid", String(!validPhone));
  formError.hidden = validName && validPhone;
  formStatus.hidden = true;

  if (!validName || !validPhone) {
    (!validName ? nameInput : phoneInput)?.focus();
    return;
  }

  formStatus.textContent = "Данные проверены. В этом макете отправка заявки не подключена.";
  formStatus.hidden = false;
});

contactForm?.querySelectorAll("input").forEach((input) => {
  input.addEventListener("input", () => {
    input.removeAttribute("aria-invalid");
    if (!formError.hidden) formError.hidden = true;
    if (!formStatus.hidden) formStatus.hidden = true;
  });
});
