# GIT EXERGY: PRIMITIVES FRAMEWORK (1-100)

> Exergía = máximo trabajo útil extraíble. Aplicado a Git: máximo valor con mínimo desperdicio de esfuerzo, tiempo y recursos.

## 🧠 MENTALIDAD Y FILOSOFÍA (1-10)

### TIP 1: COMMITS ATÓMICOS
Cada commit = UNA sola cosa.
Un bug fix, una feature, un refactor.
Nunca mezcles. Si puedes describir el commit
con "y", es que deberías partirlo.

✗ "Arreglo login y cambio estilos y añado tests"
✓ "fix: validar email vacío en formulario login"

### TIP 2: COMMITS FRECUENTES, PUSH ESTRATÉGICO
Haz commit cada 15-30 minutos de trabajo.
Haz push cuando tengas algo coherente.
Commits frecuentes = checkpoints de seguridad.
Push estratégico = no contaminas el remoto.

### TIP 3: EL REPO ES DOCUMENTACIÓN VIVA
Tu historial de commits debería contar
la historia del proyecto. Un desarrollador
nuevo debería entender la evolución del
proyecto solo leyendo `git log --oneline`.

### TIP 4: NUNCA TRABAJES EN MAIN
Main es sagrado. Siempre funciona.
Siempre desplegable. Sin excepciones.
Incluso si trabajas solo.

### TIP 5: NOMBRA COMO SI OTRO LO LEYERA MAÑANA
Ramas, commits, tags, PRs...
Todo debe ser autoexplicativo.
Tu "yo del futuro" es ese "otro".

### TIP 6: GIT NO ES BACKUP, ES CONTROL DE VERSIONES
No hagas commits tipo "guardado del viernes".
Cada commit tiene intención y propósito.
Para backups usa otras herramientas.

### TIP 7: APRENDE A LEER ANTES DE ESCRIBIR
Domina `git log`, `git diff`, `git blame`, `git show`
ANTES de dominar `git push`.
El 70% del trabajo con Git es LEER historia.

### TIP 8: MENOS ES MÁS
Archivos pequeños > archivos grandes
Ramas cortas > ramas largas
PRs pequeños > PRs enormes
Mensajes concisos > mensajes vagos

### TIP 9: AUTOMATIZA LO REPETITIVO
Si haces algo más de 3 veces,
crea un alias, un hook o un script.
La exergía se pierde en la repetición manual.

### TIP 10: DOMINA 20 COMANDOS, NO 200
El 95% de tu trabajo usa el 20% de Git.
Domina ese 20% a la perfección.
El resto, consúltalo cuando lo necesites.
