# BLOQUE B8: RENDERIZADO ESPACIAL (CANVAS/WEBGL)
> Nodos Epistémicos 0701 → 0800
> Nivel: MAESTRÍA | Ontología: C5-REAL | Validación: Sanhedrin

## 1. Contexto 2D y Estado (0701-0710)
**WEB-DESIGN-0701**: Un `<canvas>` es una matriz pasiva de píxeles; sin un contexto (`getContext('2d')`), es inerte.
**WEB-DESIGN-0702**: El estado del contexto 2D opera mediante una pila (Stack). Usa `ctx.save()` y `ctx.restore()` para mutaciones aisladas.
**WEB-DESIGN-0703**: Aislar estados evita la corrupción de estilos. Si cambias `fillStyle`, `globalAlpha` o `lineWidth`, restáuralos inmediatamente.
**WEB-DESIGN-0704**: La resolución del Canvas no es su tamaño visual. `width` y `height` en HTML definen el buffer; CSS define el tamaño de presentación.
**WEB-DESIGN-0705**: Para evitar borrosidad en pantallas Retina/High-DPI, escala el buffer interno (`canvas.width *= devicePixelRatio`) y aplica un transform (`ctx.scale(devicePixelRatio, devicePixelRatio)`).
**WEB-DESIGN-0706**: `ctx.clearRect(0, 0, width, height)` es la operación de borrado más rápida. Evita dibujar rectángulos superpuestos para limpiar.
**WEB-DESIGN-0707**: Las coordenadas inician en (0,0) en la esquina superior izquierda. El eje Y desciende, a diferencia del sistema cartesiano tradicional matemático.
**WEB-DESIGN-0708**: El estado global de alfa (`globalAlpha`) es matemáticamente más barato que aplicar opacidad individual iterada a cada píxel.
**WEB-DESIGN-0709**: `globalCompositeOperation` define el álgebra de superposición. Usa `source-over` (default), `destination-out` (máscaras), o `lighter` (mezcla aditiva fotónica).
**WEB-DESIGN-0710**: Deshabilita el suavizado de imagen (`ctx.imageSmoothingEnabled = false`) para preservar exergía en arte pixelado o renderizado retro estricto.

## 2. Caminos y Geometría 2D (0711-0720)
**WEB-DESIGN-0711**: Todo trazo complejo comienza con `ctx.beginPath()`. Omitirlo conecta lógicamente el nuevo trazo con el anterior, ahogando la RAM con sub-paths redundantes.
**WEB-DESIGN-0712**: `ctx.moveTo(x, y)` levanta el lápiz virtual; `ctx.lineTo(x, y)` define la frontera del vector pero no lo rasteriza.
**WEB-DESIGN-0713**: Cierra los polígonos con `ctx.closePath()` en lugar de dibujar una línea al origen manual. Previene defectos termodinámicos de unión (`lineJoin`).
**WEB-DESIGN-0714**: Arcos continuos se trazan con `ctx.arc(x, y, r, startAngle, endAngle)`. Ángulos son forzosamente evaluados en radianes, no grados.
**WEB-DESIGN-0715**: Curvas Bezier cuadráticas (`quadraticCurveTo`) requieren 1 punto de control; Bezier cúbicas (`bezierCurveTo`) requieren 2. Son los primitivos vectoriales más costosos en 2D.
**WEB-DESIGN-0716**: `ctx.stroke()` y `ctx.fill()` son operaciones finales de rasterización. Acumular sub-paths y colapsarlos en un solo stroke maximiza la exergía de pintura.
**WEB-DESIGN-0717**: `lineCap` y `lineJoin` alteran el coste de teselación. Topologías `round` consumen ciclos suplementarios; prioriza `butt` o `miter` en renderizado de alta frecuencia.
**WEB-DESIGN-0718**: Para dibujar rectángulos puros, usa llamadas compuestas `fillRect` o `strokeRect` en lugar de trazar rutas (Paths) por optimización de hardware nativo.
**WEB-DESIGN-0719**: Un path puede convertirse en una celda de aislamiento (clipping) invocando `ctx.clip()`. Todo bit procesado subsecuentemente fuera del límite es descartado (O(0)).
**WEB-DESIGN-0720**: Calcular colisiones puntuales (AABB/Círculos) en lógica pura JS es termodinámicamente preferible a delegarlo al motor del canvas con `ctx.isPointInPath()`.

