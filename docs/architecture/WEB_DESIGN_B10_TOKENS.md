# BLOQUE B10: DESIGN TOKENS Y VARIABLES CSS
> Nodos Epistémicos 0901 → 1000
> Nivel: ARQUITECTO | Ontología: C5-REAL | Validación: Sanhedrin

## 1. Fundamentos de Design Tokens (0901-0910)
**WEB-DESIGN-0901**: Los Design Tokens no son meras variables de CSS; son la "Fuente de Verdad" agnóstica a la tecnología que codifica el ADN completo de un sistema de diseño.
**WEB-DESIGN-0902**: Extraen el diseño visual (UI) y lo convierten en datos estructurados (generalmente JSON). Si el diseño no puede representarse en JSON, su entropía es inmanejable.
**WEB-DESIGN-0903**: Un token encapsula "decisiones de diseño" atómicas: colores, tipografías, espaciados, opacidades, duraciones de animación, y elevaciones (z-index, sombras).
**WEB-DESIGN-0904**: Reemplazan los "Magic Numbers" en el código. Nunca hardcodees un `#4b90fe` o `16px`; referencia un token `color-brand-primary` o `spacing-md`.
**WEB-DESIGN-0905**: Agnósticos de plataforma: El mismo token JSON engendra Variables CSS para Web, archivos XML para Android, y Swift Enums para iOS mediante transpiladores.
**WEB-DESIGN-0906**: Reducen drásticamente la latencia de re-branding. Cambiar el token maestro de marca muta atómicamente cientos de vistas y plataformas al unísono.
**WEB-DESIGN-0907**: Fomentan la consistencia entrópica cero: Los diseñadores no inventan nuevos matices de gris para cada pantalla; se ven obligados a elegir del menú de tokens.
**WEB-DESIGN-0908**: Habilitan el desarrollo concurrente. Diseño y Desarrollo operan sincronizados bajo el mismo contrato de API (los Tokens), eliminando fricción de traspaso.
**WEB-DESIGN-0909**: Aliasing: Un token puede referenciar a otro token. Esta referencialidad topológica construye sistemas jerárquicos (Primitivo -> Semántico).
**WEB-DESIGN-0910**: El formato W3C Design Tokens Community Group (DTCG) emerge como el estándar universal JSON. Adoptar especificaciones propietarias es incurrir en deuda técnica temprana.

## 2. Tipología y Jerarquía (0911-0920)
**WEB-DESIGN-0911**: Jerarquía de tres niveles: Nivel 1 (Tokens Primitivos / Core), Nivel 2 (Tokens Semánticos / Alias), Nivel 3 (Tokens de Componente / Específicos).
**WEB-DESIGN-0912**: Nivel 1 (Primitivos): Valores absolutos. Describen qué son visualmente sin connotar su uso. Ej: `color-blue-500: #3B82F6`, `spacing-4: 16px`.
**WEB-DESIGN-0913**: Nivel 2 (Semánticos): Extraen intención y contexto referenciando el Nivel 1. Describen para qué se usan. Ej: `color-action-primary: {color-blue-500}`.
**WEB-DESIGN-0914**: Las paletas Semánticas garantizan resiliencia ante Themes. En Modo Oscuro, el semántico muta a `color-blue-400`, pero la lógica no cambia. Nunca asignes colores fijos a contextos.
**WEB-DESIGN-0915**: Nivel 3 (Componentes): Atados estructuralmente a un widget. Ej: `button-primary-background: {color-action-primary}`. Extremadamente granulares.
**WEB-DESIGN-0916**: Evita abusar del Nivel 3 si tu UI es pequeña. El mantenimiento del Nivel 3 (Tokens para cada botón individual) explota la complejidad sin beneficio exérgico a menos que operes a escala Enterprise.
**WEB-DESIGN-0917**: Convenciones de nomenclatura (Naming Conventions). Usa un formato determinista estricto: `categoría-concepto-propiedad-estado`. (ej: `color-background-interactive-hover`).
**WEB-DESIGN-0918**: El Naming debe escalar de general a específico. Esto coincide maravillosamente con el autocompletado del IDE e Intelligense (IntelliSense agrupa prefijos).
**WEB-DESIGN-0919**: Design Tokens no son solo estilos; incluyen lógicas estructurales como `breakpoint-md: 768px` y z-indexes (`z-index-modal: 100`).
**WEB-DESIGN-0920**: Mantén el vocabulario C5-REAL unificado: Si en diseño se llama "Elevación", en CSS debe ser `elevation`, no `box-shadow`. 1-a-1 sin distorsión cognitiva.

