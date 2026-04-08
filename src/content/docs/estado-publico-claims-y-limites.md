---
title: "Estado público, claims y límites"
description: "Qué puede afirmarse públicamente sobre CORTEX Persist, qué requiere verificación adicional y qué no debe presentarse como hecho probado."
---

> Esta página separa tres cosas que suelen mezclarse en proyectos de infraestructura para agentes: lo que existe, lo que está implementado pero requiere contexto para verificarse, y lo que todavía no debe venderse como hecho probado.
>
> **Última revisión editorial:** 7 de abril de 2026

---

## Por qué existe esta página

CORTEX Persist tiene un repositorio real, documentación real y una superficie técnica visible. El problema no es si hay proyecto o no. El problema aparece cuando el mensaje público avanza más rápido que la parte verificable.

En una capa de confianza para agentes, eso es especialmente peligroso. Si la narrativa habla en términos absolutos y la evidencia pública todavía no llega hasta ahí, el producto pierde credibilidad justo en el eje donde dice aportar confianza.

Esta página fija la frontera documental pública de CORTEX:

- qué está respaldado hoy por el repositorio, la CLI y la documentación visible
- qué necesita una verificación adicional antes de publicarse como claim comercial
- qué no debe presentarse como benchmark, garantía legal o superficie estable todavía

---

## Alcance de la revisión

Esta página está escrita para la **superficie pública**. No presupone acceso a ramas privadas, despliegues internos, benchmarks no publicados ni materiales comerciales cerrados.

La frontera de evidencia aquí es:

- la web pública y la documentación publicada
- el repositorio público y sus archivos visibles
- la superficie real de la CLI documentada y observable en el código
- el empaquetado y exports visibles del paquete Python
- el texto oficial del **Reglamento (UE) 2024/1689** y la cronología pública de la Comisión Europea

Quedan fuera de esta página:

- pruebas internas no publicadas
- roadmaps no materializados
- demos privadas
- afirmaciones de ventas que no tengan un artefacto público reproducible detrás

---

## Niveles de evidencia

Para evitar ambigüedad, toda afirmación pública sobre CORTEX debería caer en uno de estos niveles:

| Nivel | Significado | ¿Se puede usar en la web? | Requisito mínimo |
|:---|:---|:---|:---|
| **A — Verificado públicamente** | Se puede confirmar hoy en el repo, la docs, la CLI o una URL pública accesible. | Sí | Debe existir un artefacto visible y actual. |
| **B — Implementado pero dependiente del entorno** | Existe en código o metadata, pero depende de despliegue, publicación o configuración externa. | Sí, con matiz | Hay que explicar que requiere verificación operativa. |
| **C — Parcial o no alineado** | Hay piezas reales, pero el mensaje público no coincide exactamente con la superficie visible. | No, sin corrección previa | Debe reescribirse antes de publicarse. |
| **D — Aspiracional / roadmap** | Idea válida, pero sin prueba pública reproducible. | No como claim factual | Debe etiquetarse como roadmap o hipótesis. |

---

## Qué sí puede decirse hoy con respaldo público

### 1. Existe un producto técnico real

Esto sí está soportado por el repositorio público:

- existe un paquete Python llamado `cortex-persist` en la metadata del proyecto
- existe un binario de CLI llamado `cortex`
- existe una implementación Python central exportada como `CortexEngine`
- hay documentación pública para quickstart, CLI, API, seguridad, arquitectura y compliance
- el proyecto describe una arquitectura local-first sobre SQLite con verificación hash-chained y checkpoints Merkle

Fuentes públicas de referencia:

