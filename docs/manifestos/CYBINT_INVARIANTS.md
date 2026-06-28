<!-- [C5-REAL] Exergy-Maximized -->
# 🕸️ CYBINT: 100 Primitivas, 100 Invariantes & Casos de Uso

> **STATUS:** C5-REAL  
> **DOMAIN:** Cyber Intelligence (CYBINT) / Threat Intelligence  
> **OPERATOR:** borjamoskv

Este documento establece la ontología absoluta de operaciones CYBINT. Cero ruido narrativo. 100 funciones atómicas (Primitivas), 100 leyes inmutables (Invariantes) y 3 topologías de despliegue (Casos de Uso).

---

## 🏗️ PARTE I: 100 PRIMITIVAS CYBINT (Causal Nodes)
*Las Primitivas son verbos. Acciones atómicas y deterministas que mutan el estado de la inteligencia.*

### Dominio 1: Telemetría & Colección (001-010)
`CYB-P001` Extraer ASN (Autonomous System Number) de IP.
`CYB-P002` Resolver DNS Pasivo (pDNS) histórico.
`CYB-P003` Capturar hash JARM de handshake TLS.
`CYB-P004` Archivar banner de respuesta HTTP crudo.
`CYB-P005` Registrar WHOIS histórico (Registrant/Email).
`CYB-P006` Extraer metadatos EXIF de payloads droppeados.
`CYB-P007` Interceptar y parsear User-Agent de request.
`CYB-P008` Mapear topología de red BGP.
`CYB-P009` Extraer llaves públicas SSH (HostKeys).
`CYB-P010` Resolver registros MX/TXT/SPF/DMARC.

### Dominio 2: Análisis de Artefactos / Malware (011-020)
`CYB-P011` Calcular hashes SHA-256 / SHA-3.
`CYB-P012` Generar hash SSDeep (Fuzzy Hashing).
`CYB-P013` Extraer strings ASCII/Unicode de binario.
`CYB-P014` Desempaquetar ejecutables (UPX, custom packers).
`CYB-P015` Hookear llamadas a la API de Windows (Syscalls).
`CYB-P016` Extraer Mutex (Mutual Exclusions) en memoria.
`CYB-P017` Parsear tabla IAT (Import Address Table).
`CYB-P018` Identificar compilador/linker via Rich Header.
`CYB-P019` Extraer llaves XOR embebidas.
`CYB-P020` Mapear entropy ratio de secciones PE.

### Dominio 3: Caza de Amenazas en Red (021-030)
`CYB-P021` Ejecutar regla YARA sobre PCAP.
`CYB-P022` Aislar beaconing periodicity (Jitter analysis).
`CYB-P023` Detectar Domain Generation Algorithms (DGA).
`CYB-P024` Extraer SNI (Server Name Indication) de TLS.
`CYB-P025` Analizar túneles DNS/ICMP (Payload size/entropy).
`CYB-P026` Decodificar tráfico base64/hex en HTTP GET/POST.
`CYB-P027` Identificar Fast-Flux DNS routing.
`CYB-P028` Parsear logs Zeek/Bro (conn.log, http.log).
`CYB-P029` Mapear flujos NetFlow/IPFIX.
`CYB-P030` Detectar suplantación de MAC (ARP Spoofing).

### Dominio 4: OSINT / Dark Web (031-040)
`CYB-P031` Raspar foros .onion via proxies Tor.
`CYB-P032` Extraer PGP keys de actores de amenazas.
`CYB-P033` Monitorear repositorios de GitHub por leaks de API.
`CYB-P034` Buscar bins en Pastebin via expresiones regulares.
`CYB-P035` Correlacionar aliases en foros underground.
`CYB-P036` Monitorear canales de Telegram de Ransomware (RaaS).
`CYB-P037` Analizar volcados de datos (Data Leaks).
`CYB-P038` Buscar metadatos de documentos públicos (FOCA).
`CYB-P039` Extraer relaciones de LinkedIn/Empresariales.
`CYB-P040` Consultar APIs de Shodan/Censys por vulnerabilidades.