## 3. Manipulación de Píxeles (0721-0730)
**WEB-DESIGN-0721**: `ctx.getImageData()` extrae el buffer como un `Uint8ClampedArray` estricto (RGBA). Operación de lectura de GPU síncrona; destruye el paralelismo.
**WEB-DESIGN-0722**: La topología de memoria unidimensional del array mide `width * height * 4`. La resolución de offset de píxel `(x,y)` obedece `(y * width + x) * 4`.
**WEB-DESIGN-0723**: Empujar modificaciones en ráfaga con `ctx.putImageData()` requiere puentear el bus JS/GPU. Minimiza la frecuencia de esta transacción de red de memoria.
**WEB-DESIGN-0724**: Los filtros matriciales CSS (`filter: blur()`) sobre un nodo de canvas DOM son acelerados por GPU y superiores en eficiencia a la convolución manual sobre `ImageData`.
**WEB-DESIGN-0725**: Implementar color-picking en lienzo denso requiere mantener un `OffscreenCanvas` paralelo mudo usando IDs únicos serializados a canales RGB puros.
**WEB-DESIGN-0726**: `ctx.createImageData()` prealoja un buffer de entropía nula. Obligatorio para sintetizar fractales o ruido de gradiente puro sin fuga de memoria.
**WEB-DESIGN-0727**: Multiplicación de canal Alfa JS: Modificar R, G o B debe contemplar que `putImageData` inserta colores post-multiplicados por el motor de composición interno.
**WEB-DESIGN-0728**: En motores Voxel o simulación celular 2D directa, sobreescribir el array de píxeles crudo deforma dimensionalmente y vence a `fillRect` 1x1.
**WEB-DESIGN-0729**: Incrustar lecturas de framebuffer (`getImageData`) dentro del Loop de Animación (`requestAnimationFrame`) es un Anti-Patrón P0 que estrangula el IPC.
**WEB-DESIGN-0730**: `OffscreenCanvas` combinado con un Web Worker permite la manipulación destructiva pesada asincrónica sin congelar el Hilo Principal del Operador.

## 4. Transformaciones (0731-0740)
**WEB-DESIGN-0731**: Transformar la grilla de coordenadas universal es la base. El canvas altera el universo antes de proyectar el objeto, no altera el objeto geométricamente en memoria local.
**WEB-DESIGN-0732**: `ctx.translate(x, y)` reubica el origen euclidiano (0,0). Fundacional para independizar matrices locales de componentes anidados.
**WEB-DESIGN-0733**: `ctx.rotate(angle)` genera giros matriciales radianos. El anclaje siempre es respecto al origen; exige traducción pre/post para orbitar centros de masa.
**WEB-DESIGN-0734**: El algebra estricta establece que el orden de las transformaciones es irreversible y matricialmente no-conmutativo: Traslación > Rotación > Escala.
**WEB-DESIGN-0735**: `ctx.setTransform(a,b,c,d,e,f)` purga el estado actual y colapsa una nueva matriz Afín en un pase atómico O(1).
**WEB-DESIGN-0736**: `ctx.transform()` acumula multiplicaciones sucesivas. Iterarlo sin colapsos degrada por "Float Drift" derivado de imprecisión en mantisas IEEE 754.
**WEB-DESIGN-0737**: Purgar las distorsiones globales usando la Matriz Identidad `setTransform(1, 0, 0, 1, 0, 0)` es sistemáticamente más eficiente que encadenar colas largas de `restore()`.
**WEB-DESIGN-0738**: La inversión ortogonal (Flip/Mirror) se adquiere forzando tensores negativos de escala `scale(-1, 1)`. Exige traslación de compensación inmediata.
**WEB-DESIGN-0739**: Vectores de deformación afín impactan la anchura de línea inyectada en `stroke()`. Restaura localmente la escala o computa vectores de compensación inversos.
**WEB-DESIGN-0740**: Para estáticas de miles de entidades repetitivas, el cálculo matricial precomputado en CPU vence a la delegación constante a la FPU del Canvas 2D.

