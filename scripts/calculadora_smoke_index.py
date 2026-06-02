import networkx as nx
import requests
import json
import time
from pathlib import Path

# ==========================================
# CORTEX PERSIST: SMOKE INDEX CALCULATOR
# Reality Level: C5-REAL
# ==========================================

INPUT_GRAPH = Path("data/reputation_graph/mafia_ai_graph.graphml")
OUTPUT_CSV = Path("data/reputation_graph/smoke_index_report.csv")

class SmokeIndexCalculator:
    def __init__(self):
        self.G = nx.read_graphml(INPUT_GRAPH)
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CortexPersist-SmokeIndex/1.0"
        }
        
    def fetch_github_metrics(self, username: str) -> int:
        """
        Proxy metric for real empirical output: Public Repos / Contributions.
        We do a simple user search to fetch public repos as a baseline for C5-REAL output.
        """
        url = f"https://api.github.com/users/{username}"
        try:
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("public_repos", 0)
            elif resp.status_code == 404:
                # User not found on GitHub with that exact substack handle
                return 0
            elif resp.status_code == 403:
                # Rate limit
                print("[!] GitHub API Rate Limit Hit.")
                return 0
        except Exception as e:
            return 0
        return 0

    def calculate(self):
        print(f"[*] Calculating Smoke Index for {self.G.number_of_nodes()} nodes...")
        
        # Calculate Centrality (Social Legitimacy = Proxy for Narrative Output)
        try:
            centrality = nx.eigenvector_centrality(self.G, max_iter=1000, weight='weight')
        except:
            centrality = nx.degree_centrality(self.G)
            
        results = []
        for node in self.G.nodes():
            soc_legitimacy = centrality.get(node, 0.0)
            
            # Fetch Real Output
            real_output = self.fetch_github_metrics(node)
            time.sleep(0.6) # Avoid aggressive rate limiting
            
            # Formula: Centrality / (Real Output + 1)
            # High Centrality + Low Output = High Smoke
            # High Centrality + High Output = Balanced (Legitimacy backed by Reality)
            
            # Normalize centrality to make numbers readable (0-100 scale)
            norm_centrality = soc_legitimacy * 100
            
            smoke_index = norm_centrality / (real_output + 1)
            
            results.append({
                "Node": node,
                "Social_Legitimacy": round(norm_centrality, 4),
                "Real_Output_Repos": real_output,
                "Smoke_Index": round(smoke_index, 4)
            })
            
        # Sort by Smoke Index descending
        results.sort(key=lambda x: x["Smoke_Index"], reverse=True)
        
        print("\n--- TOP 10 ÍNDICE DE HUMO (MAFIA AI) ---")
        print(f"{'Nodo':<30} | {'Legitimidad Social':<20} | {'Output Real (Repos)':<20} | {'Smoke Index':<15}")
        print("-" * 95)
        for r in results[:10]:
            print(f"{r['Node']:<30} | {r['Social_Legitimacy']:<20} | {r['Real_Output_Repos']:<20} | {r['Smoke_Index']:<15}")
            
        # Export
        import csv
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Node", "Social_Legitimacy", "Real_Output_Repos", "Smoke_Index"])
            writer.writeheader()
            writer.writerows(results)
            
        print(f"\n[*] Report exported to {OUTPUT_CSV}")

if __name__ == "__main__":
    if not INPUT_GRAPH.exists():
        print("[!] Graph file not found. Run extractor first.")
        exit(1)
        
    calc = SmokeIndexCalculator()
    calc.calculate()