### Dominio 5: Modelado de Adversarios (041-050)
`CYB-P041` Mapear táctica a MITRE ATT&CK.
`CYB-P042` Mapear técnica a MITRE ATT&CK.
`CYB-P043` Instanciar nodo en el Modelo Diamante (Adversary).
`CYB-P044` Instanciar nodo en el Modelo Diamante (Infrastructure).
`CYB-P045` Instanciar nodo en el Modelo Diamante (Capability).
`CYB-P046` Instanciar nodo en el Modelo Diamante (Victim).
`CYB-P047` Asignar nivel de sofisticación (Tier 1-6).
`CYB-P048` Identificar motivaciones (Financiero, Espionaje, Hacktivismo).
`CYB-P049` Generar grafo de dependencias de la campaña.
`CYB-P050` Documentar TTPs (Tactics, Techniques, Procedures).

### Dominio 6: Enriquecimiento y Correlación (051-060)
`CYB-P051` Consultar VirusTotal API (Relaciones).
`CYB-P052` Inyectar IoC en MISP (Malware Information Sharing Platform).
`CYB-P053` Normalizar datos al formato STIX/TAXII.
`CYB-P054` Pivotar de IP a Dominio asociado.
`CYB-P055` Pivotar de Dominio a Registrante.
`CYB-P056` Pivotar de Hash a Familia de Malware.
`CYB-P057` Correlacionar logs de EDR con logs de Firewall.
`CYB-P058` Asignar score de confianza a una fuente (PPI).
`CYB-P059` Generar grafo visual de relaciones (Maltego).
`CYB-P060` Deduplicar IoCs en memoria.

### Dominio 7: Inteligencia Táctica (061-070)
`CYB-P061` Crear regla Snort/Suricata.
`CYB-P062` Crear regla Sigma para SIEM.
`CYB-P063` Generar lista de bloqueo (Blocklist).
`CYB-P064` Emitir alerta de Flash intelligence.
`CYB-P065` Escribir reporte de inteligencia táctica.
`CYB-P066` Traducir inteligencia a queries de Splunk.
`CYB-P067` Definir umbrales de alerta (Thresholds).
`CYB-P068` Desarrollar playbook de respuesta a incidentes.
`CYB-P069` Implementar sinkhole para un dominio C2.
`CYB-P070` Aislar endpoint comprometido.

### Dominio 8: Identidad y Atribución (071-080)
`CYB-P071` Analizar husos horarios en commits o timestamps.
`CYB-P072` Identificar modismos lingüísticos en foros.
`CYB-P073` Correlacionar horas de actividad (Patter of Life).
`CYB-P074` Identificar reutilización de contraseñas.
`CYB-P075` Rastrear billeteras de criptomonedas (Blockchain analysis).
`CYB-P076` Mapear infraestructura de proxys compartida.
`CYB-P077` Analizar metadata de certificados SSL let's encrypt.
`CYB-P078` Identificar patrones de registro de dominios (Naming conventions).
`CYB-P079` Correlacionar perfiles sociales con handles de foros.
`CYB-P080` Identificar huellas del sistema operativo anfitrión.

### Dominio 9: Operaciones Adversariales (081-090)
`CYB-P081` Desplegar honeypot de alta interacción.
`CYB-P082` Inyectar canarios digitales (Tokens).
`CYB-P083` Simular tráfico de adversarios (Adversary Emulation).
`CYB-P084` Realizar ingeniería inversa de algoritmos DGA.
`CYB-P085` Desofuscar scripts maliciosos (PowerShell/VBS).
`CYB-P086` Interceptar y manipular tráfico C2.
`CYB-P087` Explotar vulnerabilidades en infraestructura del atacante.
`CYB-P088` Recopilar inteligencia desde dentro de una botnet.
`CYB-P089` Engañar al adversario mediante desinformación activa.
`CYB-P090` Mapear el kill chain de un ataque en curso.

