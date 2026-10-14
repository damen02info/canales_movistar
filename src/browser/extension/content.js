// ---------------------------------------------------------------------------
// Content Script: Movistar Plus+ DOM Automation & Player Control
// ---------------------------------------------------------------------------

let currentChannel = null;

// ---------------------------------------------------------------------------
// Helpers: Dialogs, Selectors and Video Introspection
// ---------------------------------------------------------------------------

function dismissOverlays() {
  // Cookie banner
  const cookieBtn = document.querySelector("#onetrust-accept-btn-handler");
  if (cookieBtn && cookieBtn.offsetParent !== null) {
    cookieBtn.click();
  }

  // Error modal confirmation buttons (e.g. PL01 or generic dialogs)
  const buttons = document.querySelectorAll("button");
  for (const btn of buttons) {
    const text = btn.textContent.trim().toUpperCase();
    if (text === "ACEPTAR" && btn.offsetParent !== null) {
      btn.click();
      break;
    }
  }
}

function findChannelButton(channelName) {
  const target = channelName.trim().toLowerCase();
  const imgs = document.querySelectorAll("button.poster img[alt]");
  for (const img of imgs) {
    const alt = img.getAttribute("alt") || "";
    if (alt.trim().toLowerCase() === target) {
      return img.closest("button.poster");
    }
  }
  return null;
}

function getVideoDetails() {
  const v = document.querySelector("video");
  if (!v) return null;
  return {
    paused: v.paused,
    readyState: v.readyState,
    width: v.videoWidth,
    height: v.videoHeight,
    volume: v.volume,
    muted: v.muted,
  };
}

async function waitForVideo(timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    dismissOverlays();
    const v = document.querySelector("video");
    if (v && v.readyState >= 1) {
      return v;
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  const v = document.querySelector("video");
  if (v) return v;
  throw new Error("Timeout waiting for player video element");
}

function teardownActivePlayer() {
  const v = document.querySelector("video");
  if (v) {
    try {
      v.pause();
      v.removeAttribute("src");
      v.load();
    } catch (_) {}
  }
  const backBtn = document.querySelector(
    "button[aria-label*='Volver' i], button[class*='back' i], .player-header button"
  );
  if (backBtn) {
    backBtn.click();
  }
}

// ---------------------------------------------------------------------------
// Core Actions: Play Channel, Control and Status
// ---------------------------------------------------------------------------

async function playChannel(channelInfo) {
  const channelName = channelInfo.name;
  dismissOverlays();

  // 1. Teardown existing player and return to grid if needed
  teardownActivePlayer();
  await new Promise((r) => setTimeout(r, 200));

  if (!window.location.pathname.includes("/canales")) {
    window.location.href = "https://ver.movistarplus.es/canales";
    return { status: "navigating", channel: channelInfo };
  }

  // 2. Locate channel button in virtualized grid with incremental scrolling
  window.scrollTo(0, 0);
  await new Promise((r) => setTimeout(r, 250));

  let btn = findChannelButton(channelName);
  for (let attempt = 0; attempt < 30 && !btn; attempt++) {
    window.scrollBy(0, 1000);
    await new Promise((r) => setTimeout(r, 250));
    btn = findChannelButton(channelName);
  }

  if (!btn) {
    throw new Error(`Canal '${channelName}' no encontrado en la parrilla.`);
  }

  // 3. Scroll to element and trigger click
  btn.scrollIntoView({ behavior: "instant", block: "center" });
  await new Promise((r) => setTimeout(r, 150));
  btn.click();

  // 4. Check for warning dialogs right after click
  await new Promise((r) => setTimeout(r, 500));
  dismissOverlays();

  // 5. Wait for video element initialization
  const video = await waitForVideo(15000);

  // 6. Direct keyboard fullscreen trigger ('f')
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "f", code: "KeyF", bubbles: true }));
  await new Promise((r) => setTimeout(r, 300));

  currentChannel = channelInfo;
  return {
    status: "playing",
    channel: channelInfo,
    video: getVideoDetails(),
  };
}

function handleMediaControl(action) {
  const act = action.toLowerCase();
  const v = document.querySelector("video");

  if (!v) {
    throw new Error("No active video element found.");
  }

  if (act === "play") {
    v.play();
  } else if (act === "pause") {
    v.pause();
  } else if (act === "toggle_play" || act === "toggle") {
    if (v.paused) v.play();
    else v.pause();
  } else if (act === "fullscreen") {
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "f", code: "KeyF", bubbles: true }));
  } else if (act === "mute") {
    v.muted = !v.muted;
  } else if (act === "volume_up") {
    v.muted = false;
    v.volume = Math.min(1.0, v.volume + 0.1);
  } else if (act === "volume_down") {
    v.volume = Math.max(0.0, v.volume - 0.1);
  } else {
    throw new Error(`Unsupported action: ${action}`);
  }

  return { status: "ok", action_applied: act, video: getVideoDetails() };
}

function getStatus() {
  const details = getVideoDetails();
  const isPlaying = details && !details.paused;
  return {
    active: details !== null,
    state: isPlaying ? "playing" : details ? "paused" : "stopped",
    channel: currentChannel,
    video: details,
  };
}

// ---------------------------------------------------------------------------
// Message Dispatcher from Background Service Worker
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const { action } = message;

  (async () => {
    try {
      let data = null;
      if (action === "play_channel") {
        data = await playChannel(message.channel);
      } else if (action === "control") {
        data = handleMediaControl(message.control_action);
      } else if (action === "status") {
        data = getStatus();
      } else {
        throw new Error(`Unknown action: ${action}`);
      }
      sendResponse({ data });
    } catch (err) {
      sendResponse({ error: err.message || String(err) });
    }
  })();

  return true; // Keep message channel open for asynchronous response
});
