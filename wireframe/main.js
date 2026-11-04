const header = document.querySelector(".site-header");
const mobileMenu = document.querySelector(".mobile-nav");
const contactForm = document.querySelector("#contact-form");
const phoneInput = document.querySelector("#contact-phone");
const nameInput = document.querySelector("#contact-name");
const interestInput = document.querySelector("#contact-interest");
const formError = document.querySelector("#contact-error");
const formStatus = document.querySelector("#contact-status");
const pageRoot = document.documentElement;
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let loaderActive = pageRoot.classList.contains("loader-pending") && !reducedMotion;

if (!reducedMotion) {
  pageRoot.classList.add("motion-ready");
}

const imageStates = new Map();
const revealImageIfReady = (frame, state) => {
  if (!state.ready || !state.intersected || state.started || state.failed) return;
  if (loaderActive && frame.classList.contains("hero-image-frame")) return;

  state.started = true;
  frame.classList.add("is-image-revealing");
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => frame.classList.add("is-image-revealed"));
  });
};

const markImageReady = (frame, image, state) => {
  if (state.failed) return;
  if (image.naturalWidth === 0) {
    state.failed = true;
    frame.classList.remove("is-image-revealing", "is-image-revealed");
    frame.classList.add("is-image-error");
    return;
  }

  const reveal = () => {
    if (image.naturalWidth === 0) {
      state.failed = true;
      frame.classList.remove("is-image-revealing", "is-image-revealed");
      frame.classList.add("is-image-error");
      return;
    }
    state.ready = true;
    revealImageIfReady(frame, state);
  };

  if (typeof image.decode === "function") {
    image.decode().then(reveal, reveal);
  } else {
    reveal();
  }
};

if ("IntersectionObserver" in window && !reducedMotion) {
  const imageObserver = new IntersectionObserver((entries, observer) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      const state = imageStates.get(entry.target);
      if (!state) continue;
      state.intersected = true;
      revealImageIfReady(entry.target, state);
      observer.unobserve(entry.target);
    }
  }, { threshold: 0, rootMargin: "0px 0px -15% 0px" });

  document.querySelectorAll("[data-image-frame]").forEach((frame) => {
    const image = frame.querySelector("img");
    if (!image) return;

    const state = { ready: false, intersected: false, started: false, failed: false };
    imageStates.set(frame, state);
    image.addEventListener("load", () => markImageReady(frame, image, state), { once: true });
    image.addEventListener("error", () => {
      state.failed = true;
      frame.classList.remove("is-image-revealing", "is-image-revealed");
      frame.classList.add("is-image-error");
    }, { once: true });

    if (image.complete) {
      if (image.naturalWidth > 0) markImageReady(frame, image, state);
      else {
        state.failed = true;
        frame.classList.add("is-image-error");
      }
    }
    imageObserver.observe(frame);
  });
}

const finishLoader = () => {
  document.body.classList.add("is-loaded");
  if (!loaderActive) return;

  loaderActive = false;
  pageRoot.classList.remove("loader-pending");
  for (const [frame, state] of imageStates) revealImageIfReady(frame, state);
};

document.body.classList.add("is-loaded");
if (loaderActive) {
  const loaderExitPanel = document.querySelector(".loader-panels span:first-child");
  const onLoaderExit = (event) => {
    if (event.animationName === "loader-panel-out") finishLoader();
  };

  if (getComputedStyle(document.querySelector(".loader")).visibility === "hidden") {
    finishLoader();
  } else {
    loaderExitPanel?.addEventListener("animationend", onLoaderExit, { once: true });
    window.setTimeout(finishLoader, 4200);
  }
} else if (reducedMotion) {
  pageRoot.classList.remove("loader-pending");
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

if (!contactForm?.hasAttribute("data-lead-form")) {
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
}