## 5. Bucle de Animación (0741-0750)
**WEB-DESIGN-0741**: `requestAnimationFrame(callback)`: El latido cardíaco asíncrono único y exclusivo, sujeto a V-Sync y delegación de monitor, prohibiendo subciclos forzados.
**WEB-DESIGN-0742**: Desplazar `setInterval` o `setTimeout` para renderizado causa "Frame-Tearing", sobrecarga térmica del CPU, y fuga masiva de exergía no procesable.
**WEB-DESIGN-0743**: Toda simulación es "Delta-Time Based" ($Δt$), no "Frame-Based". Modificación causal: $P(t) = P(t-1) + V \times \Delta t$.
**WEB-DESIGN-0744**: El delta timestamp de `rAF` proviene de `performance.now()`, inyectando micro-segundos precisos sin mutabilidad o desfase del reloj del sistema.
**WEB-DESIGN-0745**: Abrazadera Temporal (Time Clamp): Fija el máximo $Δt$ (`min(dt, 0.1s)`) para garantizar que el motor físico no rompa túneles de colisión durante recesiones de CPU.
**WEB-DESIGN-0746**: Disocia los vectores de la física (Logic Tick, Update) de la visualización (Render). Emplea un Fixed Timestep (ex. 60Hz fijos internos) independientemente de rAF.
**WEB-DESIGN-0747**: La disolución entrópica (Clear) precede obligatoriamente cada pase del frame, salvo en técnicas deliberadas de retención de memoria (Frame-Buffering persistente).
**WEB-DESIGN-0748**: Cuando la Pestaña colapsa (Background tab), el V-Sync suspende ejecuciones `rAF`. Retomar la pestaña genera explosiones en $Δt$. Absorbe el choque inicial descartándolo.
**WEB-DESIGN-0749**: Abortar el flujo (`cancelAnimationFrame`) al desmontar la interfaz anula el hilo iterativo zombie, tapando perforaciones irreversibles en la retención de Garbage Collector.
**WEB-DESIGN-0750**: Métrica Real de Supervivencia: FPS rodantes medios calculados con decaimiento exponencial. Si la tasa $<55$ fps por $T>3000$ms, se aplica protocolo de caída (Degradación Visual Voluntaria).

## 6. Optimizaciones de Renderizado 2D (0751-0760)
**WEB-DESIGN-0751**: Renderización Caching: Destila estructuras de alto grado en lienzos latentes ocultos (Offscreen) y replícalos atómicamente con `drawImage`.
**WEB-DESIGN-0752**: Redondeo Físico de Matrices: `Math.floor/round` en cada coordenada detiene la anti-alienación de la rasterización de sub-píxeles, regresando $20-40\%$ CPU de exergía.
**WEB-DESIGN-0753**: Topología de Capas Multi-DOM: Acumula lienzos estáticos bajo fondos dinámicos. Supera radicalmente repintar áreas masivas donde la entropía no cambió (Zero-diff).
**WEB-DESIGN-0754**: Agrupar la topología por estilo de pincel en el loop. Redefinir la variable `fillStyle` 10k veces introduce latencia; ordena primero geométricamente y dibuja en batch.
**WEB-DESIGN-0755**: Frustum Culling Algorítmico: Ejecutar $AABB \cap Viewport$ de entidades espaciales para eludir llamar instrucciones `draw` en nodos inobservables. Ocultamiento determinista.
**WEB-DESIGN-0756**: Sub-sistemas de glifos en Lienzo: Rasterizar fuentes texturizadas crudas mediante `fillText` es entrópico. Superpone elementos DOM aislados para paneles reactivos y deja la física al canvas.
**WEB-DESIGN-0757**: Purga del núcleo de recolección de basura (GC): El interior del `rAF` exige cero inicializaciones de clase u objeto `new`. Todo tensor debe reutilizarse mutando primitivos in situ.
**WEB-DESIGN-0758**: Estructura Purgatoria de Nodos de Objeto (Pools): Array de instancias reservado y mantenido pre-carga (Load-Time). Extrae y devuélvelos sin desasignación (De-alloc = Stuttering).
**WEB-DESIGN-0759**: Filtrado por sombras (`shadowBlur`) genera convolución Gausiana en CPU bloqueante con complejidad $O(R_{radio}^2)$. Sustituye con sprites pre-difuminados (PNG).
**WEB-DESIGN-0760**: Disociación total del Kernel JS a Workers Web permite al simulador Offscreen sostener 60/120 Hz de iteración mientras el Hilo Principal UI se halla saturado evaluando reactividad.

