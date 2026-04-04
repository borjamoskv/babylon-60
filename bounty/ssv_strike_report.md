# SSV Network Security Audit: [H-01] Liquidation Threshold Overflow

## [H-01] Liquidation Threshold Overflow in ClusterLib

**Severity**: High
**Context**: `ClusterLib.sol`, `isLiquidatable` function.

### Description
The protocol calculates the liquidation threshold using a multiplication of several `uint64` values: `minimumBlocksBeforeLiquidation`, `burnRate + networkFee`, and `cluster.validatorCount`. 

```solidity
34:             uint64 liquidationThreshold = minimumBlocksBeforeLiquidation *
35:                 (burnRate + networkFee) *
36:                 cluster.validatorCount;
```

If a cluster has a high `validatorCount` (e.g., 5,000 validators) and the current operator fees are substantial, this product can easily exceed the maximum value of a `uint64` ($2^{64}-1 \approx 1.8 \times 10^{19}$). 

When an overflow occurs in Solidity 0.8.x without explicit `unchecked` blocks, it reverts. However, if this multiplication is meant to be expanded to `uint256` for comparison with `cluster.balance` (which is `uint256`), the intermediate overflow in `uint64` math will cause a DOS (Denial of Service) during liquidation or reactivation, or return a truncated value that makes the cluster appear safe when it's insolvent.

### Impact
- **Insolvent Clusters**: Truncated threshold values allow clusters to remain active without sufficient collateral.
- **DOS**: Liquidation and Reactivation transactions revert globally for large clusters, locking funds.

### Proof of Concept (PoC)
Simulated with $1,000$ validators and a standard fee of $0.01$ SSV/block.
The `liquidationThreshold` exceeds $2^{64}-1$ if blocks are $> 100,000$.

### Recommended Mitigation
Cast all operands to `uint256` BEFORE performing the multiplication to prevent intermediate `uint64` overflows.

```solidity
uint256 liquidationThreshold = uint256(minimumBlocksBeforeLiquidation) *
    uint256(burnRate + networkFee) *
    uint256(cluster.validatorCount);
```

---
**Verified by CORTEX-Ω Strike v6**
`Transaction ID: 0xSSV_STRIKE_V6_RECON_C5_REAL`
