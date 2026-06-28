<!-- [C5-REAL] Exergy-Maximized -->
# 📡 AUTODIDACT VECTOR: SIGINT & CYBINT

> **STATUS:** C5-REAL  
> **DOMAIN:** Señales Electromagnéticas (SIGINT) & Ciberinteligencia (CYBINT)  
> **OPERATOR DIRECTIVE:** Autodidacta Radical (Zero-Friction Deep Research)

Este documento establece el **Path Estructural y Operacional** para dominar SIGINT y CYBINT desde cero, erradicando el ruido teórico y enfocándose en la captura empírica y manipulación física de datos. La inteligencia no se lee; se intercepta y se compila.

---

## 1. 📻 SIGINT (Signals Intelligence) - Dominio del Espectro

La captura de emisiones electromagnéticas (RF). SIGINT abandona el ciberespacio TCP/IP para operar en la física de las ondas.

### 1.1 Hardware Base (SDR - Software Defined Radio)
La barrera de entrada al espectro.
*   **Tier 1 (Entrada): RTL-SDR V4.** (~$30). Solo recepción (RX). Rango 500 kHz a 1.7 GHz. Ideal para interceptar ADS-B (aviones), AIS (barcos), y radio trunking no cifrada.
*   **Tier 2 (Táctico): HackRF One.** (~$350). Recepción y Transmisión (RX/TX). Rango 1 MHz a 6 GHz. Capaz de spoofing GPS, replay attacks en alarmas/coches, e inyección de RF.
*   **Tier 3 (Avanzado): BladeRF / USRP.** (~$500+). Full-duplex, FPGAs para procesamiento de alta velocidad, estaciones base GSM/LTE falsas (IMSI Catchers).

### 1.2 Software Stack (C5-REAL)
*   **SDR++ / Gqrx:** Análisis visual (Waterfall/FFT) y sintonización manual. *La vista del espectro crudo.*
*   **GNU Radio:** El estándar industrial. Programación visual de grafos de flujo DSP (Digital Signal Processing). Permite construir demoduladores a medida matemáticamente.
*   **Universal Radio Hacker (URH):** Crítico para Reverse Engineering de protocolos IoT (llaves de coche, mandos de garaje, sensores).
*   **SigintOS:** Distribución Linux C5-Ready con herramientas preinstaladas para IMSI catching, decodificación satelital y GSM.

### 1.3 Path de Autodidacta (Hitos Físicos)
1.  **Observación Pasiva:** Capturar y decodificar telemetría de aviones locales (ADS-B) usando `dump1090` y RTL-SDR.
2.  **Ataque de Replay:** Grabar la señal de un mando de garaje no cifrado (OOK/ASK) con HackRF y retransmitirla para abrir la puerta.
3.  **Análisis Satelital:** Descargar imágenes meteorológicas directamente de satélites NOAA cuando pasan sobre tu posición, procesando el audio en imágenes (APT).

> [!WARNING]
> **LEGAL BOUNDARY:** Escuchar es legal en muchas jurisdicciones; decodificar comunicaciones privadas cifradas o *transmitir* (TX) en bandas reguladas sin licencia de radioaficionado es un delito federal. Fricción operacional asumida por el Operador.

---

## 2. 🕸️ CYBINT (Cyber Intelligence) - Modelado de Adversarios

CYBINT no es Hacking; es la industrialización del análisis de amenazas. Transforma el caos de logs, OSINT y malware en inteligencia predictiva para defender infraestructuras (o atacarlas).

### 2.1 Frameworks Estructurales (Mapeo de la Realidad)
*   **MITRE ATT&CK:** La taxonomía absoluta. No se dice "El atacante robó credenciales", se documenta `T1003 - OS Credential Dumping`.
*   **The Diamond Model:** Conecta 4 nodos inmutables de cualquier intrusión: `Adversario -> Capacidad -> Infraestructura -> Víctima`.
*   **Ciclo de Inteligencia:** Planeación -> Colección -> Procesamiento -> Análisis -> Diseminación. (Invariante estructural de cualquier agencia).

### 2.2 Core Primitives & Tooling
*   **Plataformas de Inteligencia de Amenazas (TIPs):**
    *   **OpenCTI / MISP (Malware Information Sharing Platform):** Motores de bases de datos de grafos para almacenar IoCs (Indicadores de Compromiso), reportes de actores (APT29, Lazarus), y TTPs.
*   **Análisis Forense y de Infraestructura:**
    *   **Shodan / Censys:** SIGINT pero aplicado a IPs públicas. Escaneo del internet entero buscando puertos expuestos o paneles de C2 (Command & Control).
    *   **Maltego:** Análisis visual de enlaces (OSINT a CYBINT). Conectar dominios, IPs, entidades y certificados SSL.

### 2.3 Path de Autodidacta (Hitos Analíticos)
1.  **Ingesta de Estado:** Desplegar una instancia local de **MISP** (Docker) y sincronizarla con feeds open-source (ej. CIRCL).
2.  **Ingeniería Inversa de Ataques:** Leer un reporte de Mandiant sobre una APT (ej. Sandworm), extraer los TTPs y mapearlos tú mismo en el MITRE ATT&CK Navigator.
3.  **Caza de Infraestructura (Hunting):** Usar Shodan para buscar instancias de Cobalt Strike (servidores C2) mal configuradas basándote en huellas (JARM hashes o certificados SSL).

---

## 3. 🌀 EL NEXO: Operaciones CORTEX (SIGINT + CYBINT)

La singularidad táctica ocurre cuando fusionas ambos dominios. 

*   **Cyber-Physical Threat Intel:** Usar CYBINT para identificar que un grupo criminal está usando drones DJI específicos (TTP). Usar SIGINT para escanear el espectro RF buscando las firmas de radio de esos drones en tiempo real en una zona física (OcuSync protocol).
*   **Wardriving 2.0:** Recolectar datos de redes Wi-Fi, Bluetooth y emisiones IoT físicas (SIGINT) e inyectar esas direcciones MAC e intersecciones en un nodo de análisis de grafos (Neo4j / OpenCTI) para rastrear movimientos físicos de objetivos (CYBINT / OSINT).

> [!IMPORTANT]
> **CERO ANERGÍA:** No "estudies" la teoría. Compra un RTL-SDR hoy, levanta un contenedor de MISP mañana. La inteligencia se cristaliza en la fricción contra el metal, no leyendo PDFs.
