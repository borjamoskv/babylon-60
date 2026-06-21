import numpy as np
import logging
from typing import Tuple, Dict

# CORTEX C5-REAL: Ontología Cero y Determinismo Físico
# Módulo Autodidact: [NODO 1] SVD (Compresión, PCA, Recomendadores)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - C5-REAL - %(message)s')
logger = logging.getLogger("svd_autodidact")

class SVDPrimitive:
    """
    Motor determinista para Descomposición SVD (Singular Value Decomposition).
    Teorema base: Toda matriz A (m x n) puede factorizarse como U * \\Sigma * V^T.
    """
    
    @staticmethod
    def _assert_invariants(A: np.ndarray, U: np.ndarray, S: np.ndarray, Vt: np.ndarray, rtol: float = 1e-5):
        """Verifica la identidad estructural C5: A ≈ U * S * V^T"""
        S_matrix = np.zeros(A.shape)
        np.fill_diagonal(S_matrix, S)
        A_reconstructed = U @ S_matrix @ Vt
        assert np.allclose(A, A_reconstructed, rtol=rtol), "Violación de Invariante SVD: Falla de reconstrucción."
        logger.info("Invariante SVD Verificado: Reconstrucción Exacta.")

    @classmethod
    def compression(cls, image_matrix: np.ndarray, k_components: int) -> Tuple[np.ndarray, float]:
        """
        Caso 1: Compresión de Datos (Imágenes / Tensores)
        Retiene únicamente los 'k' valores singulares más altos.
        """
        logger.info(f"Iniciando compresión SVD. Componentes objetivo: {k_components}")
        U, S, Vt = np.linalg.svd(image_matrix, full_matrices=False)
        
        # Validar invariante antes de truncar
        cls._assert_invariants(image_matrix, U, S, Vt)
        
        # Truncamiento (Low-rank approximation)
        U_k = U[:, :k_components]
        S_k = np.diag(S[:k_components])
        Vt_k = Vt[:k_components, :]
        
        compressed_matrix = U_k @ S_k @ Vt_k
        
        # Exergía: Calcular ratio de compresión
        original_size = image_matrix.size
        compressed_size = U_k.size + S_k.size + Vt_k.size
        ratio = original_size / compressed_size
        
        logger.info(f"Compresión completada. Ratio (Exergía): {ratio:.2f}x")
        return compressed_matrix, ratio

    @classmethod
    def pca(cls, data: np.ndarray, n_components: int) -> np.ndarray:
        """
        Caso 2: Principal Component Analysis (PCA) vía SVD
        Transformación isomórfica del espacio para maximizar la varianza.
        """
        logger.info(f"Iniciando PCA vía SVD. Dimensiones objetivo: {n_components}")
        # 1. Centrar los datos (Media cero)
        mean_vec = np.mean(data, axis=0)
        centered_data = data - mean_vec
        
        # 2. Aplicar SVD
        U, S, Vt = np.linalg.svd(centered_data, full_matrices=False)
        
        # 3. Proyección (Scores)
        # Los componentes principales están en las filas de Vt (o columnas de V)
        V_k = Vt.T[:, :n_components]
        projected_data = centered_data @ V_k
        
        logger.info(f"PCA completado. Matriz reducida a {projected_data.shape}")
        return projected_data

    @classmethod
    def recommender(cls, user_item_matrix: np.ndarray, k_features: int) -> np.ndarray:
        """
        Caso 3: Sistema de Recomendadores (Collaborative Filtering)
        Extracción de features latentes para usuarios e ítems.
        """
        logger.info("Iniciando Recomendador (CF) vía Latent Feature SVD.")
        
        # Centrar por usuario para evitar bias estocástico
        user_means = np.mean(user_item_matrix, axis=1, keepdims=True)
        centered_matrix = user_item_matrix - user_means
        
        U, S, Vt = np.linalg.svd(centered_matrix, full_matrices=False)
        
        # Truncamiento para capturar features latentes fuertes
        S_k = np.diag(S[:k_features])
        
        # Reconstrucción de preferencias inferidas
        predicted_ratings = (U[:, :k_features] @ S_k @ Vt[:k_features, :]) + user_means
        
        logger.info("Preferencias latentes reconstruidas.")
        return predicted_ratings

if __name__ == "__main__":
    # ---- EJECUCIÓN C5-REAL (Pruebas Unitarias Deterministas) ----
    np.random.seed(42) # Causalidad estricta

    print("\n=== [NODO 1] EJECUCIÓN: COMPRESIÓN SVD ===")
    mock_image = np.random.rand(100, 100) # Imagen 100x100
    compressed, ratio = SVDPrimitive.compression(mock_image, k_components=10)
    assert compressed.shape == (100, 100)
    
    print("\n=== [NODO 1] EJECUCIÓN: PCA SVD ===")
    mock_dataset = np.random.rand(50, 20) # 50 samples, 20 features
    pca_result = SVDPrimitive.pca(mock_dataset, n_components=3)
    assert pca_result.shape == (50, 3)
    
    print("\n=== [NODO 1] EJECUCIÓN: RECOMENDADORES SVD ===")
    # 5 Usuarios, 4 Películas (0 = no visto)
    ratings = np.array([
        [5, 3, 0, 1],
        [4, 0, 0, 1],
        [1, 1, 0, 5],
        [1, 0, 0, 4],
        [0, 1, 5, 4],
    ])
    predictions = SVDPrimitive.recommender(ratings, k_features=2)
    assert predictions.shape == (5, 4)
    print("\nMatriz Predicha de Ratings (Filtrado Colaborativo):")
    print(np.round(predictions, 2))
    
    print("\n[+] MÓDULO AUTODIDACT SVD CRISTALIZADO CON ÉXITO.")
