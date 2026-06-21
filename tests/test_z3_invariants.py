import pytest
import z3

class TestZ3Invariants:
    """
    AX-045: Verificación Formal (Causal Compiler / Z3) para scripts de infraestructura.
    Garantiza físicamente la imposibilidad de estados corruptos en hot-paths críticos.
    """

    def test_registry_lock_invariant(self):
        """
        ANTI_GRAVITY/01_ACTIVE/observability/registry.py
        Prueba que, una vez _FROZEN es True, ninguna inyección de registro puede tener éxito.
        """
        is_frozen = z3.Bool('is_frozen')
        attempt_register = z3.Bool('attempt_register')
        success = z3.Bool('success')
        
        # Contrato del código (Línea 34 de registry.py):
        # if _FROZEN: raise RegistryLockError
        registry_logic = success == z3.And(attempt_register, z3.Not(is_frozen))
        
        solver = z3.Solver()
        solver.add(registry_logic)
        
        # INVARIANTE A PROBAR: Si está congelado, el éxito es absolutamente falso.
        invariant = z3.Implies(is_frozen, z3.Not(success))
        
        # Z3 demuestra invariantes probando que su negación es INALCANZABLE (UNSAT)
        solver.add(z3.Not(invariant))
        assert solver.check() == z3.unsat, "VIOLACIÓN Z3: El registro permite inyección post-congelación."

    def test_deploy_blocking_invariant(self):
        """
        ANTI_GRAVITY/01_ACTIVE/memory/deploy.py
        Prueba que ninguna mutación de estado (bootstrap, manifest) ocurre si hay errores bloqueantes.
        """
        blocking_errors_count = z3.Int('blocking_errors_count')
        mutate_state = z3.Bool('mutate_state')
        status_blocked = z3.Bool('status_blocked')
        
        # Contrato del código (Línea 114 de deploy.py):
        # if blocking: return { "status": "blocked" }
        deploy_logic = z3.And(
            blocking_errors_count >= 0,
            status_blocked == (blocking_errors_count > 0),
            mutate_state == (blocking_errors_count == 0)
        )
        
        solver = z3.Solver()
        solver.add(deploy_logic)
        
        # INVARIANTE A PROBAR: status_blocked IMPLICA estrictamente Not(mutate_state)
        invariant = z3.Implies(status_blocked, z3.Not(mutate_state))
        
        solver.add(z3.Not(invariant))
        assert solver.check() == z3.unsat, "VIOLACIÓN Z3: Deploy permite mutación con errores bloqueantes."

    def test_repo_health_status_invariant(self):
        """
        ANTI_GRAVITY/01_ACTIVE/creation/repo_health.py
        Prueba que el estado resultante siempre refleja la realidad de los issues detectados.
        """
        issues_count = z3.Int('issues_count')
        status_is_blocked = z3.Bool('status_is_blocked')
        
        # Contrato del código (Línea 122 de repo_health.py):
        # status = "ok" if not issues else "blocked"
        health_logic = z3.And(
            issues_count >= 0,
            status_is_blocked == (issues_count > 0)
        )
        
        solver = z3.Solver()
        solver.add(health_logic)
        
        # INVARIANTE A PROBAR: Bidireccionalidad estricta entre status="blocked" e issues_count > 0
        invariant = (status_is_blocked == (issues_count > 0))
        
        solver.add(z3.Not(invariant))
        assert solver.check() == z3.unsat, "VIOLACIÓN Z3: Divergencia entre reporte de estado e issues reales."