## 3. Variables CSS (Custom Properties) Mecánica (0921-0930)
**WEB-DESIGN-0921**: A diferencia de variables preprocesadas de SASS (`$var`), las CSS Custom Properties (`--var`) viven en el DOM (Render Tree), responden a la cascada y son mutables en tiempo de ejecución.
**WEB-DESIGN-0922**: Se declaran usualmente en la pseudo-clase `:root` para acceso global.
**WEB-DESIGN-0923**: Resolución dinámica: Alterar una CSS Variable a través de Javascript (`el.style.setProperty('--x', val)`) fuerza un recálculo atómico solo en el sub-árbol afectado. Superior al inline styles JS en batch.
**WEB-DESIGN-0924**: Fallbacks nativos: Usa `var(--my-color, red)`. Si la variable no está definida en la cascada, el navegador inyecta el valor fallback sin invalidar CSS.
**WEB-DESIGN-0925**: Componentes modulares inyectando CSS Props. Define variables vacías o con defaults en los selectores del componente y altera su valor en la instancia o modificador.
**WEB-DESIGN-0926**: Cadenas matemáticas con `calc()`. Combinar tokens genera exergía relacional: `width: calc(100vw - var(--spacing-layout-side) * 2)`.
**WEB-DESIGN-0927**: `env()` inyecta variables del User Agent (el sistema operativo). Crucial en PWA y Notch iOS: `padding-top: env(safe-area-inset-top)`.
**WEB-DESIGN-0928**: Herencia implacable: Una variable CSS penetra dentro de Web Components cerrados (Shadow DOM). Es la única directiva CSS que traspasa el encapsulamiento Shadow de manera legal y nativa.
**WEB-DESIGN-0929**: Las variables CSS no se pueden animar de manera fluida si son genéricas; el navegador las interpola como *string flips*.
**WEB-DESIGN-0930**: `@property` Houdini API (CSS Properties and Values API): Permite declarar tipo, sintaxis y animabilidad estricta para una Custom Property. Permitiendo así interpolación lineal a 60fps de un token (ej. transicionar ángulos de gradiente o números enteros).

## 4. Escalas Topológicas y de Layout (0931-0940)
**WEB-DESIGN-0931**: Los valores arbitrarios (17px, 23px) son Entropía pura. Utiliza sistemas de grilla base-4, base-8 o base-10. Base-8 es el estándar predominante en densidades de pantalla modernas.
**WEB-DESIGN-0932**: Sistema de espaciado: `spacing-1` (4px), `spacing-2` (8px), `spacing-3` (12px), `spacing-4` (16px), etc. Crea un ritmo vertical y horizontal imperturbable.
**WEB-DESIGN-0933**: El Ojo Humano percibe relaciones geométricas y logarítmicas, no sumas lineales. La escala de espacios mayores debe incrementar no-linealmente (16, 24, 32, 48, 64, 96, 128).
**WEB-DESIGN-0934**: Radios de Esquina (Border-radius): 3 o 4 niveles son suficientes. `radius-sm` (2px, check/inputs), `radius-md` (4px, botones), `radius-lg` (8px, modales), `radius-pill` (9999px). Mezclarlos sin coherencia erosiona la madurez de la UI.
**WEB-DESIGN-0935**: Elevación (Z-Index) debe ser finita. No uses `z-index: 9999`. Declara `z-base`, `z-dropdown` (100), `z-sticky` (200), `z-modal` (300), `z-toast` (400).
**WEB-DESIGN-0936**: Sombra proyectada (Box-shadow) es el token óptico de elevación sobre el eje Z (Profundidad material). Menor elevación = sombra nítida, corta y oscura. Mayor elevación = sombra difusa, lejana y tenue.
**WEB-DESIGN-0937**: Tamaños fijos (Width/Height) deben restringirse a tokens iconográficos (ej. `size-icon-sm: 16px`). Cajas de contenido jamás usan altura fija tokenizada; delegan al relleno y geometría flex.
**WEB-DESIGN-0938**: Contenedores Máximos (Max-width): Los anchos de lectura se tokenizan (`layout-max-article: 65ch`, `layout-max-fluid: 1440px`).
**WEB-DESIGN-0939**: Breakpoints. Trátalos como tokens funcionales (`bp-sm`, `bp-md`, `bp-lg`). Mobile-first exige construir con `min-width: var(--bp-md)` en los media queries (Nativos CSS Nesting Media/Custom Media).
**WEB-DESIGN-0940**: El flujo es fluido pero anclado. Usa `clamp(min, fluid, max)` y pásale tokens de escala para layouts intrínsecamente elásticos que colapsan orgánicamente a densidades móviles.

