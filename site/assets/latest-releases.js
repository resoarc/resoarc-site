/* Keep the homepage Information list in sync with /releases/ (the source of truth).
   Only a same-origin GET is made; no user data is sent. */
(() => {
  "use strict";
  const target = document.querySelector(".updates-items");
  if (!target) return;

  function latestItems(html) {
    const page = new DOMParser().parseFromString(html, "text/html");
    return [...page.querySelectorAll(".release-entry")].map((entry, index) => {
      const time = entry.querySelector("time[datetime]");
      const heading = entry.querySelector("h2");
      if (!time || !heading || !/^\d{4}-\d{2}-\d{2}$/.test(time.dateTime)) return null;
      const label = entry.querySelector("time + span");
      const link = [...entry.querySelectorAll("a[href]")].find(a => {
        try {
          const url = new URL(a.getAttribute("href"), location.origin);
          return url.origin === location.origin && url.pathname.startsWith("/");
        } catch (_) { return false; }
      });
      return {
        date: time.dateTime,
        label: label ? label.textContent.trim() : "UPDATE",
        title: heading.textContent.trim(),
        href: link ? new URL(link.getAttribute("href"), location.origin).pathname : "/releases/",
        index,
      };
    }).filter(Boolean).sort((a, b) =>
      b.date.localeCompare(a.date) || a.index - b.index
    ).slice(0, 3);
  }

  function display(items) {
    if (!items.length) return;
    const fragment = document.createDocumentFragment();
    for (const item of items) {
      const row = document.createElement("div");
      row.className = "update-row";
      const time = document.createElement("time");
      time.dateTime = item.date;
      time.textContent = item.date.replaceAll("-", ".");
      const category = document.createElement("span");
      category.textContent = item.label;
      const heading = document.createElement("strong");
      const link = document.createElement("a");
      link.href = item.href;
      link.textContent = item.title + " ↗";
      heading.append(link);
      row.append(time, category, heading);
      fragment.append(row);
    }
    const more = document.createElement("p");
    more.className = "no-more";
    const link = document.createElement("a");
    link.href = "/releases/";
    link.textContent = "更新履歴をすべて見る ↗";
    more.append(link);
    fragment.append(more);
    target.replaceChildren(fragment);
  }

  fetch("/releases/", { credentials: "same-origin", cache: "no-store" })
    .then(response => {
      if (!response.ok || !(response.headers.get("content-type") || "").includes("text/html")) {
        throw new Error("Release page unavailable");
      }
      return response.text();
    })
    .then(html => display(latestItems(html)))
    .catch(() => {
      /* Leave the useful server-rendered fallback in place. */
    });
})();
