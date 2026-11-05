const header = document.querySelector(".site-header");
const mobileMenu = document.querySelector(".mobile-nav");
const interestInput = document.querySelector("#contact-interest");
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

// A bounded, 30 fps SVG mask: pointer inertia and a brief organic settling motion.
const footerWordmark = document.querySelector('[data-footer-wordmark]');
if (footerWordmark) {
  const svg = footerWordmark.querySelector('svg');
  const spot = footerWordmark.querySelector('[data-footer-spot]');
  const shape = footerWordmark.querySelector('[data-footer-blob-shape]');
  const interactive = matchMedia('(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)');
  // One softly edged path; the filter is bounded to a small local SVG region.
  const layer = document.createElementNS('http://www.w3.org/2000/svg','use');
  layer.setAttribute('href','#footer-blob-shape');
  layer.setAttribute('filter','url(#footer-blob-soften)');
  spot.append(layer);
  let bounds = null, frame = 0, x = 0, y = 0, targetX = 0, targetY = 0;
  let lastPaint = 0, lastMove = 0, phase = 0, spread = 0.9, stretch = 0, angle = 0;
  function contour() {
    const count = 12, points = [];
    for (let index=0;index<count;index++) {
      const a=index*Math.PI*2/count;
      const radius=128*(1+0.17*Math.sin(3*a+phase)+0.10*Math.sin(5*a-phase*0.73)+0.05*Math.cos(2*a+phase*0.4));
      points.push([Math.cos(a)*radius,Math.sin(a)*radius]);
    }
    const at=index=>points[(index+count)%count];
    let d=`M${points[0].join(',')}`;
    for(let index=0;index<count;index++) {
      const previous=at(index-1),current=at(index),next=at(index+1),after=at(index+2);
      d+=`C${current[0]+(next[0]-previous[0])/6},${current[1]+(next[1]-previous[1])/6} ${next[0]-(after[0]-current[0])/6},${next[1]-(after[1]-current[1])/6} ${next.join(',')}`;
    }
    shape.setAttribute('d',d+'Z');
  }
  function paintSpot(now) {
    frame=0;
    if (!interactive.matches || document.hidden || !footerWordmark.classList.contains('is-highlighted')) return;
    const elapsed=now-lastPaint;
    if (elapsed>=1000/30-0.5) {
      const dt=Math.min(elapsed,48), follow=1-Math.exp(-dt/85), soften=1-Math.exp(-dt/160);
      const dx=targetX-x,dy=targetY-y,distance=Math.hypot(dx,dy);
      if(distance>0.5) {
        const direction=Math.atan2(dy,dx)*180/Math.PI;
        angle+=(((direction-angle)%360+540)%360-180)*soften;
      }
      x+=dx*follow;y+=dy*follow;
      stretch+=(Math.min(distance/450,0.24)-stretch)*soften;
      spread+=(1-spread)*soften;
      phase+=dt*0.0014;
      contour();
      spot.style.transform=`translate(${x}px, ${y}px) rotate(${angle}deg) scale(${spread*(1+stretch)}, ${spread*(1-stretch*0.25)})`;
      lastPaint=now;
    }
    // No persistent idle animation, including when a pointer is parked here.
    if (now-lastMove<1100 || Math.hypot(targetX-x,targetY-y)>0.1) frame=requestAnimationFrame(paintSpot);
  }
  function moveSpot(event) {
    if (!interactive.matches || document.hidden || event.pointerType === 'touch') return;
    bounds ||= svg.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    targetX=(event.clientX-bounds.left)*1000/bounds.width;
    targetY=(event.clientY-bounds.top)*260/bounds.height;
    lastMove=performance.now();
    if (!footerWordmark.classList.contains('is-highlighted')) {
      x=targetX;y=targetY;angle=0;stretch=0;spread=0.9;phase=lastMove*0.001;
      lastPaint=lastMove-1000/30;
      footerWordmark.classList.add('is-highlighted');
    }
    if (!frame) frame = requestAnimationFrame(paintSpot);
  }
  function resetSpot() {
    cancelAnimationFrame(frame); frame = 0; bounds = null;
    footerWordmark.classList.remove('is-highlighted');
  }
  footerWordmark.addEventListener('pointerenter', event => {
    if (!interactive.matches || event.pointerType === 'touch') return;
    bounds = svg.getBoundingClientRect();
    moveSpot(event);
  });
  footerWordmark.addEventListener('pointermove', moveSpot, { passive: true });
  footerWordmark.addEventListener('pointerleave', resetSpot);
  footerWordmark.addEventListener('pointercancel', resetSpot);
  interactive.addEventListener('change', resetSpot);
  window.addEventListener('resize', resetSpot, { passive: true });
  window.addEventListener('scroll', resetSpot, { passive: true });
  window.addEventListener('blur', resetSpot);
  document.addEventListener('visibilitychange', () => { if (document.hidden) resetSpot(); });
  new IntersectionObserver(entries=>{if(!entries[0].isIntersecting)resetSpot();}).observe(footerWordmark);
}