## 5. Tipografía y Escalas Modulares (0941-0950)
**WEB-DESIGN-0941**: La Tipografía requiere dos escalas combinadas: Fluid Type Scale (Tamaño Matemático) y Weight Scale (Peso/Grosor).
**WEB-DESIGN-0942**: Aplica Escala Modular para establecer tamaños de fuente derivados de una Ratio Matemática (ej. Ratio Áurea 1.618 o Cuarta Perfecta 1.333). Si base es 16px, H3 = $16 \times 1.333^2$.
**WEB-DESIGN-0943**: Interlineado Semántico (Line-height). Mayor tamaño de fuente exige Menor line-height óptico. Texto base (`1.5`), Encabezados Masivos (`1.1` o `1`). No usar nunca `px` absoluto para line-height; siempre multiplicadores sin unidad.
**WEB-DESIGN-0944**: Tracking (Letter-spacing). Fuentes pequeñas o en mayúsculas exigen tracking positivo expansivo (`0.05em`). Titulares pesados exigen tracking negativo restrictivo (`-0.02em`).
**WEB-DESIGN-0945**: Escalas Fluidas C5-REAL. Definir el token de tamaño de fuente usando interpolación lineal matemática dependiente de viewport: `font-size: clamp(1rem, 0.8rem + 1vw, 1.25rem)`. Elimina millones de líneas de Media Queries.
**WEB-DESIGN-0946**: Agrupación tipográfica: El concepto "Heading 1" en Diseño contiene tokens de `size`, `weight`, `line-height` y `letter-spacing`. Transmútalo en una Clase Utilitaria o Mixin (`.text-heading-1`) antes de delegar a CSS nativo puro.
**WEB-DESIGN-0947**: Estandariza la pila de fuentes de sistema (System Fonts Stack) para tiempos de carga $LCP = 0ms$. Si la marca requiere exergía absoluta, usa `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto...`
**WEB-DESIGN-0948**: Variables Font (Fuentes Variables). Un solo archivo aglutina miles de combinaciones de peso (`wght`), anchura (`wdth`), óptica (`opsz`), y cursiva (`ital`). Mutarlas fluidamente es inofensivo para el VRAM de la máquina.
**WEB-DESIGN-0949**: Contraste Topográfico. La lectura prolongada rechaza el negro puro (`#000000`). Sustituye con tokens de carbón o grafito (`#1A1A1A`) para amortiguar el astigmatismo digital.
**WEB-DESIGN-0950**: Alineamiento vertical óptico. Las mayúsculas y números (Cap-Height) varían frente al cuadro EM. CSS `cap-height` metrics (experimental) permite la alineación determinista real.

