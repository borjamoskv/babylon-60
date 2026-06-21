import pytest
import torch
import math
import torch.nn.functional as F

# Tolerancia estricta de aserción paramétrica para suprimir el ruido de coma flotante
TOLERANCIA = 1e-4

@pytest.fixture
def base_tensor():
    return torch.tensor([2.0], requires_grad=True)

class TestAlgebraPrimitives:
    def test_variable_constante_ecuacion(self, base_tensor):
        c_const = torch.tensor([5.0], requires_grad=False)
        target = torch.tensor([14.0])
        optimizer = torch.optim.SGD([base_tensor], lr=0.01)
        
        for _ in range(50):
            optimizer.zero_grad()
            loss = ((base_tensor ** 2) + c_const - target) ** 2
            loss.backward()
            optimizer.step()
            
        torch.testing.assert_close(base_tensor, torch.tensor([3.0]), rtol=TOLERANCIA, atol=TOLERANCIA)

    def test_inecuacion_dominio_rango(self):
        space = torch.linspace(-5, 5, 100)
        ineq_mask = space > 0
        assert ineq_mask.sum().item() == 50
        
    def test_factorizacion_svd(self):
        A = torch.tensor([[2.0, 1.0], [1.0, 3.0]])
        U, S, V = torch.linalg.svd(A)
        # SVD singular values for A are ~ [3.6180, 1.3820]
        torch.testing.assert_close(S, torch.tensor([3.6180, 1.3820]), rtol=1e-3, atol=1e-3)

class TestGeometryCalculusPrimitives:
    def test_pitagoras_metrica(self):
        cateto_a = torch.tensor([3.0])
        cateto_b = torch.tensor([4.0])
        hipotenusa = torch.sqrt(cateto_a**2 + cateto_b**2)
        assert hipotenusa.item() == 5.0
        
    def test_derivada_cadena(self, base_tensor):
        h_x = torch.sin(base_tensor ** 2) 
        h_x.backward()
        expected = 2 * 2.0 * math.cos(4.0)
        torch.testing.assert_close(base_tensor.grad, torch.tensor([expected]), rtol=TOLERANCIA, atol=TOLERANCIA)

class TestStatisticsProbability:
    def test_momentos_bayes(self):
        data = torch.tensor([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        assert torch.mean(data).item() == 5.0
        assert torch.median(data).item() == 4.0
        
        # Bayes P(A|B)
        p_a = torch.tensor(0.01)
        p_b_given_a = torch.tensor(0.99)
        p_b = torch.tensor(0.05)
        p_a_given_b = (p_b_given_a * p_a) / p_b
        torch.testing.assert_close(p_a_given_b, torch.tensor(0.1980), rtol=1e-3, atol=1e-3)

    def test_regresion_lineal(self):
        x = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])
        y = torch.tensor([2.0, 4.0, 5.0, 4.0, 5.0])
        X_mat = torch.stack([x, torch.ones_like(x)], dim=1)
        coef = torch.linalg.lstsq(X_mat, y).solution
        torch.testing.assert_close(coef, torch.tensor([0.6000, 2.2000]), rtol=1e-3, atol=1e-3)

class TestAdvancedAIPrimitives:
    def test_logica_booleana_conjuntos(self):
        A = torch.tensor([True, False, True, False])
        B = torch.tensor([True, True, False, False])
        implicacion = (~A) | B
        assert torch.all(implicacion == torch.tensor([True, True, False, True]))
        
    def test_transformer_attention(self):
        Q = torch.randn(1, 4, 8)
        K = torch.randn(1, 4, 8)
        V_att = torch.randn(1, 4, 8)
        scores = torch.bmm(Q, K.transpose(1, 2)) / math.sqrt(8)
        attention_weights = F.softmax(scores, dim=-1)
        attention_output = torch.bmm(attention_weights, V_att)
        assert attention_output.shape == (1, 4, 8)
        # Sum of attention weights across the last dimension must be exactly 1
        torch.testing.assert_close(attention_weights.sum(dim=-1), torch.ones(1, 4), rtol=TOLERANCIA, atol=TOLERANCIA)
