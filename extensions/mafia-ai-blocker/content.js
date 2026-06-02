// CORTEX PERSIST: DOM OBSERVER & OBFUSCATOR
// Reality Level: C5-REAL

// MAFIA_AI_BLACKLIST is loaded from blacklist.js

let obfuscatedCount = 0;

function censorNode(element, nodeName) {
    if (element.dataset.cortexCensored === "true") return;
    
    // Marcar como censurado para no repetir
    element.dataset.cortexCensored = "true";
    
    // Obfuscación agresiva C5-REAL
    element.style.filter = "blur(8px) grayscale(100%)";
    element.style.opacity = "0.2";
    element.style.pointerEvents = "none";
    element.style.transition = "all 0.3s ease";
    
    // Añadir overlay de aviso
    const overlay = document.createElement("div");
    overlay.innerText = `[ BLOQUEO C5-REAL ]\nRuido Térmico: @${nodeName}\nSmoke Index > 10.0`;
    overlay.style.position = "absolute";
    overlay.style.top = "50%";
    overlay.style.left = "50%";
    overlay.style.transform = "translate(-50%, -50%)";
    overlay.style.color = "#ff3333";
    overlay.style.backgroundColor = "rgba(10, 10, 10, 0.9)";
    overlay.style.border = "1px solid #ff3333";
    overlay.style.padding = "10px";
    overlay.style.fontWeight = "bold";
    overlay.style.fontFamily = "monospace";
    overlay.style.zIndex = "9999";
    overlay.style.textAlign = "center";
    
    // Asegurar que el padre sea relativo para posicionar el overlay
    if (window.getComputedStyle(element).position === "static") {
        element.style.position = "relative";
    }
    
    element.appendChild(overlay);
    
    obfuscatedCount++;
    chrome.storage.local.set({ obfuscatedCount });
}

function scanDOM() {
    if (!window.MAFIA_AI_BLACKLIST) return;
    
    // 1. Twitter / X (Busca enlaces a perfiles y data-testids)
    const links = document.querySelectorAll("a[href^='/']");
    links.forEach(link => {
        const username = link.getAttribute("href").replace("/", "").split("?")[0].toLowerCase();
        if (MAFIA_AI_BLACKLIST.includes(username)) {
            // Subir al contenedor del tweet (aproximación genérica)
            const tweet = link.closest("article") || link.closest("[data-testid='cellInnerDiv']");
            if (tweet) {
                censorNode(tweet, username);
            }
        }
    });
    
    // 2. Substack (Busca data-substacks o hrefs)
    const substackLinks = document.querySelectorAll("a[href*='.substack.com']");
    substackLinks.forEach(link => {
        try {
            const url = new URL(link.href);
            const subdomain = url.hostname.split(".")[0].toLowerCase();
            if (MAFIA_AI_BLACKLIST.includes(subdomain)) {
                const article = link.closest("div.post-preview") || link.closest("article") || link.parentElement;
                if (article) censorNode(article, subdomain);
            }
        } catch(e) {}
    });
}

// Ejecutar escaneo inicial
setTimeout(scanDOM, 1000);

// Observar mutaciones (scroll infinito)
const observer = new MutationObserver((mutations) => {
    let shouldScan = false;
    for (let m of mutations) {
        if (m.addedNodes.length > 0) {
            shouldScan = true;
            break;
        }
    }
    if (shouldScan) {
        // Debounce simple
        clearTimeout(window.cortexScanTimer);
        window.cortexScanTimer = setTimeout(scanDOM, 300);
    }
});

observer.observe(document.body, { childList: true, subtree: true });
