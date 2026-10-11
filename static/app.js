// ---------------------------------------------------------------------------
// Movistar Plus+ Controller Client Logic
// Monochromatic Architectural Dark Interface
// ---------------------------------------------------------------------------

const CATEGORIES = [
  { id: "todos", name: "Todos" },
  { id: "generalistas", name: "Generalistas" },
  { id: "cine_series", name: "Cine y Series" },
  { id: "deportes", name: "Deportes y Fútbol" },
  { id: "documentales", name: "Documentales y Estilo" },
  { id: "infantil", name: "Infantil" },
  { id: "musica", name: "Música" },
  { id: "noticias", name: "Noticias e Internacional" },
  { id: "autonomicos", name: "Autonómicos" }
];

let allChannels = [];
let currentPlaybackState = null;
let currentSettings = null;
let currentCategory = "todos";
let currentSearchQuery = "";

// ---------------------------------------------------------------------------
// DOM Elements
// ---------------------------------------------------------------------------
const connectionStatus = document.getElementById("connectionStatus");
const currentChannelName = document.getElementById("currentChannelName");
const currentTechnicalInfo = document.getElementById("currentTechnicalInfo");
const btnPower = document.getElementById("btnPower");
const powerText = document.getElementById("powerText");

const btnTogglePlay = document.getElementById("btnTogglePlay");
const btnMute = document.getElementById("btnMute");
const btnVolDown = document.getElementById("btnVolDown");
const btnVolUp = document.getElementById("btnVolUp");
const volumeIndicator = document.getElementById("volumeIndicator");
const btnFullscreen = document.getElementById("btnFullscreen");

const channelsContainer = document.getElementById("channelsContainer");
const channelSearch = document.getElementById("channelSearch");
const btnClearSearch = document.getElementById("btnClearSearch");
const channelCount = document.getElementById("channelCount");
const categoryNav = document.getElementById("categoryNav");

// Settings Modal Elements
const btnSettingsToggle = document.getElementById("btnSettingsToggle");
const btnCloseSettings = document.getElementById("btnCloseSettings");
const settingsModal = document.getElementById("settingsModal");
const chkAutostart = document.getElementById("chkAutostart");
const selDefaultChannel = document.getElementById("selDefaultChannel");
const selIdleMinutes = document.getElementById("selIdleMinutes");
const btnStopPlaybackModal = document.getElementById("btnStopPlaybackModal");
const btnShutdownApp = document.getElementById("btnShutdownApp");

// ---------------------------------------------------------------------------
// API Communication
// ---------------------------------------------------------------------------
async function fetchStatus() {
  try {
    const res = await fetch("/api/playback/status");
    if (!res.ok) throw new Error("Status error");
    const data = await res.json();
    updatePlaybackUI(data);
    setConnectionOnline(true);
  } catch (err) {
    setConnectionOnline(false);
  }
}

async function fetchChannels() {
  try {
    const res = await fetch("/api/channels");
    if (!res.ok) throw new Error("Channels fetch failed");
    allChannels = await res.json();
    channelCount.textContent = `${allChannels.length} canales`;
    updateCategoryBadges();
    applyFilterAndRender();
    populateSettingsChannels();
  } catch (err) {
    console.error("Error loading channels:", err);
  }
}

async function fetchSettings() {
  try {
    const res = await fetch("/api/settings");
    if (!res.ok) throw new Error("Settings fetch failed");
    currentSettings = await res.json();
    chkAutostart.checked = Boolean(currentSettings.autostart);
    if (currentSettings.default_channel) {
      selDefaultChannel.value = currentSettings.default_channel;
    }
    if (currentSettings.auto_stop_idle_minutes !== undefined) {
      selIdleMinutes.value = String(currentSettings.auto_stop_idle_minutes);
    }
  } catch (err) {
    console.error("Error loading settings:", err);
  }
}

async function playChannel(channelId) {
  try {
    currentTechnicalInfo.textContent = "Sintonizando canal y preparando pantalla completa...";
    const res = await fetch("/api/playback/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel_id: channelId }),
    });
    if (!res.ok) {
      const err = await res.json();
      alert(`Error al sintonizar: ${err.detail || "Fallo del servidor"}`);
    }
    await fetchStatus();
  } catch (err) {
    alert("Error de conexión al iniciar canal.");
  }
}

async function stopPlayback() {
  try {
    currentTechnicalInfo.textContent = "Cerrando navegador...";
    await fetch("/api/playback/stop", { method: "POST" });
    await fetchStatus();
  } catch (err) {
    alert("Error al detener reproducción.");
  }
}

async function sendControl(action) {
  try {
    const res = await fetch("/api/playback/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    const data = await res.json();
    if (data.video) {
      updateVideoDetails(data.video);
    }
  } catch (err) {
    console.error("Control failed:", err);
  }
}

async function saveSettingsPatch(patch) {
  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    currentSettings = await res.json();
  } catch (err) {
    alert("Error al guardar ajustes.");
  }
}

