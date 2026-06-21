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

## 🛠️ OPERACIONES BASE (11-25)

```bash
# 11. Ver estado del repositorio
git status

# 12. Ver estado resumido
git status -s

# 13. Agregar archivo específico al staging
git add archivo.txt

# 14. Agregar todos los archivos
git add .

# 15. Agregar archivos por patrón
git add *.js

# 16. Agregar de forma interactiva
git add -i

# 17. Agregar por parches (hunks)
git add -p

# 18. Eliminar archivo del repositorio y del disco
git rm archivo.txt

# 19. Eliminar archivo solo del repositorio (mantener en disco)
git rm --cached archivo.txt

# 20. Renombrar/mover archivo
git mv viejo.txt nuevo.txt

# 21. Deshacer cambios en archivo (working directory)
git checkout -- archivo.txt

# 22. Restaurar archivo (Git moderno)
git restore archivo.txt

# 23. Quitar archivo del staging
git restore --staged archivo.txt

# 24. Ver diferencias en working directory
git diff

# 25. Ver diferencias en staging
git diff --staged
```

## 📝 COMMITS (26-40)

```bash
# 26. Crear commit con mensaje
git commit -m "mensaje del commit"

# 27. Commit con add automático (archivos tracked)
git commit -am "mensaje del commit"

# 28. Modificar último commit
git commit --amend -m "nuevo mensaje"

# 29. Agregar archivos al último commit sin cambiar mensaje
git commit --amend --no-edit

# 30. Commit vacío (útil para triggers CI/CD)
git commit --allow-empty -m "trigger build"

# 31. Commit con coautoría
git commit -m "mensaje

Co-authored-by: Nombre <email@ejemplo.com>"

# 32. Ver historial de commits
git log

# 33. Historial en una línea
git log --oneline

# 34. Historial con gráfico
git log --oneline --graph --all

# 35. Historial con estadísticas
git log --stat

# 36. Historial de un archivo específico
git log -- archivo.txt

# 37. Buscar en mensajes de commits
git log --grep="bugfix"

# 38. Ver commits de un autor
git log --author="Nombre"

# 39. Ver commits entre fechas
git log --after="2024-01-01" --before="2024-12-31"

# 40. Ver detalle de un commit específico
git show abc1234
```

## 🌿 RAMAS (BRANCHES) (41-58)

```bash
# 41. Listar ramas locales
git branch

# 42. Listar todas las ramas (locales y remotas)
git branch -a

# 43. Listar ramas remotas
git branch -r

# 44. Crear nueva rama
git branch nueva-rama

# 45. Crear rama y cambiar a ella
git checkout -b nueva-rama

# 46. Crear rama y cambiar (Git moderno)
git switch -c nueva-rama

# 47. Cambiar de rama
git checkout nombre-rama

# 48. Cambiar de rama (Git moderno)
git switch nombre-rama

# 49. Renombrar rama actual
git branch -m nuevo-nombre

# 50. Eliminar rama local
git branch -d nombre-rama

# 51. Forzar eliminación de rama local
git branch -D nombre-rama

# 52. Eliminar rama remota
git push origin --delete nombre-rama

# 53. Fusionar rama en la actual
git merge nombre-rama

# 54. Merge sin fast-forward (genera commit de merge)
git merge --no-ff nombre-rama

# 55. Abortar un merge con conflictos
git merge --abort

# 56. Rebase de la rama actual
git rebase main

# 57. Rebase interactivo (últimos N commits)
git rebase -i HEAD~3

# 58. Abortar un rebase
git rebase --abort
```

## 🌐 REPOSITORIOS REMOTOS (59-75)

