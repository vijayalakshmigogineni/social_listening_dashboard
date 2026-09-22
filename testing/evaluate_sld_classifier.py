"""
Evaluate the SLD classifier against a manually labeled sample.

Usage:
    python evaluate_sld_classifier.py

Reads:
    labeling_template.csv  (must have the gold_* columns filled in by hand
    -- see sample_for_labeling.py)

Prints:
    accuracy / precision / recall / F1 for sld_candidate (binary)
    a full classification report + confusion matrix for content_type
    a full classification report + confusion matrix for intent_level
"""

import sys

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INPUT_PATH = "labeling_template.csv"


def normalize_bool(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "1": True, "yes": True,
              "false": False, "0": False, "no": False, "": False})
        .fillna(False)
    )


def main():
    df = pd.read_csv(INPUT_PATH)
    df = df[df["gold_content_type"].notna() & (df["gold_content_type"] != "")]

    if df.empty:
        raise SystemExit(
            f"No labeled rows found -- fill in the gold_* columns in "
            f"{INPUT_PATH} first (see sample_for_labeling.py)."
        )

    print(f"Evaluating on {len(df)} manually labeled posts\n")

    # ---- SLD candidate (binary) -----------------------------------------
    y_true = normalize_bool(df["gold_sld_candidate"])
    y_pred = normalize_bool(df["sld_candidate"])

    print("=" * 70)
    print("SLD CANDIDATE (binary: should this show on the dashboard?)")
    print("=" * 70)
    print(f"Accuracy : {accuracy_score(y_true, y_pred):.3f}")
    print(f"Precision: {precision_score(y_true, y_pred, zero_division=0):.3f}")
    print(f"Recall   : {recall_score(y_true, y_pred, zero_division=0):.3f}")
    print(f"F1       : {f1_score(y_true, y_pred, zero_division=0):.3f}")
    print("\nConfusion matrix (rows=true, cols=pred, order=[False, True]):")
    print(confusion_matrix(y_true, y_pred, labels=[False, True]))

    # ---- content type (multi-class) --------------------------------------
    print("\n" + "=" * 70)
    print("CONTENT TYPE (multi-class)")
    print("=" * 70)
    print(classification_report(
        df["gold_content_type"], df["content_type"], zero_division=0
    ))

    # ---- intent level (multi-class incl. null) ------------------------------
    gold_intent = df["gold_intent_level"].fillna("NONE").replace("", "NONE")
    pred_intent = df["intent_level"].fillna("NONE").replace("", "NONE")

    print("\n" + "=" * 70)
    print("INTENT LEVEL (multi-class; NONE = non-operational / null)")
    print("=" * 70)
    print(classification_report(gold_intent, pred_intent, zero_division=0))

    labels = sorted(set(gold_intent) | set(pred_intent))
    print("Confusion matrix labels:", labels)
    print(confusion_matrix(gold_intent, pred_intent, labels=labels))


if __name__ == "__main__":
    main()
