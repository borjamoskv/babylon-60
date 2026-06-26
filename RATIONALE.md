# RATIONALE DE DISEÑO (BABYLON-60)

Este documento aísla la filosofía arquitectónica ("por qué") de la especificación normativa ("qué").

## 1. Minimalismo Extremo del TCB
La confianza no debe recaer en que el código de ejecución sea impenetrable, sino en que el código de ejecución sea **descartable**. Al reducir el Trusted Computing Base (TCB) a la semántica formal, el intérprete de referencia, la especificación del Proof IR y el verificador del artefacto, permitimos la evolución de motores paralelos (ej. versiones de CPU vs GPU) sin corromper la verdad matemática.

## 2. El Paradigma de Open Conformity
La interoperabilidad no es una amenaza competitiva, es un multiplicador de confianza. Si un tercero construye un motor concurrente en C++ o Zig, y dicho motor emite un *Artifact Bundle* cuyo hash global converge idénticamente con el del Intérprete de Referencia, el motor de terceros es validado. La seguridad por oscuridad es una falacia entrópica.

## 3. Desacoplamiento del Theorem Prover
No anclamos el kernel a Lean 4 o Coq. Compilamos hacia un `Proof IR` nativo. La traducción semántica a los axiomas específicos de un demostrador particular ocurre fuera del bucle crítico (Ouroboros) de ejecución de la máquina virtual. Esto garantiza la persistencia matemática del artefacto exportado a través de las décadas, independientemente de qué software de verificación domine en el futuro.