### Dominio 10: Gobernanza de Inteligencia (091-100)
`CYB-P091` Auditar el ciclo de vida de la inteligencia.
`CYB-P092` Definir Requerimientos Prioritarios de Inteligencia (PIR).
`CYB-P093` Evaluar la madurez del programa de inteligencia.
`CYB-P094` Establecer métricas de rendimiento (KPIs).
`CYB-P095` Gestionar el acceso a inteligencia sensible (TLP).
`CYB-P096` Integrar inteligencia en procesos de gestión de riesgos.
`CYB-P097` Desarrollar planes de recolección de inteligencia.
`CYB-P098` Validar la integridad de los datos de inteligencia.
`CYB-P099` Formar a analistas en técnicas CYBINT.
`CYB-P100` Automatizar la ingesta y procesamiento de inteligencia.

---

## ⚖️ PARTE II: 100 INVARIANTES CYBINT (Leyes Termodinámicas)
*Los Invariantes son verdades inmutables. No cambian con la tecnología; son axiomas del conflicto.*

### Infraestructura y C2 (001-010)
`CYB-I001` La infraestructura es costosa; los atacantes siempre la reutilizan.
`CYB-I002` El pDNS no miente; el historial de resolución sobrevive a la eliminación del registro.
`CYB-I003` Los certificados SSL compartimentan el ruido; firmas únicas (JARM) delatan el backend.
`CYB-I004` Los dominios generados por algoritmos (DGA) tienen alta entropía pero patrones matemáticos predecibles.
`CYB-I005` Los atacantes cometen errores de configuración (OPSEC fails) al desplegar servidores C2.
`CYB-I006` Fast-Flux oculta la IP, pero revela la red de bots subyacente.
`CYB-I007` El uso de proxies comerciales (VPNs/VPS) anonimiza, pero agrupa a los atacantes en ASNs específicos.
`CYB-I008` Los puertos inusuales (ej. 4444) son firmas de herramientas por defecto.
`CYB-I009` La vida útil de un dominio C2 es inversamente proporcional a su exposición.
`CYB-I010` El beaconing tiene jitter; la ausencia total de jitter delata a un novato o un script básico.

### Artefactos y Malware (011-020)
`CYB-I011` Los hashes (MD5/SHA256) son la métrica más frágil de la inteligencia (Pirámide del Dolor).
`CYB-I012` El fuzzy hashing (SSDeep) expone la evolución del código, no solo la identidad del archivo.
`CYB-I013` Las cadenas de texto (strings) en binarios a menudo revelan rutas de compilación y nombres de usuario.
`CYB-I014` Los packers ocultan el código, pero el packer mismo es una firma identificable.
`CYB-I015` Las marcas de tiempo de compilación (Timestamps) pueden ser falsificadas, pero a menudo se olvidan.
`CYB-I016` Los Mutex previenen la doble infección, pero sirven como un IoC de alta fidelidad.
`CYB-I017` Las importaciones de API (IAT) revelan las intenciones del malware antes de la ejecución.
`CYB-I018` El Rich Header en binarios PE identifica de forma única el entorno de compilación de Windows.
`CYB-I019` La entropía alta en una sección de datos sugiere cifrado o compresión (cargas útiles ocultas).
`CYB-I020` El malware sin archivos (Fileless) reside en la memoria, dejando rastros en los procesos de volcado.