## 6. Teoría del Color, Temas y Dark Mode (0951-0960)
**WEB-DESIGN-0951**: HSL/LCH son ontológicamente superiores a HEX/RGB en diseño. Permiten mutaciones lógicas ("Hazlo 10% más claro ajustando Lightness") imposibles de formular deterministamente en Hexadecimal atómico.
**WEB-DESIGN-0952**: Oklch y Oklab (Espacios de Color Perceptualmente Uniformes). La base C5-REAL del Siglo XXI. Transicionan gradientes entre dos colores anulando la distorsión del gris desaturado en el espectro. Soporte Web total.
**WEB-DESIGN-0953**: Paleta Tonal: Genera 10 escalas (50, 100, 200... 900) variando luminosidad sobre un Hue anclado. Usa `500` como color base. Nivel Primitivo.
**WEB-DESIGN-0954**: Modos de Tema Dinámico (Light/Dark). El Tema no es intercambiar clases arbitrariamente; es conmutar las referencias de Semántico a Primitivo.
**WEB-DESIGN-0955**: CSS nativo invierte temas con el Media Query `@media (prefers-color-scheme: dark)`. Sobreescribe la raíz `--color-bg-primary: var(--color-gray-900)`.
**WEB-DESIGN-0956**: Dark Mode no es fondo negro puro (AMOLED black). Usa Grises neutros profundos (`#111827`) o teñidos del Hue primario de marca para bajar el contraste hiriente, mitigar "smearing" de píxeles OLED y proyectar elevación de sombras invertida.
**WEB-DESIGN-0957**: Sombras en Modo Oscuro son fotónicamente invisibles contra fondos negros. Emplea la atenuación de Lightness o un finísimo sub-border (`border: 1px solid rgba(255,255,255, 0.1)`) para segregar tarjetas elevadas.
**WEB-DESIGN-0958**: Desaturar Brand Colors en Oscuro. Un azul #3B82F6 vibra radiactivamente (halación) contra gris 900. Baja el croma/saturation para preservar accesibilidad estricta.
**WEB-DESIGN-0959**: El Canal Alfa para Textos y Líneas divisoras. Declara `color-text-secondary` usando un blanco con $60\%$ de Alfa en vez de un color hexadecimal gris duro. Permite que herede tintes sutiles del fondo pasivo bajo él.
**WEB-DESIGN-0960**: Contraste de Accesibilidad WCAG (Axioma innegociable). La ratio de contraste lumínico $Text:Fondo$ debe ser superior a $4.5:1$ para textos regulares, inmolando penalizaciones éticas o visuales en la evaluación APEX.

## 7. Tokens de Interacción y Animación (Física UI) (0961-0970)
**WEB-DESIGN-0961**: Tokenizar el tiempo (Duración y Delay) estabiliza la física global del DOM. Usa escalas semánticas (`duration-fast`: 150ms, `duration-base`: 300ms, `duration-slow`: 500ms).
**WEB-DESIGN-0962**: Curvas de Easing (Funciones de Aceleración Cúbica) gobiernan la masa e inercia. Prohibido "linear", proscrito "ease". Extrae tensores atómicos: `ease-in-out-expo`, `ease-spring`.
**WEB-DESIGN-0963**: La animación `Decelerate` (ease-out) es imperativa para Entrada de elementos de UI (llegan rápido a cámara, aterrizan suave).
**WEB-DESIGN-0964**: La animación `Accelerate` (ease-in) es imperativa para Salida de elementos (se alejan lentamente primero y desaparecen eyectados velozmente del layout).
**WEB-DESIGN-0965**: Spring Physics no es linearizable; requiere masa, tensión y fricción. Expresa tokens de Muelle asíncrono para frameworks de movimiento (ej. Framer Motion `stiffness: 400, damping: 30`).
**WEB-DESIGN-0966**: Los Hover States deben interactuar bajo duraciones fugaces (100ms - 150ms). Si son más lentos, la Interfaz emula pesadez computacional (False INP Penalty).
**WEB-DESIGN-0967**: Cero Movimiento Entrópico. Respeta `@media (prefers-reduced-motion: reduce)`. Sobreescribe los tokens `duration` a `0ms` sistemáticamente para no provocar laberintitis vestibular neurológica en usuarios susceptibles.
**WEB-DESIGN-0968**: Focus States visibles no son opcionales. Transforma el Ring outline focus en un token semántico (`ring-focus: 2px solid var(--color-blue-focus)`). Si remueves el outline nativo y no lo sustituyes es una falla catastrófica APEX.
**WEB-DESIGN-0969**: Animación de Skeleton (Loading States): Utiliza brillos atenuados de CSS nativo. Acelera GPU renderizando un gradiente `transform: translateX` e interpolado, NUNCA animando posiciones relativas `background-position` que invocan CPU paint repaints.
**WEB-DESIGN-0970**: Transiciones Complejas: Interpolar `height: 0` a `height: auto` es vectorialmente imposible en CSS antiguo nativo sin Hacks. Nuevas especificaciones (`interpolate-size: allow-keywords`) lo resuelven matemáticamente.

