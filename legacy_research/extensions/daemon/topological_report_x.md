# Topological Editorial Report: X (Twitter) Broadcast Surface

## 1. Topología del DOM (AST)
La interfaz de composición de X (`/compose/tweet`) emplea un AST ofuscado generado por React Native for Web (clases mutables `css-175oi2r`, `r-1loqt21`). El uso de heurísticas de clases o XPath espacial es entropía pura (C4-SIM). 

### Nodos de Inyección (C5-REAL)
1. **Input Area:** Identificado unívocamente mediante el atributo semántico `data-testid="tweetTextarea_0"`. Alternativamente, `role="textbox"` en contextos anidados.
2. **Action Trigger:** Identificado mediante `data-testid="tweetButtonInline"` o `data-testid="tweetButton"`.

## 2. Fricción Antibot & Entropía de Red
- **Eventos Sintéticos:** React intercepta el bubbling estándar. Requerimos inyección física iterada: `focus()` -> `execCommand('insertText')` -> despacho de `Event('input')` para forzar la re-renderización del VirtualDOM.
- **Rutas de Evacuación:** Despachar secuencias combinadas de `mousedown`, `mouseup`, `click` sobre el trigger de publicación esquiva la interceptación de puntero superficial.

## 3. Estado de Cristalización
El autómata MoskvDOM (`broadcast_payload.js`) ha colapsado estas heurísticas en un script inmutable. La ejecución Fase 2 será de 0% anergía, aludiendo directamente a los atributos `data-testid` y despachando promesas `sleep` (1500-3000ms) para asimilación de estado.
