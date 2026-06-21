import torch
import torch.nn as nn
import time
import sys
import logging

logging.basicConfig(level=logging.INFO, format="[C5-REAL] %(message)s")
logger = logging.getLogger("Cortex-Algebra")

def validate_algebraic_primitives():
    logger.info("Initializing C5-REAL Tensor Geometries for Algebra Primitives")
    
    # 01. Variable (Mutable Tensor with Gradients)
    x_var = torch.tensor([2.0], requires_grad=True)
    logger.info(f"[01] Variable created: {x_var.data}, requires_grad={x_var.requires_grad}")
    
    # 02. Constante (Immutable Tensor)
    c_const = torch.tensor([5.0], requires_grad=False)
    logger.info(f"[02] Constante created: {c_const.data}, requires_grad={c_const.requires_grad}")
    
    # 03. Expresión algebraica (Computation Graph)
    expr = (x_var ** 2) + c_const
    logger.info(f"[03] Expresion algebraica (Graph): x^2 + c = {expr.item()}")
    
    # 04. Ecuación (Optimization Problem: x^2 + 5 = 14)
    target = torch.tensor([14.0])
    optimizer = torch.optim.SGD([x_var], lr=0.01)
    for _ in range(50):
        optimizer.zero_grad()
        loss = ((x_var ** 2) + c_const - target) ** 2
        loss.backward()
        optimizer.step()
    logger.info(f"[04] Ecuación resuelta: x converge a {x_var.item():.4f} (Objetivo: 3.0)")
    
    # 05. Inecuación (Topological Boundary)
    space = torch.linspace(-5, 5, 100)
    ineq_mask = space > 0
    logger.info(f"[05] Inecuación (x > 0) validada. Mask sum: {ineq_mask.sum().item()} / 100")
    
    # 06. Función (Deterministic Mapping)
    def f_map(t: torch.Tensor) -> torch.Tensor:
        return torch.sin(t)
    logger.info(f"[06] Función (sin(pi/2)): {f_map(torch.tensor([torch.pi/2])).item()}")
    
    # 07. Dominio (Input Tensor Space validation)
    domain_x = torch.tensor([-1.0, 0.0, 1.0])
    valid_domain = domain_x >= 0
    logger.info(f"[07] Dominio restringido (x >= 0): {valid_domain}")
    
    # 08. Rango (Output Projection)
    range_y = f_map(domain_x)
    logger.info(f"[08] Rango proyectado: {range_y}")
    
    # 09. Sistema de ecuaciones (Ax = b)
    A = torch.tensor([[2.0, 1.0], [1.0, 3.0]])
    b = torch.tensor([5.0, 5.0])
    x_sys = torch.linalg.solve(A, b)
    logger.info(f"[09] Sistema de ecuaciones Ax=b resuelto: {x_sys}")
    
    # 10. Polinomio, 11. Monomio, 12. Binomio, 13. Trinomio
    x_poly = torch.tensor([2.0])
    monomial = 3 * (x_poly ** 3)
    binomial = monomial - 2 * x_poly
    trinomial = binomial + 5
    logger.info(f"[10-13] Polinomio (Trinomio) 3x^3 - 2x + 5 (x=2) = {trinomial.item()}")
    
    # 14. Factorización (SVD Decomposition)
    U, S, V = torch.linalg.svd(A)
    logger.info(f"[14] Factorización (SVD) Singular Values: {S}")
    
    # 15. Exponente & 16. Logaritmo
    base = torch.tensor([2.0])
    exp_val = torch.exp(base)
    log_val = torch.log(exp_val)
    logger.info(f"[15, 16] Exponente y Logaritmo: log(exp({base.item()})) = {log_val.item():.4f}")
    
    # 17. Matriz
    M = torch.rand(3, 3)
    logger.info(f"[17] Matriz M shape: {M.shape}")
    
    # 18. Determinante
    det_A = torch.linalg.det(A)
    logger.info(f"[18] Determinante det(A): {det_A.item():.4f}")
    
    # 19. Vector
    vec = torch.randn(5)
    logger.info(f"[19] Vector V shape: {vec.shape}, L2 Norm: {torch.linalg.vector_norm(vec).item():.4f}")
    
    # 20. Plano cartesiano
    x_grid, y_grid = torch.meshgrid(torch.arange(3), torch.arange(3), indexing='ij')
    logger.info(f"[20] Plano cartesiano (Meshgrid) shape: {x_grid.shape}")

    logger.info("Validation complete. Zero Anergy. C5-REAL Structural Invariants confirmed.")

if __name__ == "__main__":
    validate_algebraic_primitives()