// ---------------------------------------------------------------------------
// UI State Updates
// ---------------------------------------------------------------------------
function setConnectionOnline(online) {
  if (online) {
    connectionStatus.className = "status-indicator online";
    connectionStatus.querySelector(".status-text").textContent = "SISTEMA ACTIVO";
  } else {
    connectionStatus.className = "status-indicator";
    connectionStatus.querySelector(".status-text").textContent = "DESCONECTADO";
  }
}

function updatePlaybackUI(status) {
  currentPlaybackState = status;

  if (status.active && status.channel) {
    connectionStatus.className = "status-indicator streaming";
    connectionStatus.querySelector(".status-text").textContent = "STREAMING ACTIVO";

    currentChannelName.textContent = status.channel.name;
    const v = status.video;
    if (v) {
      const res = v.width && v.height ? `${v.width}x${v.height}` : "1080p";
      const pausedText = v.paused ? " | Pausado" : " | En directo";
      currentTechnicalInfo.textContent = `Resolución: ${res} — Widevine DRM OK${pausedText}`;
      updateVideoDetails(v);
    } else {
      currentTechnicalInfo.textContent = "Reproduciendo en Chrome";
    }

    btnPower.className = "btn-power active";
    powerText.textContent = "APAGAR";
  } else {
    currentChannelName.textContent = "Sin Emisión Activa";
    currentTechnicalInfo.textContent = "Chrome inactivo — Sistema en espera";
    btnPower.className = "btn-power";
    powerText.textContent = "ENCENDER";
  }

  // Synchronize active highlights across all cards in DOM
  const currentId = status.channel ? status.channel.id : null;
  document.querySelectorAll(".channel-card").forEach((card) => {
    if (card.dataset.id === currentId) {
      card.classList.add("active");
    } else {
      card.classList.remove("active");
    }
  });
}

function updateVideoDetails(v) {
  if (v.volume !== undefined && v.volume !== null) {
    volumeIndicator.textContent = `${Math.round(v.volume * 100)}%`;
  }
  if (v.muted !== undefined) {
    btnMute.style.opacity = v.muted ? "0.4" : "1";
  }
  if (v.paused !== undefined) {
    btnTogglePlay.querySelector("span").textContent = v.paused ? "Reanudar" : "Pausar";
  }
}

function updateCategoryBadges() {
  const counts = { todos: allChannels.length };
  CATEGORIES.forEach((cat) => {
    if (cat.id !== "todos") {
      counts[cat.id] = allChannels.filter((c) => c.category === cat.id).length;
    }
  });

  for (const [catId, count] of Object.entries(counts)) {
    const badge = document.getElementById(`badge-${catId}`);
    if (badge) badge.textContent = String(count);
  }
}

// ---------------------------------------------------------------------------
// Card and Section Builders
// ---------------------------------------------------------------------------
function createChannelCard(ch) {
  const card = document.createElement("div");
  card.className = "channel-card";
  card.dataset.id = ch.id;

  const currentId = currentPlaybackState && currentPlaybackState.channel ? currentPlaybackState.channel.id : null;
  if (ch.id === currentId) {
    card.classList.add("active");
  }

  card.innerHTML = `
    <div class="channel-logo-wrap">
      <img class="channel-logo" src="${ch.logo_url || ''}" alt="${ch.name}" loading="lazy" onerror="this.style.display='none'">
    </div>
    <span class="channel-name">${ch.name}</span>
  `;

  card.addEventListener("click", () => playChannel(ch.id));
  return card;
}

function buildSectionBlock(categoryMeta, channelsList) {
  const section = document.createElement("section");
  section.className = "category-block";
  section.dataset.category = categoryMeta.id;

  const header = document.createElement("div");
  header.className = "category-block-header";
  header.innerHTML = `
    <div class="category-block-title-wrap">
      <h3 class="category-block-title">${categoryMeta.name}</h3>
      <span class="category-block-count">${channelsList.length}</span>
    </div>
  `;

  const grid = document.createElement("div");
  grid.className = "channels-grid";

  channelsList.forEach((ch) => {
    grid.appendChild(createChannelCard(ch));
  });

  section.appendChild(header);
  section.appendChild(grid);
  return section;
}