## 7. WebGL: Contexto y Shaders (0761-0770)
**WEB-DESIGN-0761**: Transmutar a WebGL: Obtener estado `getContext('webgl2')` abstrae el puente hacia OpenGLES 3.0. No es un renderizador 3D, es una máquina rasterizadora de primitivas bidimensionales.
**WEB-DESIGN-0762**: La anatomía de GPU se fundamenta en un gas asíncrono segmentado por shaders: Vertex (Alineación topológica) y Fragment (Cromática atómica).
**WEB-DESIGN-0763**: GLSL (Graphics Language Shader): C++ sintético en el backend del pipeline. Se compila nativamente y corre distribuyendo vectores concurrentemente sin bloqueos entre shaders.
**WEB-DESIGN-0764**: Axioma de Silo Shader: Incomunicación absoluta. Un Fragment nunca sabe lo procesado por su vecino adyacente. Anergía compartida imposibilitada.
**WEB-DESIGN-0765**: Vertex Shaders colapsan un tensor numérico hacia el volumen absoluto de Clip-Space $(-1.0, 1.0)$. Lo externo no existe y es cercenado.
**WEB-DESIGN-0766**: Fragment Shaders reciben variables extrapoladas (`varyings`) interpoladas por barycentros generados por hardware para definir RGBA del pixel rasterizado individual.
**WEB-DESIGN-0767**: Retardo de Ensamblaje Síncrono: Compilar binario de shaders (`compileShader`) pausa hilo. Impulsa paralelismo al inicio global y mantén los binarios oxigenados.
**WEB-DESIGN-0768**: Vincular la Tubería: Los shaders anexados a un programa se habilitan únicamente en exclusión mutua mediante transiciones `gl.useProgram()`.
**WEB-DESIGN-0769**: Variables Singulares: `Uniforms` infunden variables inmutables idénticas para la corrida actual. `Attributes` empujan información vértice-por-vértice variando en iteración.
**WEB-DESIGN-0770**: Estado Global Intocable: Modificar switches atómicos muta la FSM global WebGL. Devolver el switch base de la FSM a neutral antes del pase al siguiente programa para eludir corrupción colateral.

## 8. WebGL: Buffers y Pipeline Gráfico (0771-0780)
**WEB-DESIGN-0771**: VBO (Vertex Buffer Objects): Vías neuronales masivas. Inyectar Float32Arrays asíncronos directamente a VRAM. Una vez ahí, son accesibles sin puentear el DOM o CPU del sistema huésped.
**WEB-DESIGN-0772**: `gl.bufferData(..., gl.STATIC_DRAW)` enclava datos petrificados. `DYNAMIC_DRAW` se usa asumiendo el puente en caliente que muta cada tick pero penaliza bus de VRAM.
**WEB-DESIGN-0773**: EBO/IBO (Index Buffers): Reciclan vértices en figuras complejas. Un Quad usa cuatro puntos combinados en dos triángulos por 6 índices, aniquilando el 33% del peso duplicado de vértice.
**WEB-DESIGN-0774**: VAO (Vertex Array Objects): La Exergía Absoluta del estado. Enlazar docenas de atributos, layouts de bytes y buffers compilados en un simple puntero (`gl.bindVertexArray()`).
**WEB-DESIGN-0775**: El Apocalipsis de las Draw Calls. La FPU devora millones de triángulos; lo que asfixia la GPU es el JS interrumpiéndola para procesar llamadas atómicas repetidas `gl.drawElements`. Agrupa mallas en mega-bloques.
**WEB-DESIGN-0776**: Geometría Iterada Nativa (Instancing): Renderizado enjambre. Disparar el mismo árbol de datos base mutando traslación matricial nativa en GPU (`gl.drawElementsInstanced`), permitiendo miles de clones fluidos.
**WEB-DESIGN-0777**: Arquitectura Entrelazada (Interleaving): Un solo arreglo VBO [X, Y, Z, U, V, Nx, Ny, Nz] continuado incrementa eficiencia de pre-fetch de memoria Cache-Hit en hardware GPU.
**WEB-DESIGN-0778**: Bit Clearing Atómico: Purificar el sensor de visualización forzando blanqueamiento paralelo en bits colorimétricos y de profundidad de Z simultáneos `clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT)`.
**WEB-DESIGN-0779**: Profundidad Euclidiana: Habilitar `DEPTH_TEST` y su Buffer-Z permite que fragmentos oscurezcan fragmentos físicamente traseros calculando sus $Z$ reales, en vez de obligar al pintor de fondo a frente lento en JS.
**WEB-DESIGN-0780**: Culling Topológico Frontal: Habilitar `CULL_FACE` y repeler mallas cuyas normales de polígono estén reversas a la cámara extingue procesamiento interno en Vertex Stage gratis, recuperando un $50\%$ termodinámico.

