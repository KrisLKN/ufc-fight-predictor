// app.js — UFC Fight Predictor (identite portfolio + photos Wikipedia)

const state = { fighters: [], a: null, b: null };
const el = (id) => document.getElementById(id);

/* ---------- Theme (clair/sombre, defaut sombre, memorise) ---------- */
(function theme() {
  const html = document.documentElement;
  const apply = (t) => {
    html.setAttribute("data-theme", t);
    el("iconMoon").style.display = t === "light" ? "block" : "none";
    el("iconSun").style.display = t === "light" ? "none" : "block";
    localStorage.setItem("ufc-theme", t);
  };
  apply(localStorage.getItem("ufc-theme") || "dark");
  el("themeToggle").addEventListener("click", () =>
    apply(html.getAttribute("data-theme") === "light" ? "dark" : "light")
  );
})();

/* ---------- Photos des combattants (scraping Wikipedia, cote client) ---------- */
const photoCache = new Map();
async function fighterPhoto(name) {
  if (photoCache.has(name)) return photoCache.get(name);
  const url =
    "https://en.wikipedia.org/w/api.php?action=query&format=json&origin=*" +
    "&prop=pageimages&piprop=thumbnail&pithumbsize=400&redirects=1&titles=" +
    encodeURIComponent(name);
  let src = null;
  try {
    const data = await fetch(url).then((r) => r.json());
    const pages = data?.query?.pages || {};
    const page = Object.values(pages)[0];
    if (page?.thumbnail?.source) src = page.thumbnail.source;
  } catch (_) { /* hors-ligne ou bloque : on garde les initiales */ }
  photoCache.set(name, src);
  return src;
}

function initials(name) {
  return name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
}

async function setAvatar(box, name, side) {
  if (!name) { box.className = "avatar"; box.innerHTML = `<span class="avatar-ph">${side.toUpperCase()}</span>`; return; }
  box.className = "avatar loading";
  box.innerHTML = `<span class="avatar-ph">${initials(name)}</span>`;
  const src = await fighterPhoto(name);
  if (box.dataset.name !== name) return;            // une autre selection a eu lieu
  box.className = "avatar" + (src ? " filled" : "");
  box.innerHTML = src
    ? `<img src="${src}" alt="${name}" loading="lazy">`
    : `<span class="avatar-ph">${initials(name)}</span>`;
}

/* ---------- Init ---------- */
async function init() {
  try {
    const [health, list] = await Promise.all([
      fetch("/api/health").then((r) => r.json()),
      fetch("/api/fighters").then((r) => r.json()),
    ]);
    const m = health.metrics;
    el("model-badge").textContent =
      `precision ${(m.accuracy * 100).toFixed(0)}% · ${m.n_fighters} combattants`;
    state.fighters = list.fighters;
    setupPicker("a", "Charles Oliveira");
    setupPicker("b", "Ilia Topuria");
  } catch (e) {
    showError("Impossible de charger les donnees. L'API est-elle demarree ?");
  }
}

function setupPicker(side, defaultName) {
  const select = el(`select-${side}`);
  const search = el(`search-${side}`);
  const avatar = el(`avatar-${side}`);

  const render = (query = "") => {
    const q = query.toLowerCase();
    select.innerHTML = "";
    state.fighters
      .filter((f) => f.name.toLowerCase().includes(q))
      .slice(0, 300)
      .forEach((f) => {
        const opt = document.createElement("option");
        opt.value = f.name;
        opt.textContent = f.weight_class ? `${f.name} · ${f.weight_class}` : f.name;
        select.appendChild(opt);
      });
  };

  const choose = (name) => {
    state[side] = name;
    avatar.dataset.name = name;
    setAvatar(avatar, name, side);
    refreshButton();
  };

  render();
  search.addEventListener("input", () => render(search.value));
  select.addEventListener("change", () => choose(select.value));

  const match = state.fighters.find((f) => f.name === defaultName);
  if (match) { select.value = defaultName; choose(defaultName); }
  refreshButton();
}

function refreshButton() { el("predict-btn").disabled = !(state.a && state.b); }
function showError(msg) { const e = el("error"); e.textContent = msg; e.hidden = false; }
function clearError() { el("error").hidden = true; }

/* ---------- Prediction ---------- */
async function predict() {
  clearError();
  if (state.a === state.b) { showError("Choisis deux combattants differents."); return; }
  const btn = el("predict-btn");
  btn.disabled = true; btn.textContent = "Calcul...";
  try {
    const res = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fighter_a: state.a, fighter_b: state.b }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Erreur de prediction");
    }
    await renderResult(await res.json());
  } catch (e) {
    showError(e.message);
  } finally {
    btn.disabled = false; btn.textContent = "Predire le vainqueur";
  }
}

async function renderResult(data) {
  const a = data.fighters.a, b = data.fighters.b;
  const pa = data.probabilities[a.name], pb = data.probabilities[b.name];

  el("winner-name").textContent = data.winner;
  const wav = el("winner-avatar");
  wav.innerHTML = "";
  const wsrc = await fighterPhoto(data.winner);
  if (wsrc) wav.innerHTML = `<img src="${wsrc}" alt="${data.winner}">`;

  el("proba-a").style.width = `${(pa * 100).toFixed(0)}%`;
  el("proba-b").style.width = `${(pb * 100).toFixed(0)}%`;
  el("proba-a-name").textContent = `${a.name} ${(pa * 100).toFixed(0)}%`;
  el("proba-b-name").textContent = `${(pb * 100).toFixed(0)}% ${b.name}`;

  const rows = [
    ["Victoires", a.wins, b.wins, "max"],
    ["Combats", a.fights, b.fights, "none"],
    ["Taux de victoire", pct(a.win_rate), pct(b.win_rate), "rate"],
    ["Age", a.age ?? "—", b.age ?? "—", "minAge"],
    ["Allonge", a.reach ? `${a.reach}"` : "—", b.reach ? `${b.reach}"` : "—", "maxReach"],
  ];
  const lead = (kind, av, bv) => {
    if (kind === "max" || kind === "rate" || kind === "maxReach")
      return numeric(av) === numeric(bv) ? 0 : numeric(av) > numeric(bv) ? -1 : 1;
    if (kind === "minAge")
      return numeric(av) === numeric(bv) ? 0 : numeric(av) < numeric(bv) ? -1 : 1;
    return 0;
  };
  let html = `<tr><th>${a.name}</th><th></th><th>${b.name}</th></tr>`;
  rows.forEach(([label, av, bv, kind]) => {
    const l = lead(kind, av, bv);
    html += `<tr><td class="${l === -1 ? "lead" : ""}">${av}</td><td>${label}</td><td class="${l === 1 ? "lead" : ""}">${bv}</td></tr>`;
  });
  el("compare").innerHTML = html;

  el("result").hidden = false;
  el("result").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(0)}%`);
const numeric = (v) => parseFloat(String(v).replace(/[^0-9.]/g, "")) || 0;

el("predict-btn").addEventListener("click", predict);
init();
