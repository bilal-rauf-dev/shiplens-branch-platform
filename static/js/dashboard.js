"use strict";

// This file is loaded only by the financial dashboards. The tables remain usable
// without JavaScript and json_script provides data without executable inline code.
(() => {
  const labels = JSON.parse(document.getElementById("chart-labels").textContent);
  const money = JSON.parse(document.getElementById("money-trend").textContent);
  const tokens = getComputedStyle(document.documentElement);
  const locale = document.documentElement.lang;
  Chart.defaults.font.family = tokens.getPropertyValue("--md-font").trim();
  Chart.defaults.color = tokens.getPropertyValue("--md-on-surface-variant").trim();
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const monthLabel = new Intl.DateTimeFormat(locale, {
    month: "short", year: "2-digit", timeZone: "UTC", numberingSystem: "latn"
  });
  const options = {
    locale: locale + "-u-nu-latn",
    responsive: true,
    maintainAspectRatio: false,
    animation: reducedMotion ? false : { duration: 300 },
    plugins: { legend: { rtl: document.documentElement.dir === "rtl" } },
    scales: { y: { beginAtZero: true } }
  };
  new Chart(document.getElementById("money-chart"), {
    type: "bar",
    data: {
      labels: money.map(point => monthLabel.format(new Date(point.month + "T00:00:00Z"))),
      datasets: [
        { label: labels.collected, data: money.map(point => Number(point.collected)), backgroundColor: tokens.getPropertyValue("--md-primary").trim() },
        { label: labels.approved, data: money.map(point => Number(point.approved)), backgroundColor: tokens.getPropertyValue("--md-tertiary").trim() }
      ]
    },
    options
  });
  const memberCanvas = document.getElementById("member-chart");
  if (memberCanvas) {
    const members = JSON.parse(document.getElementById("member-trend").textContent);
    new Chart(memberCanvas, {
      type: "bar",
      data: {
        labels: members.map(point => monthLabel.format(new Date(point.month + "T00:00:00Z"))),
        datasets: [{ label: labels.members, data: members.map(point => point.new), backgroundColor: tokens.getPropertyValue("--md-primary").trim() }]
      },
      options: { ...options, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
    });
  }
})();