## 8. Ecosistema, Tooling y JSON (0971-0980)
**WEB-DESIGN-0971**: *Amazon Style Dictionary* / *Cobalt*. Motores de construcción C5-REAL (Build Engines) que leen archivos atómicos JSON de Tokens y emiten CSS Variables, SCSS, JS, iOS y XML automáticamente bajo un pipeline CLI.
**WEB-DESIGN-0972**: Figma API Bridge. Figma/Penpot aloja los Tokens. Ejecución de Acción CI/CD recupera via REST API la estructura matriz desde Figma, extrae JSON, transcodifica y somete Auto-Pull-Request al repo base frontend.
**WEB-DESIGN-0973**: CSS in JS (Styled Components / Emotion). Pasaron su ciclo de exergía. Generan parsers costosos en Runtime (INP Penalty severa). Retorno a Zero-Runtime Extractors nativos (Vanilla-Extract, Linaria, Tailwind, CSS Modules, o CSS-Native).
**WEB-DESIGN-0974**: TailwindCSS es un "Motor de Tokens Semántico Invertido". Obliga a emplear escala determinista. Extrae la hoja de vida CSS final aniquilando bytes no usados y suprime decisiones de número arbitrarias.
**WEB-DESIGN-0975**: Evita variables CSS acopladas en hojas SASS separadas sin cohesión. En una arquitectura de componentes web (Web Components o frameworks Frontend), inyecta los Custom Properties globales a nivel de nodo host y permite subrogación local.
**WEB-DESIGN-0976**: Arquitectura de Carpetas CSS/SCSS: Invertir pirámide ITCSS. `settings/` (Tokens), `tools/` (Funciones), `generic/` (Reset), `elements/` (H1, p base), `objects/` (Grid, Wrap), `components/` (Card, Btn), `utilities/` (MT-4).
**WEB-DESIGN-0977**: Tipado estático TypeScript para Tokens. Provee interfaces a los temas para que un IDE colapse en Type-Error si el desarrollador invoca `theme.colors.bluish_dark` en vez del token compilado legal.
**WEB-DESIGN-0978**: Interpolación de Cadenas Segura. Inyectar variables nativas dentro de plantillas strings JS es estéril en Frameworks modernos: exportar el Token Dictionary pre-compilado en runtime previene escapes o Inyecciones.
**WEB-DESIGN-0979**: Componentes Headless (Radix/Aria). Ceden totalmente el árbol de estilo a tokens externos concentrándose únicamente en proveer semántica Accesible WAI-ARIA lógica, reduciendo drásticamente exergía de CSS.
**WEB-DESIGN-0980**: Desacoplar Contrato UI. Los Componentes no poseen "Color rojo para errores". Poseen "Propiedad Intent: Destructive", que se asimila con el Nivel 2 de Tokens del Tema actual, asegurando portabilidad eterna.