```bash
# 59. Ver remotos configurados
git remote -v

# 60. Agregar remoto
git remote add origin https://github.com/usuario/repo.git

# 61. Cambiar URL del remoto
git remote set-url origin https://github.com/usuario/nuevo-repo.git

# 62. Eliminar remoto
git remote remove origin

# 63. Renombrar remoto
git remote rename origin upstream

# 64. Descargar cambios sin fusionar
git fetch origin

# 65. Descargar de todos los remotos
git fetch --all

# 66. Traer y fusionar cambios (pull)
git pull origin main

# 67. Pull con rebase (evita commits de merge)
git pull --rebase origin main

# 68. Enviar cambios al remoto
git push origin main

# 69. Push forzado (¡cuidado!)
git push --force origin main

# 70. Push forzado seguro
git push --force-with-lease origin main

# 71. Push de nueva rama al remoto
git push -u origin nueva-rama

# 72. Push de todas las ramas
git push --all origin

# 73. Push de todos los tags
git push --tags

# 74. Ver información detallada de un remoto
git remote show origin

# 75. Limpiar referencias remotas obsoletas
git remote prune origin
```

## 🏷️ TAGS (76-82)

```bash
# 76. Listar tags
git tag

# 77. Crear tag ligero
git tag v1.0.0

# 78. Crear tag anotado
git tag -a v1.0.0 -m "Versión 1.0.0 estable"

# 79. Crear tag en commit específico
git tag -a v1.0.0 abc1234 -m "Release 1.0.0"

# 80. Eliminar tag local
git tag -d v1.0.0

# 81. Eliminar tag remoto
git push origin --delete v1.0.0

# 82. Push de un tag específico
git push origin v1.0.0
```

## 🛠️ HERRAMIENTAS AVANZADAS (83-95)

```bash
# 83. Guardar cambios temporalmente (stash)
git stash

# 84. Stash con mensaje descriptivo
git stash save "trabajo en progreso login"

# 85. Listar stashes
git stash list

# 86. Aplicar último stash (y mantenerlo)
git stash apply

# 87. Aplicar último stash (y eliminarlo)
git stash pop

# 88. Eliminar un stash específico
git stash drop stash@{0}

# 89. Limpiar todos los stashes
git stash clear

# 90. Cherry-pick: traer commit específico a rama actual
git cherry-pick abc1234

# 91. Buscar commit que introdujo un bug
git bisect start
git bisect bad          # commit actual es malo
git bisect good abc1234 # este commit era bueno

# 92. Ver quién modificó cada línea de un archivo
git blame archivo.txt

# 93. Crear archivo .gitignore
echo "node_modules/
.env
dist/
*.log" > .gitignore

# 94. Limpiar archivos no rastreados (dry run)
git clean -n

# 95. Limpiar archivos no rastreados (ejecutar)
git clean -fd
```

## 🔄 DESHACER Y RECUPERAR (96-100)

```bash
# 96. Revertir un commit (crea nuevo commit inverso)
git revert abc1234

# 97. Reset suave (mantiene cambios en staging)
git reset --soft HEAD~1

# 98. Reset mixto (mantiene cambios en working directory)
git reset --mixed HEAD~1

# 99. Reset duro (elimina todos los cambios) ⚠️
git reset --hard HEAD~1

# 100. Ver historial de TODOS los movimientos (recuperación)
git reflog
```

## 📋 FLUJO DE TRABAJO TÍPICO CONSOLIDADO

```bash
# Flujo completo para consolidar un repo en GitHub:

# 1️⃣  Crear repo en GitHub y clonar
git clone https://github.com/usuario/mi-proyecto.git
cd mi-proyecto

# 2️⃣  Configurar .gitignore
echo "node_modules/
.env
dist/" > .gitignore

# 3️⃣  Crear rama de desarrollo
git checkout -b develop

# 4️⃣  Trabajar en feature
git checkout -b feature/login

# 5️⃣  Hacer cambios y commits
git add .
git commit -m "feat: implementar formulario de login"

# 6️⃣  Actualizar con cambios remotos
git pull --rebase origin develop

# 7️⃣  Fusionar feature en develop
git checkout develop
git merge --no-ff feature/login

# 8️⃣  Push al remoto
git push origin develop

# 9️⃣  Cuando esté listo, merge a main y tag
git checkout main
git merge --no-ff develop
git tag -a v1.0.0 -m "Primera versión estable"
git push origin main --tags

# 🔟  Limpiar
git branch -d feature/login
git push origin --delete feature/login
```

> **💡 Tip de Exergía:** Usa `git reflog` como tu red de seguridad — registra TODO lo que haces y te permite recuperar casi cualquier cosa. Evita la pérdida catastrófica de entropía funcional.
