"""Mine associations from an acquired headerless retail basket CSV.

The dataset is deliberately not bundled. No downloads occur during execution.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
from functools import lru_cache
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder


def load_baskets(path: str | Path) -> list[frozenset[str]]:
    """Read one basket per row; blanks and repeated items are not purchases."""
    baskets = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            items = frozenset(item.strip().lower() for item in row if item.strip())
            if items:
                baskets.append(items)
    if not baskets:
        raise ValueError("No nonempty transactions found in the CSV.")
    return baskets


def encode_baskets(baskets: list[frozenset[str]]) -> pd.DataFrame:
    if not baskets:
        raise ValueError("At least one transaction is required.")
    encoder = TransactionEncoder()
    values = encoder.fit(baskets).transform(baskets)
    return pd.DataFrame(values, columns=encoder.columns_, dtype=bool)


def mine_rules(encoded: pd.DataFrame, min_support: float = .003):
    if not 0 < min_support <= 1:
        raise ValueError("min_support must be in (0, 1].")
    if encoded.empty:
        raise ValueError("The encoded transaction matrix is empty.")
    itemsets = apriori(encoded, min_support=min_support, use_colnames=True)
    if itemsets.empty or not any(itemsets["itemsets"].map(len) > 1):
        empty = pd.DataFrame(columns=["antecedents", "consequents", "support",
                                      "confidence", "lift"])
        return itemsets, empty
    # A zero confidence threshold retains positive and negative associations.
    rules = association_rules(itemsets, metric="confidence", min_threshold=0)
    return itemsets, rules


def direct_metrics(baskets, antecedent, consequent) -> dict[str, float]:
    """Independent count-based oracle used to verify library rule metrics."""
    a, b = frozenset(antecedent), frozenset(consequent)
    if not a or not b or a & b or not baskets:
        raise ValueError("Use nonempty disjoint itemsets and transactions.")
    n = len(baskets)
    support_a = sum(a <= basket for basket in baskets) / n
    support_b = sum(b <= basket for basket in baskets) / n
    support_ab = sum((a | b) <= basket for basket in baskets) / n
    if not support_a or not support_b:
        raise ValueError("Both itemsets must occur in the transactions.")
    confidence = support_ab / support_a
    return {"support": support_ab, "confidence": confidence,
            "lift": confidence / support_b,
            "antecedent_support": support_a, "consequent_support": support_b}


def verify_rules(baskets, rules: pd.DataFrame) -> float:
    """Check every rule against empirical basket counts, without trusting prose."""
    postings = {}
    for index, basket in enumerate(baskets):
        for item in basket:
            postings.setdefault(item, set()).add(index)

    @lru_cache(maxsize=None)
    def support(items):
        matches = [postings.get(item, set()) for item in items]
        matches.sort(key=len)
        return len(set.intersection(*matches)) / len(baskets)

    max_error = 0.0
    for rule in rules.itertuples():
        a, b = rule.antecedents, rule.consequents
        joint = support(a | b)
        confidence = joint / support(a)
        expected = {"support": joint, "confidence": confidence,
                    "lift": confidence / support(b)}
        for key in ("support", "confidence", "lift"):
            error = abs(float(getattr(rule, key)) - expected[key])
            max_error = max(max_error, error)
            if not np.isclose(getattr(rule, key), expected[key], atol=1e-10):
                raise AssertionError(f"Rule {key} does not match basket counts.")
    return max_error


def build_network(rules: pd.DataFrame, min_confidence: float = .20) -> nx.DiGraph:
    """One-item directed rules with positive lift; edges are not causal effects."""
    graph = nx.DiGraph()
    for rule in rules.itertuples():
        if (len(rule.antecedents) == len(rule.consequents) == 1
                and rule.confidence >= min_confidence and rule.lift >= 1):
            graph.add_edge(next(iter(rule.antecedents)), next(iter(rule.consequents)),
                           support=float(rule.support), confidence=float(rule.confidence),
                           lift=float(rule.lift))
    return graph


def rule_record(rule) -> dict:
    return {"antecedent": sorted(rule.antecedents), "consequent": sorted(rule.consequents),
            "support": float(rule.support), "confidence": float(rule.confidence),
            "lift": float(rule.lift)}


def plot_results(encoded: pd.DataFrame, graph: nx.DiGraph, out: Path) -> None:
    frequencies = encoded.mean().sort_values(ascending=False).head(12).sort_values()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    frequencies.plot.barh(ax=ax, color="#25636c")
    ax.set(xlabel="Share of baskets containing item", ylabel="", title="Most frequent items")
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout(); fig.savefig(out / "item_support.png", dpi=150); plt.close(fig)
    if graph.number_of_edges():
        centrality = nx.degree_centrality(graph)
        pos = nx.spring_layout(graph, seed=42, iterations=100)
        hubs = sorted(centrality, key=centrality.get, reverse=True)[:12]
        labels = {node: str(i + 1) for i, node in enumerate(hubs)}
        fig, (ax, ranking) = plt.subplots(1, 2, figsize=(13, 6.5),
                                        gridspec_kw={"width_ratios": [1.4, 1]})
        nx.draw_networkx_nodes(graph, pos, ax=ax,
                               node_size=[80 + 900 * centrality[n] for n in graph],
                               node_color="#25636c", alpha=.8)
        nx.draw_networkx_edges(graph, pos, ax=ax, alpha=.16, arrows=True,
                               width=[1 + graph.edges[e]["confidence"] for e in graph.edges])
        nx.draw_networkx_labels(graph, pos, labels=labels, ax=ax, font_size=8, font_color="white")
        ax.set_title(f"Full network: {len(graph)} items, {graph.number_of_edges()} directed rules")
        ax.axis("off")
        ranking.barh(range(len(hubs)), [centrality[node] for node in hubs], color="#25636c")
        ranking.set_yticks(range(len(hubs)), [f"{i+1}. {node}" for i, node in enumerate(hubs)])
        ranking.invert_yaxis()
        ranking.set(title="Highest total degree", xlabel="(in-degree + out-degree) / (items − 1)")
        ranking.grid(axis="x", alpha=.2)
        fig.suptitle("Association network: one-item rules, confidence ≥20%, lift ≥1")
        fig.tight_layout()
        fig.savefig(out / "association_network.png", dpi=150); plt.close(fig)


def run(data: str | Path, output: str | Path = "results") -> dict:
    data, output = Path(data), Path(output)
    baskets = load_baskets(data)
    encoded = encode_baskets(baskets)
    initial_itemsets, initial_rules = mine_rules(encoded, .003)
    extended_itemsets, extended_rules = mine_rules(encoded, .001)
    positive = initial_rules[initial_rules["lift"] >= 1]
    negative = extended_rules[extended_rules["lift"] < 1]
    graph = build_network(positive)
    # Count verification covers every initial/extended rule; small data makes this practical.
    error = max(verify_rules(baskets, initial_rules), verify_rules(baskets, extended_rules))
    output.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_kind": "Corrected publication pipeline; newly recomputed from local acquired data",
        "input_sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
        "transactions": len(baskets), "unique_items": len(encoded.columns),
        "initial_min_support": .003, "initial_itemsets": len(initial_itemsets),
        "initial_positive_rules_lift_ge_1": len(positive),
        "extended_min_support": .001, "extended_itemsets": len(extended_itemsets),
        "extended_rules": len(extended_rules), "extended_negative_rules_lift_lt_1": len(negative),
        "network_nodes": graph.number_of_nodes(), "network_edges": graph.number_of_edges(),
        "max_absolute_metric_check_error": error,
        "strong_negative_example": None if negative.empty else rule_record(
            next(negative.sort_values("lift").itertuples())),
        "versions": {name: importlib.metadata.version(name) for name in
                     ["numpy", "pandas", "mlxtend", "networkx", "matplotlib"]},
        "interpretation": "Lift below 1 means less co-occurrence than independence predicts."
                          " Associations and network centrality do not establish causation or sales uplift.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    plot_results(encoded, graph, output)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/local/Market_Basket_Optimisation.csv"))
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    if not args.data.is_file():
        parser.error("Dataset missing. Follow data/README.md; no data is downloaded automatically.")
    print(json.dumps(run(args.data, args.output), indent=2))


if __name__ == "__main__":
    main()
