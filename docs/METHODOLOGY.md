# Method and corrections

This refactor retains the original notebook's questions: frequent retail items,
association strength, negative associations and item-network structure. It uses
the same locally acquired transaction file for validation, without republishing it.

For itemsets A and B, support is the fraction containing A∪B; confidence is
support(A∪B)/support(A); lift is confidence/support(B). A lift below 1 indicates
less co-occurrence than expected under independence. High confidence alone can
reflect an already common consequent. Neither lift nor centrality proves causation.

Initial Apriori support is .003; positive rules have lift ≥1. The extended analysis
uses .001 support and retains rules of every confidence to inspect lift <1.
The directed network contains only single-item antecedents/consequents with
confidence ≥.20 and lift ≥1. These match the original main network filters.

Every mined rule is independently checked against direct transaction counts. The
receipt records maximum numerical disagreement. At .001 support, rare rules may
be based on only a handful of baskets: a large lift can be unstable. This is
descriptive exploration, without holdout recommendation evaluation or measured
retail outcomes.

Corrected issues from the course notebook:

- The phrase treating lift .9864 as above 1 was incorrect; no such claim remains.
- Consequent support comes from its empirical frequency, not a mismatched printed
  scalar from another calculation.
- CSV parsing preserves the first transaction, strips blank padding and treats
  repeated items as one presence in a basket.
- Logic lives in reusable functions; independent metric and negative-association
  checks cover the previously misleading interpretation.

The historical notebook retained 1,443 initial itemsets, 4,880 positive rules and
an 80-node/281-edge network. These are historical reference counts, not a claim that
the corrected publication run necessarily reproduces all of them. The current
`results/summary.json` explicitly identifies its own run and file hash.