### Comportamiento del Adversario (021-030)
`CYB-I021` Los TTPs (Tácticas, Técnicas y Procedimientos) son el indicador más difícil de cambiar para un atacante.
`CYB-I022` Los atacantes siguen la ley del menor esfuerzo; usan herramientas integradas (Living off the Land) cuando es posible.
`CYB-I023` El espionaje busca persistencia; el cibercrimen busca monetización rápida.
`CYB-I024` Los grupos APT tienen horarios de trabajo; sus commits y ataques siguen husos horarios y días festivos.
`CYB-I025` La atribución definitiva es un mito; la atribución basada en la confianza (Confidence Level) es la realidad.
`CYB-I026` Las falsas banderas (False Flags) son comunes para desviar la atribución a naciones rivales.
`CYB-I027` El Modelo Diamante requiere al menos dos vértices para proporcionar inteligencia procesable.
`CYB-I028` Los actores de amenazas evolucionan sus TTPs en respuesta a la publicación de reportes de inteligencia.
`CYB-I029` El Ransomware as a Service (RaaS) separa al desarrollador (capability) del afiliado (adversary).
`CYB-I030` El acceso inicial se mercantiliza (Initial Access Brokers), creando cadenas de suministro criminales.

### Inteligencia y Datos (031-040)
`CYB-I031` Un IoC sin contexto no es inteligencia, es un bloqueador de firewall.
`CYB-I032` La inteligencia perece; un IoC de hace un año probablemente es un falso positivo hoy.
`CYB-I033` El enriquecimiento de datos reduce la entropía analítica.
`CYB-I034` La correlación de eventos dispares revela la campaña subyacente.
`CYB-I035` Los foros de la Dark Web son ecosistemas de confianza; la reputación es la moneda de cambio.
`CYB-I036` Las filtraciones de datos (Data Leaks) son retrospectivas; el acceso inicial ocurrió meses antes.
`CYB-I037` Las bases de datos de Whois históricas son fundamentales para rastrear la evolución de la infraestructura.
`CYB-I038` El Traffic Light Protocol (TLP) es un pacto de confianza humano, no una medida de seguridad técnica.
`CYB-I039` STIX/TAXII son estándares sintácticos, pero la semántica requiere intervención analítica.
`CYB-I040` Más datos no significa más inteligencia; el ruido oscurece la señal.

### Detección y Respuesta (041-050)
`CYB-I041` La detección perfecta no existe; la resiliencia asume el compromiso.
`CYB-I042` Las reglas YARA buscan cadenas; las reglas Sigma buscan comportamientos.
`CYB-I043` El Threat Hunting asume que los controles preventivos ya han fallado.
`CYB-I044` Los falsos positivos fatigan a los analistas; la alta fidelidad es prioritaria.
`CYB-I045` El tiempo medio de detección (MTTD) mide la eficacia de la inteligencia, no de los firewalls.
`CYB-I046` Las alertas deben tener contexto accionable o ser suprimidas.
`CYB-I047` La caza de amenazas basada en hipótesis es más efectiva que la búsqueda a ciegas de IoCs.
`CYB-I048` Los honeypots generan inteligencia de alta fidelidad con cero falsos positivos (todo tráfico es anómalo).
`CYB-I049` El aislamiento de red es una medida de contención, no de remediación.
`CYB-I050` Los playbooks de incidentes deben ser actualizados con la inteligencia táctica más reciente.

### OSINT y Reconocimiento (051-060)
`CYB-I051` Lo que se publica en internet no se puede borrar de forma fiable (Wayback Machine).
`CYB-I052` Los metadatos de los documentos (EXIF) a menudo comprometen el OPSEC físico del atacante.
`CYB-I053` Las redes sociales son vectores de ingeniería social de alta efectividad.
`CYB-I054` Shodan no ataca; Shodan revela la negligencia de la configuración.
`CYB-I055` La resolución pasiva de DNS permite reconstruir grafos de infraestructura sin tocar el objetivo.
`CYB-I056` Las filtraciones de repositorios de código exponen secretos, no solo propiedad intelectual.
`CYB-I057` Los foros de hackers revelan la demanda del mercado de vulnerabilidades (0-days).
`CYB-I058` Las relaciones en LinkedIn mapean la jerarquía objetivo para campañas de Spear Phishing.
`CYB-I059` El rastreo de billeteras cripto sigue el flujo del dinero (Ransomware), a menudo rompiendo el OPSEC.
`CYB-I060` La inteligencia de fuentes abiertas es el 80% del perfilado inicial de un adversario.

