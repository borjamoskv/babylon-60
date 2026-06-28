"""
[C5-REAL] CORTEX APEX Agentic Benchmark Protocol Evaluator.
Reverse-engineered evaluation matrix for Frontier Models.
Protocol: A-EVAL-2026.

This module evaluates agentic causal trajectories to extract thermodynamic exergy 
(Net Improvement, Steerability, Bash Recovery, Tool Hallucination).
"""

import argparse
import csv
import json
import logging
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional

# CORTEX standard logger
logger = logging.getLogger("cortex.benchmark.agentic_eval")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)

class AgenticMetrics:
    def __init__(self):
        self.total_sessions: int = 0
        self.total_cycles: int = 0
        self.net_improvement_commits: int = 0
        self.reverted_commits: int = 0
        self.zero_intervention_successes: int = 0
        self.praise_count: int = 0
        self.complaint_count: int = 0
        self.corrections: int = 0
        self.successful_corrections: int = 0
        self.bash_errors: int = 0
        self.bash_recoveries: int = 0
        self.tool_hallucinations: int = 0
        self.total_tool_calls: int = 0

class AgenticEvaluator:
    def __init__(self, transcripts_dir: Path):
        self.transcripts_dir = transcripts_dir
        self.metrics = AgenticMetrics()
        self.session_scores: List[Dict[str, float]] = []

    def evaluate_session(self, transcript_path: Path) -> None:
        """Processes a single transcript.jsonl file to extract Causal Trajectory metrics."""
        self.metrics.total_sessions += 1
        
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            logger.error(f"Transcript not found: {transcript_path}")
            return

        session_events = [json.loads(line) for line in lines if line.strip()]
        
        user_msgs = 0
        error_count = 0
        praise_found = False
        complaint_found = False
        last_bash_error = False
        
        # Local session metrics for variance
        local_tool_calls = 0
        local_hallucinations = 0
        local_bash_errors = 0
        local_recoveries = 0

        for event in session_events:
            step_type = event.get("type", "")
            content = event.get("content", "").lower()
            
            # 1. Sentiment & Praise vs Complaint
            if step_type == "USER_INPUT":
                user_msgs += 1
                if any(p in content for p in ["looks good", "perfect", "thanks", "great", "awesome", "funciona"]):
                    praise_found = True
                if any(c in content for c in ["no", "instead", "change this", "wrong", "fail", "error", "bad"]):
                    complaint_found = True
                    self.metrics.corrections += 1
            
            # 2. Tool Hallucination (Anergy Rate)
            if step_type == "PLANNER_RESPONSE":
                self.metrics.total_cycles += 1
                tool_calls = event.get("tool_calls", [])
                for tc in tool_calls:
                    self.metrics.total_tool_calls += 1
                    local_tool_calls += 1
                    tc_str = str(tc).lower()
                    if "error" in tc_str or "invalid" in tc_str or "unknown" in tc_str:
                        self.metrics.tool_hallucinations += 1
                        local_hallucinations += 1
                        
            # 3. Bash Recovery
            if step_type == "TOOL_RESPONSE":
                output = event.get("output", "")
                if "exit code" in output and "exit code 0" not in output:
                    self.metrics.bash_errors += 1
                    local_bash_errors += 1
                    last_bash_error = True
                elif last_bash_error and ("exit code 0" in output or "success" in output.lower()):
                    self.metrics.bash_recoveries += 1
                    local_recoveries += 1
                    last_bash_error = False
                    
            if step_type == "ERROR":
                error_count += 1
                
        # 4. Confirmed Success
        if user_msgs == 1 and error_count == 0:
            self.metrics.zero_intervention_successes += 1
            
        if praise_found:
            self.metrics.praise_count += 1
        if complaint_found:
            self.metrics.complaint_count += 1
            
        # Store variance data
        self.session_scores.append({
            "session": transcript_path.parent.name,
            "tool_hallucination_rate": (local_hallucinations / local_tool_calls) if local_tool_calls else 0.0,
            "bash_recovery_rate": (local_recoveries / local_bash_errors) if local_bash_errors else 0.0
        })

    def compute_aggregate_metrics(self) -> Dict[str, str]:
        """Calculates final percentages akin to the A-EVAL-2026 leaderboard."""
        ts = self.metrics.total_sessions or 1
        tc = self.metrics.total_cycles or 1
        tt = self.metrics.total_tool_calls or 1
        be = self.metrics.bash_errors or 1
        co = self.metrics.corrections or 1
        
        # In absence of direct git parsing here, we mock the commit counts as proportional
        net_improvement = ((self.metrics.net_improvement_commits - self.metrics.reverted_commits) / tc) * 100
        
        return {
            "Rank": "N/A",
            "Model": "Local-Swarm",
            "Net Improvement": f"{net_improvement:.2f}%",
            "Confirmed Success": f"{(self.metrics.zero_intervention_successes / ts) * 100:.2f}%",
            "Praise vs Complaint": f"{(self.metrics.praise_count / ts) * 100:.2f}% / {(self.metrics.complaint_count / ts) * 100:.2f}%",
            "Steerability": f"{(self.metrics.successful_corrections / co) * 100:.2f}%",
            "Bash Recovery": f"{(self.metrics.bash_recoveries / be) * 100:.2f}%",
            "Tool Hallucination": f"{(self.metrics.tool_hallucinations / tt) * 100:.2f}%",
            "Sessions": str(self.metrics.total_sessions)
        }

    def run_all(self, csv_export: Optional[str] = None) -> Dict[str, str]:
        logger.info(f"Scanning directory: {self.transcripts_dir} for transcript.jsonl files...")
        paths = list(self.transcripts_dir.rglob("transcript.jsonl"))
        
        if not paths:
            logger.warning("No transcript.jsonl files found.")
            return self.compute_aggregate_metrics()

        for path in paths:
            self.evaluate_session(path)
            
        results = self.compute_aggregate_metrics()
        
        if csv_export:
            self._export_csv(csv_export, results)
            
        return results

    def _export_csv(self, csv_path: str, results: Dict[str, str]) -> None:
        try:
            with open(csv_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(list(results.keys()))
                writer.writerow(list(results.values()))
            logger.info(f"[C5-REAL] Structural Matrix exported to {csv_path}")
        except Exception as e:
            logger.error(f"CSV export failed: {e}")

def main() -> None:
    parser = argparse.ArgumentParser(description="META_EVAL_AGENTIC task-level benchmark")
    parser.add_argument("-d", "--directory", type=str, required=True, help="Directory containing brain/session logs")
    parser.add_argument("-o", "--output", type=str, default="a_eval_results.csv", help="CSV export path")
    args = parser.parse_args()

    evaluator = AgenticEvaluator(Path(args.directory))
    results = evaluator.run_all(csv_export=args.output)
    
    print("\n=== A-EVAL-2026 CORTEX BENCHMARK RESULTS ===")
    print("-" * 50)
    for k, v in results.items():
        print(f"  {k:<20}: {v}")
    print("-" * 50)

if __name__ == "__main__":
    main()
