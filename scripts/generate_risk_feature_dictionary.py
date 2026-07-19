"""Generate the complete Phase 3 Markdown feature dictionary from frozen metadata."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    config: object = json.loads(arguments.config.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("features"), list):
        raise ValueError("Risk feature configuration is invalid")
    inventory_rows: dict[str, dict[str, str]] = {}
    with arguments.inventory.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            inventory_rows[str(row["feature_name"])] = {str(key): str(value) for key, value in row.items()}
    lines: list[str] = [
        "# Risk Feature Dictionary",
        "",
        "These are transparent **public-data CAMELS-style risk indicators**, not official CAMELS ratings. Raw calculated values are preserved; nulls are not imputed; unsupported regulatory fields are excluded.",
        "",
        "| Feature | Category | Formula | Units | Direction | Availability / missingness | Peer | Limitation |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in config["features"]:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid feature item: {item!r}")
        name: str = str(item["feature_name"])
        observed: dict[str, str] = inventory_rows[name]
        formula: str = str(item["formula"]).replace("|", "/")
        limitation: str = str(item["known_limitation"]).replace("|", "/")
        direction: str = str(item["direction_of_risk"])
        availability: str = (
            f"{observed['first_available_quarter']}–{observed['last_available_quarter']}; "
            f"{float(observed['missing_percentage']):.3f}% missing"
        )
        peer: str = "Yes" if item["peer_group_requirement"] != "None" else "No"
        lines.append(
            f"| `{name}` | {item['financial_category']} | {formula} | {item['units']} | "
            f"{direction} | {availability} | {peer} | {limitation} |"
        )
    lines.extend([
        "",
        "## Explicitly unsupported candidates",
        "",
        "The following requested candidates were not built because their inputs were excluded from the approved Core-v1 contract: "
        + ", ".join(f"`{name}`" for name in config["unsupported_candidates"]) + ".",
        "",
        "The authoritative machine-readable metadata is `configs/risk_features.yaml`; empirical counts are in `reports/feature_inventory.csv`.",
    ])
    arguments.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {arguments.output} with {len(config['features'])} features")


if __name__ == "__main__":
    main()