### Vulnerabilidades y Exploits (061-070)
`CYB-I061` Un CVE sin un exploit público (PoC) es un riesgo teórico; con PoC, es una crisis inminente.
`CYB-I062` Los atacantes priorizan la explotación de VPNs y firewalls (borde de la red).
`CYB-I063` Las vulnerabilidades de Día Cero (0-day) son caras; los atacantes prefieren Días N (N-days) no parchados.
`CYB-I064` La gestión de parches siempre va rezagada respecto al desarrollo de exploits.
`CYB-I065` Las vulnerabilidades en la cadena de suministro (Supply Chain) amplifican exponencialmente el radio de explosión.
`CYB-I066` El análisis de parches (Patch Diffing) revela la vulnerabilidad subyacente que fue corregida.
`CYB-I067` La explotación requiere precisión de memoria (ASLR/DEP dificultan, pero no imposibilitan).
`CYB-I068` Los exploits se mercantilizan rápidamente y se integran en frameworks automatizados (Metasploit, Cobalt Strike).
`CYB-I069` La configuración predeterminada insegura es más explotada que los fallos de código complejos.
`CYB-I070` El escaneo masivo de vulnerabilidades comienza minutos después de la divulgación pública de un PoC.

### Gobernanza y Estrategia (071-080)
`CYB-I071` La inteligencia debe responder a un Requisito Prioritario de Inteligencia (PIR) o es un desperdicio de exergía.
`CYB-I072` La inteligencia no procesable (Actionable Intel) es simplemente noticias cibernéticas.
`CYB-I073` La retroalimentación (Feedback) del SOC a los analistas de inteligencia cierra el ciclo y refina las alertas.
`CYB-I074` El intercambio de inteligencia (Sharing) fortalece la defensa colectiva, pero requiere confianza.
`CYB-I075` La automatización es obligatoria para el procesamiento de datos; el análisis requiere cognición humana (o IA avanzada).
`CYB-I076` La inteligencia táctica previene incidentes; la inteligencia estratégica guía la inversión en seguridad.
`CYB-I077` El sesgo de confirmación es el mayor enemigo del analista de inteligencia.
`CYB-I078` La confianza en la fuente (Reliability) y en la información (Credibility) deben evaluarse por separado.
`CYB-I079` La diseminación oportuna de inteligencia imperfecta es mejor que la inteligencia perfecta entregada tarde.
`CYB-I080` El programa de inteligencia madura cuando pasa de consumir feeds a producir inteligencia original.

### Criptografía y OPSEC (081-090)
`CYB-I081` La criptografía mal implementada es peor que la falta de criptografía (falsa sensación de seguridad).
`CYB-I082` Los atacantes usan cifrado simétrico para los datos y asimétrico para proteger las claves (Ransomware).
`CYB-I083` El análisis de tráfico cifrado infiere intenciones mediante el tamaño, la frecuencia y el tiempo de los paquetes.
`CYB-I084` La reutilización de código (Code Reuse) a través de campañas de malware es inevitable debido a la economía del desarrollo.
`CYB-I085` El OPSEC perfecto es imposible a largo plazo; la fatiga del atacante genera errores.
`CYB-I086` Los atacantes a menudo prueban su propio malware contra VirusTotal, revelando sus campañas antes de lanzarlas.
`CYB-I087` Las cuentas de correo de recuperación y la infraestructura compartida exponen redes enteras de actores.
`CYB-I088` El uso de idiomas y teclados específicos en el código fuente o metadatos acota la geolocalización.
`CYB-I089` Los atacantes registran dominios parecidos (Typosquatting) con meses de antelación a una campaña.
`CYB-I090` La desofuscación automatizada es una carrera armamentística continua contra nuevos empacadores.

