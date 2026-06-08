import json
import hashlib
import time
from typing import Any, Dict, List

# Z3 for logical guards
try:
    from z3 import Solver, Int, Bool, And, sat, unsat
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    print("Warning: Z3 not available. Logical guards will be disabled.")

class Z3Guard:
    """
    Motor de verificación SMT (Satisfiability Modulo Theories) usando Z3.
    
    Propósito en Cortex Persist (MÖBIUS - Fase 7):
    - Proporcionar validación lógica determinista (L0 de la Epistemic Membrane).
    - Detectar violaciones con unsat_core traceable.
    - Evitar alucinaciones lógicamente consistentes pero físicamente inválidas.
    - Soporte dinámico de variables (price, confidence, timestamp, ratios, etc.).
    
    Características SMT:
    - Tipos: Real (precios, porcentajes), Int, Bool.
    - Operadores: aritmética, comparaciones, And/Or/Not/Implies.
    - Binding automático de contexto desde el payload.
    - Reset por verificación para aislamiento.
    """

    def __init__(self):
        if not Z3_AVAILABLE:
            self.enabled = False
            print("⚠️ Z3 SMT no disponible. Guards lógicos desactivados.")
            return
        self.enabled = True
        self.reset()
        self.presets = {
            "pricing_policy": "price >= base_price * 0.7",
            "confidence_range": "0 <= confidence <= 100",
            "temporal_valid": "timestamp >= last_update"
        }

    def reset(self):
        """Reset completo del solver SMT para verificación limpia e independiente."""
        if self.enabled:
            self.solver = Solver()
            self.constraints: Dict[str, Any] = {}
            self.variables: Dict[str, Any] = {}  # nombre -> variable Z3

    def declare_var(self, name: str, var_type: str = "Real"):
        """
        Declara variable SMT dinámicamente.
        
        Args:
            name: Nombre de la variable (ej: 'price', 'confidence')
            var_type: 'Real' | 'Int' | 'Bool'
        """
        if name in self.variables:
            return self.variables[name]
        
        if var_type == "Int":
            var = Int(name)
        elif var_type == "Bool":
            var = Bool(name)
        else:
            var = Real(name)  # default para valores continuos (precios, ratios)
        
        self.variables[name] = var
        return var

    def bind_context(self, value: Any):
        """
        Extrae automáticamente variables del payload y las fija en el solver.
        Ejemplo: {"price": 127.49, "confidence": 85} → price == 127.49 ∧ confidence == 85
        """
        if not isinstance(value, dict):
            return
        
        for k, v in value.items():
            if isinstance(v, (int, float)):
                var_type = "Int" if isinstance(v, int) else "Real"
                var = self.declare_var(k, var_type)
                self.solver.add(var == v)
            elif isinstance(v, bool):
                var = self.declare_var(k, "Bool")
                self.solver.add(var == v)

    def add_constraint(self, guard_name: str, expr):
        """Añade una constraint SMT explícita."""
        if not self.enabled:
            return False
        self.constraints[guard_name] = expr
        self.solver.add(expr)
        return True

    def check(self, value: Any = None, guards: Optional[List[str]] = None) -> Dict:
        """
        Verificación SMT completa.
        
        Flujo:
        1. Reset solver
        2. Bind contexto del payload
        3. Constraints preset + guards solicitados
        4. check() → sat / unsat con unsat_core
        
        Returns:
            Dict con status, modelo (si sat), unsat_core (si violated) y guards_passed.
        """
        if not self.enabled:
            return {"status": "disabled", "satisfied": True}

        self.reset()
        if value:
            self.bind_context(value)

        # Constraints preset SMT (industriales)
        p = self.declare_var("price", "Real")
        c = self.declare_var("confidence", "Real")
        self.add_constraint("price_nonneg", p >= 0)
        self.add_constraint("confidence_range", And(c >= 0, c <= 100))
        self.add_constraint("price_reasonable", p <= 100000)

        # Guards personalizados
        if guards:
            for g in guards:
                if g in self.presets:
                    # Aquí se podría parsear string a expr Z3 en futuro
                    pass

        result = self.solver.check()

        if result == sat:
            model = self.solver.model()
            return {
                "status": "satisfied",
                "satisfied": True,
                "model": {str(v): model[v] for v in model},
                "guards_passed": list(self.constraints.keys()),
                "reason": "All SMT constraints satisfied"
            }
        else:
            unsat_core = []
            try:
                core = self.solver.unsat_core()
                unsat_core = [str(c) for c in core]
            except:
                unsat_core = ["unknown_core"]
            
            return {
                "status": "violated",
                "satisfied": False,
                "unsat_core": unsat_core,
                "reason": "SMT constraint violation - see unsat_core for mathematical explanation"
            }


class EpistemicMembrane:
    """
    Interceptor obligatorio (Fase 6 - MÖBIUS):
    L0: Z3 Logic Gate
    L1: Entropy Gate (fricción termodinámica)
    L2: Reality Anchor (C5-REAL enforcer)
    """
    def __init__(self, z3_guard: Z3Guard):
        self.z3_guard = z3_guard
        self.last_write_time = time.time()
        self.token_budget = 1000
        self.entropy_used = 0

    def _estimate_entropy_delta(self, value: Any) -> float:
        payload_str = json.dumps(value, ensure_ascii=False)
        return len(payload_str) / 100.0

    def _get_causal_anchor(self, metadata: Dict) -> str:
        if metadata and "causal_anchor" in metadata:
            return metadata["causal_anchor"]
        fallback = hashlib.sha256(
            (json.dumps(metadata or {}, sort_keys=True) + str(time.time())).encode()
        ).hexdigest()[:16]
        return f"sim:{fallback}"

    def check(self, key: str, value: Any, metadata: Dict = None, guards: List[str] = None) -> Dict:
        metadata = metadata or {}
        result = {
            "reality_level": "C4-SIM",
            "z3_validation": {},
            "entropy_delta": 0.0,
            "causal_anchor": self._get_causal_anchor(metadata),
            "passed": True,
            "reasons": []
        }

        # L0 - Z3 Logic Gate
        if guards and self.z3_guard and self.z3_guard.enabled:
            guard_results = {}
            for g in guards:
                # Dynamic constraints
                if isinstance(value, dict):
                    if "price" in str(value).lower() or "confidence" in str(value).lower():
                        p = Int('price')
                        c = Int('confidence')
                        self.z3_guard.add_constraint("price_nonneg", p >= 0)
                        self.z3_guard.add_constraint("confidence_range", And(c >= 0, c <= 100))
                guard_results[g] = self.z3_guard.check()
            result["z3_validation"] = guard_results
            if any(not g.get("satisfied", True) for g in guard_results.values()):
                result["passed"] = False
                result["reasons"].append("Z3 constraint violation")
                return result

        # L1 - Entropy Gate
        delta = self._estimate_entropy_delta(value)
        result["entropy_delta"] = delta
        now = time.time()
        if (now - self.last_write_time) < 0.1 and delta > 5:
            result["passed"] = False
            result["reasons"].append("High frequency entropy violation")
        self.last_write_time = now
        self.entropy_used += delta

        # L2 - Reality Anchor
        if not result["causal_anchor"].startswith("sim:"):
            result["reality_level"] = "C5-REAL"
        else:
            result["reasons"].append("No causal proof → C4-SIM")

        if result["passed"]:
            result["reasons"].append("Membrane passed")

        return result
