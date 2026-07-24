const formPost = async (url, body) => {
  const response = await fetch(url, {method: "POST", body});
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
};
const progress = document.querySelector("#progress");
let statusTimer;
function monitor() {
  progress.classList.add("visible");
  clearInterval(statusTimer);
  statusTimer = setInterval(async () => {
    try {
      const job = await fetch("/create/status", {cache:"no-store"}).then(r => r.json());
      document.querySelector("#progress-message").textContent = job.message;
      document.querySelector("#progress-percent").textContent = `${job.progress}%`;
      progress.querySelector("b").style.width = `${job.progress}%`;
      if (job.state !== "running") {
        clearInterval(statusTimer);
        if (job.state === "ready") setTimeout(() => location.reload(), 350);
      }
    } catch (_) {}
  }, 500);
}
document.querySelector("#optional-rebuild").addEventListener("click", async () => {
  await formPost("/create/build", new URLSearchParams(new FormData(document.querySelector("#create-form"))));
  monitor();
});
document.querySelector("#rebuild-button").addEventListener("click", async () => {
  await formPost("/create/rebuild", new FormData());
  monitor();
});
document.querySelector("#refine-form").addEventListener("submit", async event => {
  event.preventDefault();
  await formPost("/create/refine", new URLSearchParams(new FormData(event.currentTarget)));
  monitor();
});
document.querySelectorAll(".suggestions button").forEach(button => button.addEventListener("click", () => {
  document.querySelector("#refine-form input").value = button.textContent;
}));
document.querySelectorAll(".import-trigger").forEach(button => button.addEventListener("click", () => {
  document.querySelector("#import").scrollIntoView();
  document.querySelector("#generated-files").click();
}));
document.querySelector("#import-form").addEventListener("submit", async event => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  button.disabled = true; button.textContent = "INSPECTING…";
  try {
    const result = await formPost("/create/import", new FormData(event.currentTarget));
    document.querySelector("#import-results").innerHTML = result.added.map(item =>
      `<div><strong>${item.name}</strong><span>${item.kind || ""} · Shot ${item.assigned_shot || "unassigned"}</span><em>${item.status}</em></div>`
    ).join("");
    monitor();
  } finally { button.disabled = false; button.textContent = "IMPORT GENERATED RESULTS"; }
});
document.querySelectorAll(".view-switch button").forEach(button => button.addEventListener("click", () => {
  document.querySelectorAll(".view-switch button").forEach(item => item.classList.remove("active"));
  button.classList.add("active");
  document.querySelector("#shot-grid").classList.toggle("sequence", button.dataset.view === "sequence");
}));
const lightbox = document.querySelector("#lightbox");
document.querySelectorAll(".frame-button").forEach(button => button.addEventListener("click", () => {
  lightbox.querySelector("img").src = button.dataset.full; lightbox.showModal();
}));
lightbox.querySelector("button").addEventListener("click", () => lightbox.close());
document.querySelectorAll(".toggle-shot").forEach(button => button.addEventListener("click", async () => {
  const card = button.closest(".shot-card"), enabled = card.classList.contains("disabled");
  const body = new URLSearchParams(); body.set("enabled", enabled);
  await formPost(`/create/shot/${card.dataset.shot}/enabled`, body);
  card.classList.toggle("disabled", !enabled); button.textContent = enabled ? "Disable" : "Enable"; monitor();
}));
let dragged;
document.querySelectorAll(".shot-card").forEach(card => {
  card.addEventListener("dragstart", () => { dragged = card; card.classList.add("dragging"); });
  card.addEventListener("dragend", async () => {
    card.classList.remove("dragging");
    const body = new URLSearchParams();
    body.set("order", [...document.querySelectorAll(".shot-card")].map(item => item.dataset.shot).join(","));
    await formPost("/create/reorder", body); monitor();
  });
  card.addEventListener("dragover", event => {
    event.preventDefault();
    if (dragged && dragged !== card) {
      const rect = card.getBoundingClientRect();
      card.parentNode.insertBefore(dragged, event.clientY < rect.top + rect.height / 2 ? card : card.nextSibling);
    }
  });
});
