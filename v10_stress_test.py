import random
import json
import math

class CortexV10StressTest:
    def __init__(self, num_worlds=500, num_params=6):
        self.num_worlds = num_worlds
        self.num_params = num_params
        self.worlds = []
        self.observations = {}
        self.boundary_score = 0.0
        
    def initialize_worlds(self):
        """Genera mundos posibles con parámetros aleatorios"""
        self.worlds = [
            {
                "id": i,
                "params": [random.random() for _ in range(self.num_params)],
                "active": True
            }
            for i in range(self.num_worlds)
        ]
        print(f"✅ {len(self.worlds)} mundos inicializados")
        
    def adversarial_mask(self, intensity):
        """Simula ataque adversarial enmascarando parámetros"""
        masked_count = 0
        for world in self.worlds:
            for i in range(len(world["params"])):
                if random.random() < intensity:
                    world["params"][i] = None  # Enmascarado
                    masked_count += 1
        return masked_count
    
    def compute_observational_equivalence(self):
        """Calcula clases de equivalencia bajo observación parcial"""
        obs_map = {}
        for world in self.worlds:
            # Crear firma observable (solo params no enmascarados)
            signature = tuple(
                round(p, 2) if p is not None else "?" 
                for p in world["params"]
            )
            if signature not in obs_map:
                obs_map[signature] = []
            obs_map[signature].append(world["id"])
        
        # Calcular pares indistinguibles
        indistinguishable_pairs = 0
        for sig, world_ids in obs_map.items():
            n = len(world_ids)
            if n > 1:
                indistinguishable_pairs += n * (n - 1) // 2
                
        total_possible_pairs = len(self.worlds) * (len(self.worlds) - 1) // 2
        self.boundary_score = indistinguishable_pairs / max(total_possible_pairs, 1)
        return len(obs_map), indistinguishable_pairs
    
    def detect_partitions(self):
        """Detecta si el grafo de conocimiento se ha fragmentado"""
        # Simplificación: si hay demasiadas clases de equivalencia aisladas
        obs_map = {}
        for world in self.worlds:
            signature = tuple(
                str(p) for p in world["params"]
            )
            obs_map[signature] = True
        return len(obs_map) < self.num_worlds * 0.1  # Fragmentación crítica
    
    def run_simulation(self, steps=10):
        results = []
        print("\n🧪 INICIANDO PRUEBA DE ESTRÉS V10...\n")
        print(f"{'Paso':<6} {'Ruido':<8} {'Enmascarados':<12} {'Clases Obs':<12} {'Boundary':<10} {'Estable':<8}")
        print("-" * 70)
        
        for step in range(steps):
            noise_intensity = 0.4 + (step * 0.05)  # De 40% a 85%
            masked = self.adversarial_mask(noise_intensity)
            classes, pairs = self.compute_observational_equivalence()
            partitioned = self.detect_partitions()
            
            results.append({
                "step": step,
                "noise": round(noise_intensity, 2),
                "masked_params": masked,
                "observable_classes": classes,
                "boundary_score": round(self.boundary_score, 4),
                "stable": not partitioned
            })
            
            print(f"{step:<6} {noise_intensity:<8.2f} {masked:<12} {classes:<12} {self.boundary_score:<10.4f} {not partitioned}")
            
        return results

# Ejecutar prueba
if __name__ == "__main__":
    test = CortexV10StressTest(num_worlds=500, num_params=6)
    test.initialize_worlds()
    results = test.run_simulation(steps=10)
    
    # Guardar resultados
    with open("/workspace/v10_stress_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n📊 RESULTADOS FINALES:")
    final = results[-1]
    print(f"   Boundary Score Final: {final['boundary_score']}")
    print(f"   Clases Observables: {final['observable_classes']}")
    print(f"   Sistema Estable: {final['stable']}")
    print(f"\n💾 Resultados guardados en /workspace/v10_stress_results.json")
