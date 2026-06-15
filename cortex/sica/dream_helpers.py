# [C5-REAL] Exergy-Maximized
"""SICA Dream Engine Pattern Discovery Helpers."""

from __future__ import annotations

from collections import Counter, defaultdict

from cortex.sica.dream_types import DreamInsight, _TraceFragment
from cortex.sica.object_level import ExecutionTrace, StepOutcome
from cortex.sica.strategy import Heuristic


def discover_tool_specializations(
    traces: list[ExecutionTrace],
) -> list[DreamInsight]:
    """Discover which tools work best for which task types."""
    task_tool_success = group_tool_outcomes(traces)
    insights: list[DreamInsight] = []
    for task_type, tool_data in task_tool_success.items():
        if len(tool_data) < 2:
            continue
        insight = evaluate_tool_specialization(task_type, tool_data)
        if insight:
            insights.append(insight)
    return insights


def group_tool_outcomes(traces: list[ExecutionTrace]) -> dict[str, dict[str, list[bool]]]:
    task_tool_success: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for trace in traces:
        task_type = (trace.objective or "").split()[0].lower() if trace.objective else "unknown"
        for step in trace.steps:
            if step.tool_used:
                task_tool_success[task_type][step.tool_used].append(
                    step.outcome == StepOutcome.SUCCESS
                )
    return task_tool_success


def evaluate_tool_specialization(
    task_type: str, tool_data: dict[str, list[bool]]
) -> DreamInsight | None:
    tool_rates = {}
    for tool, outcomes in tool_data.items():
        if len(outcomes) >= 3:
            tool_rates[tool] = sum(outcomes) / len(outcomes)

    if len(tool_rates) >= 2:
        best = max(tool_rates, key=tool_rates.get)  # type: ignore[arg-type]
        worst = min(tool_rates, key=tool_rates.get)  # type: ignore[arg-type]

        if tool_rates[best] - tool_rates[worst] > 0.3:
            return DreamInsight(
                insight_type="specialization",
                description=(
                    f"For '{task_type}' tasks, '{best}' succeeds "
                    f"{tool_rates[best]:.0%} vs '{worst}' at "
                    f"{tool_rates[worst]:.0%}. Prefer '{best}'."
                ),
                confidence=min(0.9, 0.5 + len(tool_data[best]) * 0.05),
                evidence_count=len(tool_data[best]),
                proposed_heuristic=Heuristic(
                    name=f"prefer_{best}_for_{task_type}",
                    description=f"Use {best} for {task_type} tasks (dream-discovered)",
                    weight=0.6,
                ),
            )
    return None


def discover_failure_precursors(
    traces: list[ExecutionTrace],
) -> list[DreamInsight]:
    """Discover action patterns that precede failures."""
    insights: list[DreamInsight] = []
    precursor_counts: Counter[str] = Counter()

    for trace in traces:
        if trace.final_outcome != StepOutcome.FAILURE:
            continue
        for i, step in enumerate(trace.steps):
            if step.outcome == StepOutcome.FAILURE and i > 0:
                prev = trace.steps[i - 1]
                key = f"{prev.action}→{step.action}"
                precursor_counts[key] += 1
                break

    for pattern, count in precursor_counts.most_common(3):
        if count >= 3:
            insights.append(
                DreamInsight(
                    insight_type="anti_pattern",
                    description=f"Sequence '{pattern}' preceded failure {count} times.",
                    confidence=min(0.85, 0.4 + count * 0.1),
                    evidence_count=count,
                )
            )

    return insights


def discover_optimal_sequences(
    success_fragments: list[_TraceFragment],
) -> list[DreamInsight]:
    """Discover step sequences that correlate with success."""
    insights: list[DreamInsight] = []
    sequence_counts: Counter[str] = Counter()

    for frag in success_fragments:
        if len(frag.steps) >= 2:
            seq = "→".join(s.action for s in frag.steps[:3])
            sequence_counts[seq] += 1

    for seq, count in sequence_counts.most_common(3):
        if count >= 3:
            insights.append(
                DreamInsight(
                    insight_type="combo",
                    description=f"Sequence '{seq}' appeared in {count} successes.",
                    confidence=min(0.8, 0.3 + count * 0.1),
                    evidence_count=count,
                )
            )

    return insights


def discover_temporal_patterns(
    traces: list[ExecutionTrace],
) -> list[DreamInsight]:
    """Discover time-based patterns (e.g., tools that degrade over time)."""
    if len(traces) < 10:
        return []

    mid = len(traces) // 2
    old_traces = traces[:mid]
    new_traces = traces[mid:]

    old_success = sum(1 for t in old_traces if t.final_outcome == StepOutcome.SUCCESS) / len(
        old_traces
    )
    new_success = sum(1 for t in new_traces if t.final_outcome == StepOutcome.SUCCESS) / len(
        new_traces
    )

    insights: list[DreamInsight] = []
    if old_success - new_success > 0.2:
        insights.append(
            DreamInsight(
                insight_type="abstraction",
                description=(
                    f"Performance declining: old success rate {old_success:.0%} "
                    f"→ recent {new_success:.0%}. Strategy may be staling."
                ),
                confidence=0.7,
                evidence_count=len(traces),
            )
        )
    elif new_success - old_success > 0.2:
        insights.append(
            DreamInsight(
                insight_type="abstraction",
                description=(
                    f"Performance improving: old {old_success:.0%} "
                    f"→ recent {new_success:.0%}. Current strategy is working."
                ),
                confidence=0.7,
                evidence_count=len(traces),
            )
        )

    return insights