function applyFilterAndRender() {
  channelsContainer.innerHTML = "";

  const query = currentSearchQuery.trim().toLowerCase();

  // Mode 1: Search active across channels
  if (query) {
    const matched = allChannels.filter((ch) => {
      const matchName = ch.name.toLowerCase().includes(query);
      const matchId = ch.id.toLowerCase().includes(query);
      const matchCode = ch.code ? ch.code.toLowerCase().includes(query) : false;
      return matchName || matchId || matchCode;
    });

    if (matched.length === 0) {
      channelsContainer.innerHTML = `
        <div class="empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <p>No se encontraron canales para "${currentSearchQuery}"</p>
          <button class="btn-clear-search-text" id="btnResetSearch">Limpiar búsqueda</button>
        </div>
      `;
      const btnReset = document.getElementById("btnResetSearch");
      if (btnReset) {
        btnReset.addEventListener("click", () => {
          channelSearch.value = "";
          currentSearchQuery = "";
          btnClearSearch.classList.add("hidden");
          applyFilterAndRender();
        });
      }
      return;
    }

    const searchSection = buildSectionBlock(
      { id: "search", name: `Resultados (${matched.length})` },
      matched
    );
    channelsContainer.appendChild(searchSection);
    return;
  }

  // Mode 2: Specific category selected
  if (currentCategory !== "todos") {
    const catMeta = CATEGORIES.find((c) => c.id === currentCategory) || {
      id: currentCategory,
      name: currentCategory,
    };
    const catChannels = allChannels.filter((c) => c.category === currentCategory);

    if (catChannels.length === 0) {
      channelsContainer.innerHTML = `<div class="empty-state"><p>No hay canales en esta sección.</p></div>`;
      return;
    }

    const block = buildSectionBlock(catMeta, catChannels);
    channelsContainer.appendChild(block);
    return;
  }

  // Mode 3: "Todos" selected -> Render grouped by categories
  CATEGORIES.forEach((cat) => {
    if (cat.id === "todos") return;
    const catChannels = allChannels.filter((c) => c.category === cat.id);
    if (catChannels.length > 0) {
      channelsContainer.appendChild(buildSectionBlock(cat, catChannels));
    }
  });
}

function populateSettingsChannels() {
  selDefaultChannel.innerHTML = "";
  allChannels.forEach((ch) => {
    const opt = document.createElement("option");
    opt.value = ch.id;
    opt.textContent = ch.name;
    selDefaultChannel.appendChild(opt);
  });
  if (currentSettings && currentSettings.default_channel) {
    selDefaultChannel.value = currentSettings.default_channel;
  }
}

// ---------------------------------------------------------------------------
// Event Listeners
// ---------------------------------------------------------------------------
btnPower.addEventListener("click", () => {
  if (currentPlaybackState && currentPlaybackState.active) {
    stopPlayback();
  } else {
    const target = (currentSettings && currentSettings.default_channel) || "la_1";
    playChannel(target);
  }
});

btnTogglePlay.addEventListener("click", () => sendControl("toggle_play"));
btnMute.addEventListener("click", () => sendControl("mute"));
btnVolDown.addEventListener("click", () => sendControl("volume_down"));
btnVolUp.addEventListener("click", () => sendControl("volume_up"));
btnFullscreen.addEventListener("click", () => sendControl("fullscreen"));

// Category Pills Navigation
if (categoryNav) {
  categoryNav.addEventListener("click", (e) => {
    const pill = e.target.closest(".category-pill");
    if (!pill) return;

    const catId = pill.dataset.category;
    if (!catId) return;

    currentCategory = catId;

    categoryNav.querySelectorAll(".category-pill").forEach((btn) => {
      btn.classList.toggle("active", btn === pill);
    });

    // Clear search on category switch for cleaner UX
    if (currentSearchQuery) {
      currentSearchQuery = "";
      channelSearch.value = "";
      btnClearSearch.classList.add("hidden");
    }

    applyFilterAndRender();

    // Smooth scroll pill into view on mobile
    pill.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  });
}

// Search handling with clear button
channelSearch.addEventListener("input", (e) => {
  currentSearchQuery = e.target.value.trim();
  if (currentSearchQuery) {
    btnClearSearch.classList.remove("hidden");
  } else {
    btnClearSearch.classList.add("hidden");
  }
  applyFilterAndRender();
});

btnClearSearch.addEventListener("click", () => {
  channelSearch.value = "";
  currentSearchQuery = "";
  btnClearSearch.classList.add("hidden");
  channelSearch.focus();
  applyFilterAndRender();
});

// Settings Modal
btnSettingsToggle.addEventListener("click", () => {
  settingsModal.classList.remove("hidden");
  fetchSettings();
});

btnCloseSettings.addEventListener("click", () => {
  settingsModal.classList.add("hidden");
});

settingsModal.addEventListener("click", (e) => {
  if (e.target === settingsModal) {
    settingsModal.classList.add("hidden");
  }
});

chkAutostart.addEventListener("change", (e) => {
  saveSettingsPatch({ autostart: e.target.checked });
});

selDefaultChannel.addEventListener("change", (e) => {
  saveSettingsPatch({ default_channel: e.target.value });
});

selIdleMinutes.addEventListener("change", (e) => {
  saveSettingsPatch({ auto_stop_idle_minutes: parseInt(e.target.value, 10) });
});

btnStopPlaybackModal.addEventListener("click", () => {
  stopPlayback();
  settingsModal.classList.add("hidden");
});

btnShutdownApp.addEventListener("click", async () => {
  if (confirm("¿Seguro que deseas apagar el servidor y cerrar el controlador?")) {
    try {
      await fetch("/api/system/shutdown", { method: "POST" });
      alert("Servidor apagado.");
      window.close();
    } catch (e) {
      window.location.reload();
    }
  }
});

// ---------------------------------------------------------------------------
// Initialization & Polling
// ---------------------------------------------------------------------------
fetchChannels();
fetchStatus();
fetchSettings();
setInterval(fetchStatus, 2500);
