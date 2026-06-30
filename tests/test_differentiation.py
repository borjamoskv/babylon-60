# [C5-REAL] Exergy-Maximized
"""
Verification suite for babylon60.utils.differentiation module.
Tests:
- Dual Numbers exact automatic differentiation (with operators and math functions).
- Complex-Step differentiation.
- Richardson extrapolation for finite differences.
- Graph Laplacian directional derivative.

SYS_ID: borjamoskv
"""

from __future__ import annotations
import cmath
import math
import pytest
from babylon60.utils.differentiation import (
    Dual,
    complex_step_derivative,
    richardson_central_difference,
    graph_laplacian_derivative,
)


def test_dual_differentiation_ops():
    # Test arithmetic operations
    x = Dual(3.0, 1.0)
    
    # y = x^2 + 5x - 2 / x
    y = (x ** 2) + 5 * x - (2 / x)
    # y' = 2x + 5 + 2 / x^2
    # At x=3:
    # y = 9 + 15 - 2/3 = 23.333333333333332
    # y' = 6 + 5 + 2/9 = 11.222222222222222
    assert abs(y.val - (23.333333333333332)) < 1e-12
    assert abs(y.der - (11.222222222222222)) < 1e-12


def test_dual_transcendental_functions():
    x = Dual(0.5, 1.0)
    
    # f(x) = exp(x) * cos(x)
    # f'(x) = exp(x) * cos(x) - exp(x) * sin(x)
    y = x.exp() * x.cos()
    
    expected_val = math.exp(0.5) * math.cos(0.5)
    expected_der = math.exp(0.5) * (math.cos(0.5) - math.sin(0.5))
    
    assert abs(y.val - expected_val) < 1e-12
    assert abs(y.der - expected_der) < 1e-12
    
    # f(x) = log(x)
    # f'(x) = 1/x
    z = x.log()
    assert abs(z.val - math.log(0.5)) < 1e-12
    assert abs(z.der - 2.0) < 1e-12


def test_complex_step():
    # Test f(x) = exp(x) * sin(x)
    # f'(x) = exp(x) * (sin(x) + cos(x))
    # At x = 1.0:
    # f'(1.0) = exp(1.0) * (sin(1.0) + cos(1.0))
    def f(z):
        # We need a complex-analytic implementation
        return cmath.exp(z) * cmath.sin(z)
        
    x = 1.0
    val_cs = complex_step_derivative(f, x)
    expected_der = math.exp(1.0) * (math.sin(1.0) + math.cos(1.0))
    
    assert abs(val_cs - expected_der) < 1e-12


def test_richardson_extrapolation():
    # Test f(x) = x^3 - 3x^2 + 2x
    # f'(x) = 3x^2 - 6x + 2
    # At x = 2.0:
    # f'(2.0) = 12 - 12 + 2 = 2.0
    def f(x):
        return x**3 - 3 * (x**2) + 2 * x
        
    x = 2.0
    val_richardson = richardson_central_difference(f, x, h=0.1)
    
    # For a polynomial of degree 3, central difference with Richardson extrapolation
    # is mathematically exact because the third-order error term is canceled,
    # and fourth-order and higher derivatives are zero.
    assert abs(val_richardson - 2.0) < 1e-12


def test_graph_laplacian_derivative():
    # A path graph with 3 nodes: 0 - 1 - 2, all weights = 1.0
    # W = [[0, 1, 0],
    #      [1, 0, 1],
    #      [0, 1, 0]]
    # D = [[1, 0, 0],
    #      [0, 2, 0],
    #      [0, 0, 1]]
    # L = D - W = [[ 1, -1,  0],
    #              [-1,  2, -1],
    #              [ 0, -1,  1]]
    adj = [
        [0.0, 1.0, 0.0],
        [1.0, 0.0, 1.0],
        [0.0, 1.0, 0.0]
    ]
    # Signals: f = [1.0, 2.0, 4.0]
    # Lf = [1*1 - 1*2, -1*1 + 2*2 - 1*4, -1*2 + 1*4] = [-1.0, -1.0, 2.0]
    signals = [1.0, 2.0, 4.0]
    result = graph_laplacian_derivative(adj, signals)
    assert result == [-1.0, -1.0, 2.0]
