from cortex.engine.bounty_heuristics import BOUNTY_HUNTER_RULES, BountyAlphaScore

print("\n[CORTEX BOUNTY OPERATOR] - TARGET PROFILING INITIATED...\n")

# Target 1: A highly competitive, low TVL target (Solo Hunter trap)
trap_target = BountyAlphaScore(
    capital_at_risk=50_000,
    exploitability=0.8,
    novelty=0.2,
    bounty_clarity=0.5,
    competition_density=500,
)

# Target 2: High TVL, complex Web3 logic, low competition (Operator Target)
operator_target_web3 = BountyAlphaScore(
    capital_at_risk=10_000_000,
    exploitability=0.6,
    novelty=0.9,
    bounty_clarity=1.0,
    competition_density=10,
)

# Target 3: New Cloud Identity / AI agent logic (Operator Target)
operator_target_ai = BountyAlphaScore(
    capital_at_risk=50_000_000,  # Tenant isolation impact
    exploitability=0.4,
    novelty=1.0,
    bounty_clarity=0.8,
    competition_density=5,
)

print(f"TRAP TARGET SCORE (High Comp/Low TVL): {trap_target.score:,.2f}")
print(f"WEB3 OPERATOR TARGET SCORE: {operator_target_web3.score:,.2f}")
print(f"AI/CLOUD OPERATOR TARGET SCORE: {operator_target_ai.score:,.2f}\n")

print("Checking loaded Inference Rules...\n")
for rule in BOUNTY_HUNTER_RULES:
    if rule.name in [
        "cloud_tenant_isolation_breach",
        "ai_agent_state_poisoning",
        "cloud_oauth_sso_confusion",
    ]:
        print(f"[ACTIVE] New Lane Rule: {rule.name}")
        print(f"  Description: {rule.description}")
        print(f"  Condition: {rule.condition_sql}")
        print("-" * 60)

print("\n[STATUS: C5-REAL EXECUTION SUCCESSFUL]")
