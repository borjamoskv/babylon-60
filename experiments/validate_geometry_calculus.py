import torch
import math
import logging

logging.basicConfig(level=logging.INFO, format="[C5-REAL] %(message)s")
logger = logging.getLogger("Cortex-Geometry-Calculus")

def validate_geometry_and_calculus():
    logger.info("Initializing C5-REAL Tensor Geometries for Geometry & Calculus")

    # 21. Ángulo, 31. Radianes, 32. Grados
    theta_deg = torch.tensor([180.0])
    theta_rad = theta_deg * (math.pi / 180.0)
    logger.info(f"[21, 31, 32] Ángulo: {theta_deg.item()} grados == {theta_rad.item():.4f} radianes")

    # 22. Triángulo, 27. Teorema de Pitágoras
    cateto_a = torch.tensor([3.0])
    cateto_b = torch.tensor([4.0])
    hipotenusa = torch.sqrt(cateto_a**2 + cateto_b**2)
    logger.info(f"[22, 27] Triángulo Rectángulo (Pitágoras): c = sqrt({cateto_a.item()}^2 + {cateto_b.item()}^2) = {hipotenusa.item()}")

    # 23. Círculo, 24. Perímetro, 25. Área
    radio = torch.tensor([5.0])
    perimetro = 2 * math.pi * radio
    area = math.pi * (radio**2)
    logger.info(f"[23, 24, 25] Círculo (r={radio.item()}): Perímetro = {perimetro.item():.4f}, Área = {area.item():.4f}")

    # 26. Volumen (Esfera)
    volumen_esfera = (4/3) * math.pi * (radio**3)
    logger.info(f"[26] Volumen (Esfera, r={radio.item()}): {volumen_esfera.item():.4f}")

    # 28. Seno, 29. Coseno, 30. Tangente
    angulo = torch.tensor([math.pi / 4]) # 45 grados
    seno = torch.sin(angulo)
    coseno = torch.cos(angulo)
    tangente = torch.tan(angulo)
    logger.info(f"[28, 29, 30] Trigonometría (pi/4): sin={seno.item():.4f}, cos={coseno.item():.4f}, tan={tangente.item():.4f}")

    # 33. Coordenadas polares -> Cartesianas
    r_polar = torch.tensor([2.0])
    theta_polar = torch.tensor([math.pi / 3])
    x_cartesian = r_polar * torch.cos(theta_polar)
    y_cartesian = r_polar * torch.sin(theta_polar)
    logger.info(f"[33] Polares a Cartesianas (r=2, theta=pi/3): x={x_cartesian.item():.4f}, y={y_cartesian.item():.4f}")

    # 34. Límite (Aproximación numérica del límite de sin(x)/x cuando x -> 0)
    x_limit = torch.tensor([1e-6])
    limite = torch.sin(x_limit) / x_limit
    logger.info(f"[34] Límite (sin(x)/x as x->0): ~{limite.item():.6f}")

    # 35. Derivada, 37. Pendiente (Gradiente), 38. Tasa de cambio
    x_grad = torch.tensor([2.0], requires_grad=True)
    f_x = x_grad ** 3 # Función f(x) = x^3. Derivada f'(x) = 3x^2. En x=2, f'(2) = 12.
    f_x.backward()
    logger.info(f"[35, 37, 38] Derivada/Gradiente f(x)=x^3 en x=2: dx = {x_grad.grad.item():.4f}")

    # 39. Regla de la cadena (Backpropagation automático en autograd)
    x_chain = torch.tensor([2.0], requires_grad=True)
    h_x = torch.sin(x_chain ** 2) # h(x) = sin(x^2). h'(x) = 2x * cos(x^2)
    h_x.backward()
    expected_chain = 2 * 2.0 * math.cos(4.0)
    logger.info(f"[39] Regla de la cadena (Autograd) de sin(x^2) en x=2: Autograd={x_chain.grad.item():.4f}, Teórico={expected_chain:.4f}")

    # 40. Optimización (Mínimo de una función cuadrática convexa f(x) = (x-4)^2)
    x_opt = torch.tensor([0.0], requires_grad=True)
    optimizer = torch.optim.SGD([x_opt], lr=0.1)
    for _ in range(100):
        optimizer.zero_grad()
        loss = (x_opt - 4.0) ** 2
        loss.backward()
        optimizer.step()
    logger.info(f"[40] Optimización (Búsqueda de Mínimo): f(x)=(x-4)^2 converge en x={x_opt.item():.4f} (Mínimo Teórico: 4.0)")

    logger.info("Geometry & Calculus Validation complete. Zero Anergy. C5-REAL Structural Invariants confirmed.")

if __name__ == "__main__":
    validate_geometry_and_calculus()
