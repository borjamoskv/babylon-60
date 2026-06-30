def score_project(state):
    score = 100
    penalties = []
    bonuses = []

    # Penalizaciones
    orphans = state.current_architecture.get("possible_orphans", [])
    if orphans:
        penalty = min(len(orphans) * 3, 20)
        score -= penalty
        penalties.append(f"-{penalty} pts: {len(orphans)} módulos huérfanos")

    high_coupling = state.current_architecture.get("high_coupling_files", {})
    if high_coupling:
        penalty = min(len(high_coupling) * 4, 20)
        score -= penalty
        penalties.append(f"-{penalty} pts: {len(high_coupling)} archivos con acoplamiento alto")

    debt = state.technical_debt
    if debt:
        penalty = min(len(debt) * 2, 15)
        score -= penalty
        penalties.append(f"-{penalty} pts: {len(debt)} items de deuda técnica")

    conflicts = state.conflicts
    if conflicts:
        penalty = min(len(conflicts) * 5, 20)
        score -= penalty
        penalties.append(f"-{penalty} pts: {len(conflicts)} conflictos detectados")

    # Bonificaciones
    if state.stack.get("markdown_docs"):
        score += 5
        bonuses.append("+5 pts: documentación markdown presente")

    total_functions = state.current_architecture.get("total_functions", 0)
    if total_functions > 0:
        score += 5
        bonuses.append("+5 pts: código funcional detectado")

    score = max(0, min(100, score))

    if score >= 80:
        label = "🟢 SALUDABLE"
    elif score >= 50:
        label = "🟡 NECESITA ATENCIÓN"
    else:
        label = "🔴 CRÍTICO"

    return {
        "score": score,
        "label": label,
        "penalties": penalties,
        "bonuses": bonuses
    }