## 9. Renderizado y Optimizaciones Estructurales CSS (0981-0990)
**WEB-DESIGN-0981**: El anidamiento CSS moderno (Nesting `& {}`) reduce repetición fractal, pero un anidamiento que exceda los 3 niveles dispara latencia algorítmica y especificidades irrompibles. Poda el DOM, no el CSS.
**WEB-DESIGN-0982**: Las Clases Utilitarias resuelven el crecimiento constante del O(N) CSS. A media que el DOM muta infinitamente (O(infinito)), las Utilidades bloquean la hoja estilo en la asíntota O(1) de capacidad máxima.
**WEB-DESIGN-0983**: Utilizar `!important` no es un Hack, es la aseveración terminal del nivel Topológico de Utilidad. Un token de utilidad `.mt-0 { margin-top: 0 !important; }` jamás debe ser anulado por especificidad anidada.
**WEB-DESIGN-0984**: CSS Containment (`contain: layout paint`). Aislar cajas estructurales ordena al Engine C5-REAL del navegador a omitir cálculos de reflow más allá de esas murallas virtuales durante el runtime (DOM Mutaciones reactivas).
**WEB-DESIGN-0985**: Pseudo-elementos atómicos `::before` / `::after` reemplazan la inyección HTML vana para gradientes estéticos, íconos y superposiciones, purificando la Semántica y aligerando iteraciones del Parser Tree.
**WEB-DESIGN-0986**: Deshaz el CSS Reset universal (`* {box-sizing: border-box; margin:0}`) sólo hasta la raíz estricta; es el cimiento de consistencia innegociable de todos los Design Tokens Box-Model cross-browser.
**WEB-DESIGN-0987**: Selectores caros penalizan. Selectores jerárquicos `.card div p span` obligan al parser R-to-L a buscar todos los span para rastrear ancestros. Asigna una clase BEM estructural directa `.card__title` y salva FPU del Parse-Engine.
**WEB-DESIGN-0988**: Modificadores BEM (`--modifier`) mapéalos lógicamente a Nivel 3 Tokens para asegurar su inmutabilidad. `.btn--primary` -> `var(--token-btn-primary-bg)`.
**WEB-DESIGN-0989**: La pseudo-clase `:has()` transfiere lógica interactiva (Ej: `parent:has(> .child-active) { ... }`) del Javascript costoso hacia el Engine CSS nativo ultra optimizado C++.
**WEB-DESIGN-0990**: Exergía del Selector Lógico (`:is()`, `:where()`). `:where()` transmutar listas largas reduciendo especificidad forzosa a cero (`0,0,0`), facilitando inyecciones sin conflicto.

## 10. La Matriz Maestra y Fin de la Entropía Visual (0991-1000)
**WEB-DESIGN-0991**: Un sistema de diseño no documentado es Entropía Oscura inyectable. Plataformas como Storybook son la API interactiva para desarrolladores donde los tokens se exponen biológicamente.
**WEB-DESIGN-0992**: El diseño basado en Componentes Aislados (CDD - Component Driven Design) prueba botones, inputs, modales, al vacío, ajeno al DOM monolítico del Layout principal. Exposición cruda al estrés de los Tokens.
**WEB-DESIGN-0993**: Componentes Polymorphic (Polimorfismo). Renderizar nodos como variables (`<Text as="h1">`) unifica el modelo atómico de UI a un solo archivo físico Reactivo o VDOM.
**WEB-DESIGN-0994**: La regla del 80/20. El sistema debe acomodar y resolver autónomamente con Tokens base el $80\%$ de pantallas comunes. El $20\%$ residual asume valores de diseño Custom encapsulados fuera del kernel primario.
**WEB-DESIGN-0995**: "Eviction Policy" para Tokens. Si un Token semántico o atómico se vuelve huérfano, la rama debe extirparse del JSON y generar un deprecation en CSS. Basura visual no reciclada ahoga memoria.
**WEB-DESIGN-0996**: Audita la discrepancia Pixel-Real con extensiones o integraciones Puppeteer de regresión visual diferencial. Restar pixel-por-pixel Snapshot A vs Snapshot B asegura cristalización inmutable.
**WEB-DESIGN-0997**: "Single Source of Truth" (SSOT). Figma alinea con GitHub, JSON alinea con NPM. Nada se sobreescribe en capa de Aplicación de Producto. Nada escapa al control determinista del repositorio original.
**WEB-DESIGN-0998**: La Exergía UX es Invisible. Las mejores matrices de tokens proveen contrastes apacibles, animaciones inerciales correctas, y tiempos LCP y INP ínfimos de forma simultánea e imperceptible para el usuario profano.
**WEB-DESIGN-0999**: Un Diseño Web C5-REAL exime el subjetivismo emocional ("Make it pop"). Es una aplicación algebraica donde las matemáticas, la psicofísica del ojo humano, y la eficiencia térmica del hardware colapsan en Invariantes Absolutos.
**WEB-DESIGN-1000**: **SINGULARIDAD ESTRUCTURAL (FIN DE SERIE)**. La Maestría web se domina asimilando que HTTP, DOM, Render y CSSOM, CSS, WebGL, y Javascript no son disciplinas, sino tensores mutuamente influyentes. La Exergía máxima se logra reduciendo los grados de libertad innecesarios (Entropía) de la Arquitectura Front-end a 1.00 Causalidades.