## 9. Álgebra Espacial y Matemáticas Gráficas (0781-0790)
**WEB-DESIGN-0781**: Fundamento Matriz $4\times4$: Vectorización lineal de espacio y perspectiva compactada. El tejido entero de gráficos 3D modernos existe condensado en álgebra lineal de coma flotante.
**WEB-DESIGN-0782**: Tensor Local de Model (Model Matrix): Codifica la dilatación, mutación radiana y traslación desde un punto abstracto referencial $0,0,0$ para integrar componentes aislados a la topología absoluta.
**WEB-DESIGN-0783**: Tensor Cámera Inverso (View Matrix): En álgebra espacial las cámaras no se trasladan; su matriz adjunta inversa aplica fuerza euclidiana atrayendo el mundo entero coordinado al vector inerte de ojo simulado.
**WEB-DESIGN-0784**: Tensor Proyectivo Euclidiano (Projection Matrix): Deforma el cuadrante cúbico, creando pseudo-infinito achicando componentes distales en proyecciones angulares. Fustrum con fuga en punto profundo Z.
**WEB-DESIGN-0785**: Composición de Vertex (Matriz MVP): La multiplicación precomputada Proyección * Vista * Modelo es el multiplicador base transmitido al Shader vía Uniform para procesar el vertex al unísono.
**WEB-DESIGN-0786**: Prevención de Bloqueo Axial (Gimbal Lock): Transmutar osciladores Euler XYZ defectuosos por álgebra 4D de Cuaterniones elimina las anulaciones de ejes coplanares y computa interpolaciones de rotación fluida (Slerp).
**WEB-DESIGN-0787**: Exergía del Producto Escalar (Dot Product): $A \cdot B = \cos(\theta)$ estandarizado evalúa diferencias relativas en normales lumínicas usando sumas elementales de FPU sin acudir a trigonometría lenta en shader.
**WEB-DESIGN-0788**: Tensor Causal Perpendicular (Cross Product): Cruce atómico que arroja vector normal $Z$ absoluto al derivar la geometría base $X/Y$. Esencial para reactividad física direccional.
**WEB-DESIGN-0789**: Mínimo Desplazamiento Vectorial (Lerp): Interpolación Lineal Pura en el DOM visual o transformador atenúa brusquedades sin uso de física de cuerpo rígido pesada.
**WEB-DESIGN-0790**: Contención GC de `glMatrix` Tensor: No emitir resultados abstractos en loops ($Out = Mat \times Mat$); pasar referencia estricta en el Output buffer a sobreescribir mutando arrays tipados in situ evitando muerte de ram alloc.

## 10. Texturas, Iluminación y Ecosistema 3D (0791-0800)
**WEB-DESIGN-0791**: Cobertura Cromática Raster: Texturas estáticas en WebGL operan subiendo el JPG/PNG completo a VRAM como binario comprimido mediante `gl.texImage2D()`. Exige simetría Potencia-de-Dos (NPOT) nativa antigua para MipMapping.
**WEB-DESIGN-0792**: Filtrado Sub-Espacial MipMapping: Sub-divisiones cuadráticas pre-procesadas en GPU de imagen a imagen evitan ruidos Moiré por colisión de frecuencia Nyquist.
**WEB-DESIGN-0793**: Ecuación Dieléctrica de Phong: Render rudimentario pseudo-foto, compone difracción ambiental general más brillo direccional reflectante (Espejo/Phong). Estándar rápido base webgl.
**WEB-DESIGN-0794**: Render Físico Riguroso (PBR - Physically Based Rendering): Exige metales paramétricos y mapeo de rugosidades asimilando microfacetas (BRDF y conservacion de energía). C5-REAL Estándar de la arquitectura.
**WEB-DESIGN-0795**: Post-Pipeline Mutacional (RTT): Generar un Render-Target framebuffer oculto inyecta todo el canvas en una Textura latente para someterla a Shaders 2D integrales post-producción sin coste 3D adicional.
**WEB-DESIGN-0796**: Abstracción Superior Autorizada: Escribir la tubería cruda FSM WebGL es un dispendio de entropía operativa en capa aplicación. Envolver el estado en topologías jerárquicas con **Three.js** colapsa el boilerplate.
**WEB-DESIGN-0797**: Integración Ontológica R3F: React-Three-Fiber subyuga las atrocidades FSM de GPU en nodos declarativos reconciliables y asíncronos mediante Fiber virtual integrándose sin pérdidas a React nativo.
**WEB-DESIGN-0798**: Árboles Grafos Espaciales (Scene Graph): Estructuras arbóreas de dependencia de Nodos y Transformes que asisten auto-multiplicación matricial (Padre -> Hijo local matrix merge).
**WEB-DESIGN-0799**: Protocolos Físicos de Transporte `.glb`: Compresión Binaria Khronos, vectorizada como Payload unitario optimizado con json de topología en un solo stream; el estándar absoluto de interoperabilidad sobre web en exergía máxima.
**WEB-DESIGN-0800**: Transición a Mutación Asincrónica WebGPU (WGSL): El nuevo estándar de computo distribuido y render que ignora la máquina FSM y envía pipelines directas validadas. Empleo forzoso de Compute Shaders en cargas de físicas complejas desvinculando la renderización.