### Singularidad CYBINT-Física (091-100)
`CYB-I091` El daño cibernético tiene consecuencias cinéticas (ICS/SCADA).
`CYB-I092` Las redes OT (Tecnología Operativa) priorizan la disponibilidad sobre la confidencialidad, haciéndolas frágiles.
`CYB-I093` El espionaje cibernético precede inevitablemente al conflicto geopolítico físico.
`CYB-I094` Los dispositivos IoT son la cabeza de playa preferida para la formación masiva de botnets (Mirai).
`CYB-I095` La seguridad física y la ciberseguridad son el mismo dominio; un USB en el estacionamiento elude los firewalls.
`CYB-I096` La intercepción de RF (SIGINT) alimenta directamente los grafos de amenazas cibernéticas (CYBINT).
`CYB-I097` Los drones y vehículos autónomos amplían la superficie de ataque cibernético al espacio aéreo y terrestre.
`CYB-I098` La inteligencia artificial acelera la velocidad de adaptación de los TTPs, colapsando el tiempo de respuesta.
`CYB-I099` Las campañas de desinformación cibernética alteran la percepción de la realidad física de la sociedad.
`CYB-I100` **La asimetría es absoluta:** El defensor debe proteger todo el perímetro; el atacante solo necesita una vulnerabilidad (Cero Anergía).

---

## 🚀 PARTE III: 3 HIGH-EXERGY USE CASES

### Caso 1: Desmantelamiento de Infraestructura RaaS (Ransomware as a Service)
**Vector:** Pivotaje de Dominio y Análisis de Certificados (El adversario es perezoso).
1. **Ingesta:** El SOC detecta un beaconing hacia `update-telemetry[.]com`.
2. **CYB-P002 (pDNS):** Se identifica que la IP del dominio alojaba previamente `secure-login-portal[.]net`.
3. **CYB-P003 (JARM):** Se escanea la IP. El hash JARM coincide con la firma criptográfica del servidor C2 "Cobalt Strike" por defecto.
4. **CYB-I003 (Invariante):** Usando Shodan/Censys, se buscan todas las IPs globales con ese hash JARM y el mismo certificado autofirmado, identificando 45 servidores inactivos del mismo grupo APT antes de que se usen.

### Caso 2: Caza de Amenazas (Threat Hunting) por Comportamiento (Living off the Land)
**Vector:** Análisis de TTPs vs Hashes (Ignorando la Pirámide del Dolor baja).
1. **Hipótesis (CYB-I022):** El atacante usará herramientas nativas de Windows para evadir EDR.
2. **CYB-P066 (Query):** Se programa el SIEM para buscar ejecuciones de `certutil.exe` o `bitsadmin.exe` con argumentos de descarga HTTP (e.g., `-urlcache -split -f`).
3. **Correlación (CYB-P057):** Se cruza la ejecución del proceso con conexiones salientes en el firewall hacia ASNs conocidos por alojar bulletproof hosting.
4. **Resultado:** Detección de una intrusión Fileless en Etapa 2, saltándose las firmas de antivirus que nunca detectaron un binario malicioso.

### Caso 3: Atribución Temprana mediante Análisis OPSEC Fail
**Vector:** OSINT y Metadatos cruzando la barrera física.
1. **Colección:** Un analista extrae un documento de phishing droppeado en la red.
2. **CYB-P006 (EXIF):** Se extraen los metadatos del PDF malicioso. El `Author` es un alias cirílico y la zona horaria del documento es `UTC+3`.
3. **CYB-P038 / CYB-P035:** Se busca el alias en foros de la Dark Web (Exploit.in). Se encuentra un handle idéntico que publicó un script en Python hace 3 años.
4. **CYB-I086 (Invariante):** Se busca el hash del script de hace 3 años en VirusTotal (CYB-P051), el cual tiene comentarios de la comunidad que asocian ese script a las fases iniciales del grupo *Sandworm*. Se mapea la intención y se ajustan las defensas a los TTPs conocidos del grupo.
