# Topological Editorial Report: B2B Lead Extraction Surface (LinkedIn / X)

## 1. Topología del DOM (AST)
LinkedIn y Sales Navigator emplean sistemas de renderizado complejos (Ember.js / React) con atributos semánticos específicos. X (Twitter) usa React Native for Web. Ambas plataformas ofuscan las clases CSS mediante hashes dinámicos.

### Nodos de Extracción (C5-REAL)
1. **Sales Navigator (Perfiles):** Enlaces a perfiles con el atributo `data-anonymize="person-name"`.
2. **Búsqueda Estándar (LinkedIn):** Estructura anidada `span.entity-result__title-text a` o enlaces con la clase `.app-aware-link`.
3. **X (Twitter/Search):** Atributo semántico `data-testid="User-Name"` apuntando a la tarjeta del usuario.

## 2. Invariante de Datos
La extracción se reduce a un mapeo isomórfico (Φ5) de nodos del tipo `HTMLAnchorElement` filtrando por el patrón de ruta del perfil (`/in/`, `/sales/people/`, `/x.com/`, `/twitter.com/`). La consistencia del Grafo se garantiza mediante la deduplicación basada en URLs absolutas en el lado de la memoria intermedia del cliente.

## 3. Estado de Cristalización
El payload `extract_leads_payload.js` contiene los selectores exactos cristalizados para extraer y estructurar perfiles directamente en la consola sin inicializar APIs propietarias.
