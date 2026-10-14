// ---------------------------------------------------------------------------
// Background Service Worker: WebSocket Bridge & Tab Dispatcher
// ---------------------------------------------------------------------------

const WS_URL = "ws://127.0.0.1:8765/ws/browser";
let socket = null;
let reconnectTimer = null;

// Connect to local FastAPI WebSocket endpoint
function connectWebSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  try {
    socket = new WebSocket(WS_URL);
  } catch (err) {
    scheduleReconnect();
    return;
  }

  socket.onopen = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    socket.send(JSON.stringify({ type: "handshake", client: "chrome_extension" }));
  };

  socket.onmessage = async (event) => {
    try {
      const message = JSON.parse(event.data);
      const { id, action } = message;

      if (action === "ping") {
        socket.send(JSON.stringify({ id, ok: true, data: "pong" }));
        return;
      }

      const response = await dispatchToMovistarTab(message);
      socket.send(JSON.stringify({ id, ok: true, data: response }));
    } catch (err) {
      socket.send(JSON.stringify({ id: message?.id, ok: false, error: err.message || String(err) }));
    }
  };

  socket.onerror = () => {
    scheduleReconnect();
  };

  socket.onclose = () => {
    scheduleReconnect();
  };
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectWebSocket();
  }, 2000);
}

// ---------------------------------------------------------------------------
// Tab resolution and message forwarding
// ---------------------------------------------------------------------------

async function getOrOpenMovistarTab() {
  const tabs = await chrome.tabs.query({ url: "*://ver.movistarplus.es/*" });
  if (tabs.length > 0) {
    return tabs[0];
  }

  // If no tab exists, navigate current or create new
  const createdTab = await chrome.tabs.create({ url: "https://ver.movistarplus.es/canales", active: true });
  // Wait for tab to complete loading
  await new Promise((resolve) => {
    const listener = (tabId, info) => {
      if (tabId === createdTab.id && info.status === "complete") {
        chrome.tabs.onUpdated.removeListener(listener);
        resolve(null);
      }
    };
    chrome.tabs.onUpdated.addListener(listener);
    setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      resolve(null);
    }, 15000);
  });
  return createdTab;
}

async function dispatchToMovistarTab(message) {
  const tab = await getOrOpenMovistarTab();
  if (!tab || !tab.id) {
    throw new Error("Could not find or open Movistar Plus+ tab");
  }

  // Ensure content script is ready before sending message
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tab.id, message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else if (response && response.error) {
        reject(new Error(response.error));
      } else {
        resolve(response ? response.data : null);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Worker lifecycle initialization
// ---------------------------------------------------------------------------
connectWebSocket();

// Periodic heartbeat to prevent service worker from going idle
setInterval(() => {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    connectWebSocket();
  }
}, 5000);
