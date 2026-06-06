<!-- [C5-REAL] Exergy-Maximized -->
# Chrome Web Store Metadata: CORTEX-Persist Mafia AI Blocker

This document is the single source of truth for the Chrome Web Store listing. Copy and paste these fields directly into the Chrome Developer Dashboard.

## 1. Store Listing Details

**Item Name (Max 45 chars):** 
CORTEX: Mafia AI Blocker

**Summary (Max 132 chars):**
Filtro epistémico C5-REAL. Detecta y bloquea cuentas de alta influencia social sin output técnico empírico (Alto Smoke Index).

**Detailed Description:**
El ecosistema de Inteligencia Artificial está saturado de ruido. La "Mafia AI" es una cámara de eco donde cientos de cuentas generan legitimidad social cruzada (retweets, menciones cruzadas en newsletters y podcasts) sin aportar tracción real o código open-source.

CORTEX: Mafia AI Blocker actúa como tu sistema inmunológico digital (Firewall Cognitivo). Escanea tu feed en X (Twitter), LinkedIn y Substack. Si detecta la mención de un nodo clasificado con un alto "Índice de Humo" (Centralidad de red masiva dividida por output real en GitHub nulo), ofusca inmediatamente ese contenido con un filtro borroso y un overlay de advertencia.

Deja de consumir ruido térmico. Enfoca tu atención (Exergy) solo en los verdaderos *builders*.

## 2. Permissions Justification

El equipo de revisión de la Chrome Web Store rechazará la extensión si no justificamos exactamente por qué pedimos cada permiso. Usa estas justificaciones en el dashboard:

*   **`storage`:**
    *   *Justification:* Requerido para almacenar localmente el contador de intercepciones y la configuración de estado de la extensión, permitiendo que las estadísticas de bloqueo persistan entre sesiones sin transmitir datos a servidores externos.
*   **`host_permissions` (`*://*.twitter.com/*`, `*://*.x.com/*`, `*://*.substack.com/*`, `*://*.linkedin.com/*`):**
    *   *Justification:* Requerido para inyectar el content script ("content.js") exclusivamente en las plataformas sociales objetivo. El script necesita leer el DOM localmente para detectar menciones de texto y ofuscar los elementos HTML que contienen ruido térmico. No se extraen ni exfiltran datos de navegación.

## 3. Privacy & Data Use

*   **Single Purpose:** Bloquear ruido narrativo en plataformas sociales.
*   **Data Collection:** No. La extensión opera de manera 100% local. La lista negra (`blacklist.js`) está pre-empaquetada en la extensión. El escaneo del DOM ocurre en el navegador del usuario y el conteo de bloqueos se guarda en el `chrome.storage.local`.
*   **Data Transmission:** Ninguna. Cero llamadas a red salientes.
*   **Privacy Policy URL:** (El usuario debe proveer un enlace a un Gist o Notion público con una política de privacidad que declare que no hay recolección de datos).

## 4. Assets Requirements (To Do)

Antes de publicar, necesitarás subir estos archivos al Dashboard (no van dentro del ZIP):
*   **Store Icon:** 1 imagen PNG de 128x128 píxeles.
*   **Screenshots:** Al menos 1 captura de pantalla (1280x800 o 640x400) mostrando un tweet ofuscado por la extensión.
*   **Promo Tile (Opcional):** 440x280 PNG.

## 5. Version History
*   **v1.0.0:** Lanzamiento inicial C5-REAL. Inyección de blacklist compilada, soporte para X/Twitter y Substack, contador en el popup.