- [pyproject.toml](https://github.com/borjamoskv/Cortex-Persist/blob/main/pyproject.toml)
- [cortex/__init__.py](https://github.com/borjamoskv/Cortex-Persist/blob/main/cortex/__init__.py)
- [Quickstart](quickstart.md)
- [CLI](cli.md)
- [Architecture](architecture.md)
- [Security](security.md)

### 2. La narrativa correcta es "tamper-evident", no "magia"

La forma prudente y verificable de describir CORTEX hoy es:

- capa de evidencia para memoria de agentes
- registro hash-chained de hechos y decisiones
- exports y artefactos de auditoría reproducibles
- verificación de continuidad e integridad del ledger
- controles técnicos útiles para trazabilidad y revisión posterior

Eso es compatible con el repositorio visible y con la CLI pública actual.

### 3. La CLI pública tiene una superficie real y usable

La documentación y el código visible permiten sostener, al menos, estas operaciones:

- `cortex init`
- `cortex store ...`
- `cortex verify FACT_ID`
- `cortex trust-ledger verify`
- `cortex trust-ledger checkpoint`
- `cortex audit --project PROJECT --limit N`
- `cortex compliance-report`

Fuentes:

- [cortex/cli/init_cmds.py](https://github.com/borjamoskv/Cortex-Persist/blob/main/cortex/cli/init_cmds.py)
- [cortex/cli/trust_cmds.py](https://github.com/borjamoskv/Cortex-Persist/blob/main/cortex/cli/trust_cmds.py)
- [CLI](cli.md)

### 4. El enfoque local-first y la base criptográfica sí son parte del contrato público

El paquete, el README y la docs pública sí sostienen hoy estas ideas:

- SQLite como base operativa inicial
- SHA-256 para encadenado hash
- checkpoints Merkle para verificación por lotes
- auditoría y evidencia como problema de producto, no como simple logging

Eso no significa que cada claim operacional asociado a esas primitivas esté automáticamente demostrado. Significa que las primitivas están presentes en la historia pública del producto.

---

## Qué requiere matiz antes de publicarse como claim

### `pip install cortex-persist`

La metadata del proyecto y la documentación apuntan a `cortex-persist` como nombre del paquete. Eso se ve en:

- [pyproject.toml](https://github.com/borjamoskv/Cortex-Persist/blob/main/pyproject.toml)
- [Quickstart](quickstart.md)
- [SDKs](sdks.md)

Pero una cosa es que el proyecto **quiera** publicarse o se documente así, y otra que la publicación pública en PyPI esté accesible y actualizada en el momento en que se hace el claim.

Regla editorial:

- si no se ha validado el paquete público justo antes de publicar, usa "install from source" o "check latest package availability"
- no conviertas el nombre del paquete en prueba automática de distribución pública operativa

### SDK Python vs surface del paquete raíz

Hay dos realidades distintas en el repositorio:

- el paquete raíz `cortex` exporta públicamente `CortexEngine`
- existe además un SDK separado bajo `cortex-sdk/cortex_persist` que exporta `CortexClient` y `AsyncCortexClient`

Fuentes:

- [cortex/__init__.py](https://github.com/borjamoskv/Cortex-Persist/blob/main/cortex/__init__.py)
- [cortex-sdk/cortex_persist/__init__.py](https://github.com/borjamoskv/Cortex-Persist/blob/main/cortex-sdk/cortex_persist/__init__.py)

Eso obliga a escribir la documentación con precisión:

- si el ejemplo usa `from cortex import CortexEngine`, está describiendo la superficie del paquete raíz
- si el ejemplo usa `from cortex_persist import CortexClient`, debe explicar que habla del SDK separado y su estado de distribución
- no mezcles ambos imports como si fueran la misma API pública estable

### Integraciones macOS

La presencia de `mac_maestro` en el repo demuestra trabajo real en integración macOS, pero no autoriza a documentar cualquier nombre de clase como API pública estable.

La superficie visible exportada hoy incluye:

- `MaestroExecutor`
- `MacAction`
- `MacIntent`
- `VerificationOracle`
- `OracleVerdict`

Fuente:

- [cortex/mac_maestro/__init__.py](https://github.com/borjamoskv/Cortex-Persist/blob/main/cortex/mac_maestro/__init__.py)

Si una página o landing usa nombres distintos, esa diferencia debe corregirse o etiquetarse como experimental.

### Estado operativo de dominios y builds públicas

Una separación `.com` y `.dev` puede ser una buena estrategia editorial. Pero la mera existencia de la build local o del código fuente no equivale a disponibilidad pública correcta.

Antes de prometer:

- que `.dev` es la superficie oficial de docs
- que una URL concreta ya está live
- que una demo pública es la fuente canónica

hay que verificar:

- resolución DNS
- deploy activo
- enlaces internos
- coherencia entre build y repo

Esto pertenece al plano **operativo**, no al plano conceptual del producto.

---

## Qué no debe venderse hoy como hecho cerrado

### Benchmarks fuertes sin receta pública

Claims del tipo:

- "0.04 ms hallucination interception"
- "1000x compression"
- cualquier latencia extrema o multiplicador espectacular

no deberían aparecer como hechos cerrados sin una página pública que detalle:

- hardware
- configuración
- dataset
- tamaño de lote
- modo de almacenamiento
- versión exacta del código
- comando o harness reproducible

Sin eso, el claim es marketing, no evidencia.

### "Compliance" como destino automático

CORTEX puede ayudar con trazabilidad, registro, evidencia y revisión. Eso **no** equivale por sí solo a:

- certificación legal
- conformidad automática
- clasificación regulatoria resuelta
- cobertura organizativa completa

La compliance real depende, entre otras cosas, de:

- el caso de uso concreto
- el rol del operador o proveedor
- la clasificación de riesgo del sistema desplegado
- procesos organizativos y de gobernanza fuera del código

### "CORTEX detiene las alucinaciones"

La posición técnicamente honesta es:

- CORTEX hace más auditable el estado
- CORTEX hace más visible la procedencia, continuidad y revisión de decisiones
- CORTEX no convierte una salida generativa errónea en verdadera

La trazabilidad no sustituye a la veracidad.

---

## Fuente de verdad actual para la CLI

Cuando haya conflicto entre una demo de marketing y la CLI visible, la fuente de verdad debe ser el código y la referencia de CLI.

| Tema | Superficie que sí está alineada hoy | Qué no conviene publicar si no existe en el código |
|:---|:---|:---|
| Inicialización | `cortex init` | `cortex init --ledger main` |
| Verificación individual | `cortex verify FACT_ID` | `cortex verify --integrity-check` |
| Ledger completo | `cortex trust-ledger verify` | nombres no presentes en la CLI |
| Auditoría | `cortex audit --project PROJECT --limit N` | `--taint-detection` si no existe realmente |
| Snapshot técnico | `cortex compliance-report` | lenguaje de certificación legal automática |

Regla simple:

> Si el flag no aparece en `--help` o en el módulo de CLI correspondiente, no debe aparecer en la landing ni en snippets públicos.

---

## Fuente de verdad actual para SDKs e imports

### Paquete raíz

El paquete raíz documentable hoy es:

```python
from cortex import CortexEngine
```

Ese es el import coherente con la superficie exportada por el paquete `cortex`.

### SDK separado

Si se quiere documentar un cliente HTTP o una capa de SDK separada, debe explicarse que vive en otra superficie del repositorio:

```python
from cortex_persist import CortexClient, AsyncCortexClient
```

Eso no debería presentarse como sinónimo automático del paquete raíz mientras no exista una historia pública claramente unificada de distribución, versión y soporte.

### Regla editorial

No usar:

- imports inventados
- nombres de clases no exportadas públicamente
- imports de conveniencia que no coinciden con el árbol visible del repo

Sí usar:

- imports trazables a `__init__.py`
- ejemplos que un lector pueda confirmar sin adivinar

---

## Límite legal: qué puede decirse sobre el AI Act

### Lo que el texto oficial sí sostiene

El **Artículo 12** del Reglamento (UE) 2024/1689 exige, para sistemas de alto riesgo, capacidad técnica para el registro automático de eventos y un nivel de trazabilidad adecuado al propósito del sistema. La cronología oficial de la Comisión Europea sigue tratando el **2 de agosto de 2026** como el gran hito de aplicabilidad general, con excepciones y aplicación escalonada.

Fuentes oficiales:

- [EUR-Lex — Regulation (EU) 2024/1689](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689)
- [European Commission — Navigating the AI Act](https://digital-strategy.ec.europa.eu/en/faqs/navigating-ai-act)
- [European Commission — AI Act framework](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)

### Lo que no conviene afirmar literalmente

No es prudente convertir el Artículo 12 en esta frase:

> "El Artículo 12 exige audit trails inmutables."

Esa formulación es demasiado fuerte para la letra pública del texto. La lectura más defendible es:

- el AI Act exige logging automático y trazabilidad apropiada en determinados supuestos
- CORTEX aporta controles técnicos que pueden ayudar a satisfacer requisitos de trazabilidad, registro e integridad
- el reglamento no prescribe literalmente "Merkle trees", "SHA-256", "inmutabilidad sellada" o una única implementación técnica

### Multas: cómo no exagerar

Tampoco conviene usar el máximo de **35 millones de euros o 7%** como si fuera la consecuencia automática de cualquier incumplimiento relacionado con trazabilidad o documentación.

En el texto oficial, ese máximo está asociado al incumplimiento de las prácticas prohibidas del **Artículo 5**. Para otros incumplimientos regulatorios, el reglamento prevé otros escalones sancionadores, incluyendo supuestos de **15 millones o 3%**.

Regla editorial:

- si se mencionan sanciones, hay que indicar a qué tipo de infracción corresponden
- si no se va a explicar ese contexto, es mejor no poner cifras de multa en la landing

---

## Frases seguras vs frases que deberían evitarse

| Mejor usar | Evitar |
|:---|:---|
| "CORTEX provides tamper-evident memory and decision records." | "CORTEX makes your AI compliant." |
| "CORTEX can support Article 12-style traceability and record-keeping controls." | "Article 12 requires immutable Merkle-sealed audit trails." |
| "CORTEX exposes a verifiable CLI and a public Python engine surface." | "The CLI shown here is authoritative" si los flags no existen en el código |
| "Package metadata targets `cortex-persist`; verify public package availability before publishing install claims." | "Install from PyPI" sin comprobar la publicación pública actual |
| "Benchmarks should be tied to a reproducible setup." | "0.04 ms" o "1000x" sin benchmark público enlazado |

---

## Política de claims de rendimiento

Si se quiere publicar rendimiento, la documentación debe exigir un benchmark reproducible mínimo.

### Un benchmark público aceptable debe incluir

- revisión o commit exacto
- CPU, RAM y sistema operativo
- si usa SQLite local, red o caché
- número de registros
- tamaño medio del payload
- cold start vs warm run
- comando exacto o script de benchmark
- mediana, p95 y número de iteraciones

### Mientras eso no exista

Usa frases de posicionamiento, no cifras absolutas:

- "designed for low-latency local verification"
- "optimized for local-first evidence workflows"
- "intended for lightweight integrity checks on operator-managed storage"

No uses:

- récords de latencia sin receta
- multiplicadores sin baseline público
- claims comparativos contra otras herramientas sin metodología

---

## Checklist antes de publicar una landing, artículo o demo

1. **CLI**: ejecutar `cortex --help`, `cortex init --help`, `cortex audit --help` y comprobar que los snippets usan flags reales.
2. **Imports**: comprobar que cada import del ejemplo existe en un `__init__.py` público o se presenta como módulo específico.
3. **Instalación**: verificar si la publicación pública del paquete está accesible ahora mismo. Si no, usar instalación desde fuente.
4. **Links**: comprobar que `.com`, `.dev`, docs y GitHub resuelven y no se contradicen.
5. **Benchmarks**: no publicar cifras si no hay una receta reproducible enlazada.
6. **Legal**: revisar el texto del AI Act y evitar presentar interpretación jurídica como obligación literal.
7. **Compliance**: hablar de "technical alignment", "support", "mapping" o "controls", no de certificación automática.
8. **Surface area**: si una función es experimental, privada o vive en otra carpeta del repo, etiquetarla como tal.

---

## Comandos de verificación rápida

Estos checks sirven para validar claims antes de publicar copy nueva:

```bash
# Ver el nombre del paquete y entrypoint
rg -n "^name =|^version =|^cortex =" pyproject.toml

# Ver export público del paquete raíz
sed -n '1,160p' cortex/__init__.py

# Ver si el SDK separado exporta un cliente distinto
sed -n '1,160p' cortex-sdk/cortex_persist/__init__.py

# Ver flags reales de inicialización y trust commands
sed -n '1,200p' cortex/cli/init_cmds.py
sed -n '1,260p' cortex/cli/trust_cmds.py

# Ver la documentación pública actual
sed -n '1,220p' src/content/docs/quickstart.md
sed -n '1,220p' src/content/docs/cli.md
sed -n '1,220p' src/content/docs/sdks.md
```

Y si se está preparando una demo manual:

```bash
cortex --help
cortex init --help
cortex verify --help
cortex audit --help
```

---

## Qué debería poder decir un auditor técnico honesto hoy

Una formulación responsable, a fecha de esta revisión, sería algo así:

> CORTEX Persist es un proyecto real con repositorio, documentación y superficie CLI visibles. Su posicionamiento más defendible hoy es el de capa de evidencia y verificación para memoria y decisiones de agentes, con registros hash-chained y exports auditables. Puede mapearse a controles de trazabilidad y record-keeping, pero no debe presentarse como certificación legal automática ni como benchmark cerrado sin pruebas públicas reproducibles.

Si una landing, deck o artículo no puede sostenerse con una frase de este estilo, probablemente está vendiendo más certeza de la que la evidencia pública permite.

---

## Preguntas frecuentes

### ¿Esta página dice que CORTEX no funciona?

No. Dice algo más útil: que una cosa es que exista código real y otra distinta es que toda promesa pública esté ya respaldada con el mismo nivel de prueba.

### ¿Entonces no debe hablarse de compliance?

Sí debe hablarse, pero con precisión:

- mapping técnico
- soporte a trazabilidad
- controles de registro e integridad
- límites de alcance

No como garantía jurídica total.

### ¿Debe eliminarse todo lenguaje fuerte?

No. Debe mantenerse el lenguaje fuerte donde haya evidencia fuerte. En confianza e infraestructura, una frase sobria y verificable vale más que una frase maximalista que se cae al primer due diligence.

### ¿Esta página sustituye la revisión legal?

No. Esta página es una barrera editorial y técnica. La revisión legal sigue siendo obligatoria cuando se hacen afirmaciones regulatorias o de responsabilidad.

---

## Relación con otras páginas

Lee esta página junto con:

- [Compliance](compliance.md)
- [Quickstart](quickstart.md)
- [CLI](cli.md)
- [SDKs](sdks.md)
- [Security](security.md)
- [FAQ](faq.md)

La función de esta página no es repetir toda la documentación. Su función es fijar la frontera entre evidencia pública, copy defensible y exageración evitable.
