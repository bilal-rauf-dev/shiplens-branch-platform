"use strict";

// Loaded on staff pages and the login form only; public pages stay free of scripts.
// The loader is purely visual: without this file every form still submits normally.
(() => {
  const span = className => {
    const element = document.createElement("span");
    element.className = className;
    return element;
  };

  // Matches templates/partials/spinner.html.
  const buildSpinner = () => {
    const spinner = span("spinner");
    spinner.dir = "ltr";
    spinner.setAttribute("aria-hidden", "true");
    const layer = span("spinner__layer");
    layer.append(span("spinner__half spinner__half--start"), span("spinner__half spinner__half--end"));
    spinner.append(layer);
    return spinner;
  };

  document.addEventListener("submit", event => {
    const button = event.submitter;
    if (!button || button.tagName !== "BUTTON" || button.getAttribute("aria-busy") === "true") {
      return;
    }
    // Not disabled: a disabled button would drop its name and value from the POST.
    button.setAttribute("aria-busy", "true");
    button.prepend(buildSpinner());
  });

  // The back button can restore this page from memory, so clear any old loader.
  window.addEventListener("pageshow", () => {
    document.querySelectorAll('button[aria-busy="true"]').forEach(button => {
      button.removeAttribute("aria-busy");
      button.querySelector(".spinner")?.remove();
    });
  });
})();
