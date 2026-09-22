import pandas as pd
from transformers import pipeline

# -----------------------------------
# 1. Load your Reddit dataset
# -----------------------------------

df = pd.read_json(r"C:\Users\HEMA LATHA\social-listening\testing\reddit\reddit_rcm_candidates.json")

# Change this if your text column has another name
TEXT_COLUMN = "content"

# -----------------------------------
# 2. Load Zero-Shot NLI model
# -----------------------------------

classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli"
)

# -----------------------------------
# 3. Intent labels
# -----------------------------------

candidate_labels = [
    "the author is describing a problem they are experiencing",
    "the author is asking for information",
    "the author is looking for a solution to a problem",
    "the author is looking for a vendor or service provider",
    "the post does not express a specific request or problem-solving intent"
]

label_mapping = {
    "the author is describing a problem they are experiencing": "L0",
    "the author is asking for information": "L1",
    "the author is looking for a solution to a problem": "L2",
    "the author is looking for a vendor or service provider": "L3",
    "the post does not express a specific request or problem-solving intent": "NONE"
}

# -----------------------------------
# 4. Run NLI
# -----------------------------------

results = []

for index, row in df.iterrows():

    title = str(row.get("title") or "")
    body = str(row.get(TEXT_COLUMN) or "")
    text = (title + "\n" + body).strip()

    if not text:
        continue

    result = classifier(
        text,
        candidate_labels,
        multi_label=False
    )

    labels = result["labels"]
    scores = result["scores"]

    top_label = labels[0]
    top_score = scores[0]

    second_score = scores[1]

    margin = top_score - second_score

    prediction = label_mapping[top_label]

    if margin < 0.10:
        ambiguity = "AMBIGUOUS"
    else:
        ambiguity = "CLEAR"

    results.append({
        "source_item_id": row.get("source_item_id", index),
        "text": text,
        "nli_prediction": prediction,

        "l0_score": scores[
            labels.index(
                "the author is describing a problem they are experiencing"
            )
        ],

        "l1_score": scores[
            labels.index(
                "the author is asking for information"
            )
        ],

        "l2_score": scores[
            labels.index(
                "the author is looking for a solution to a problem"
            )
        ],

        "l3_score": scores[
            labels.index(
                "the author is looking for a vendor or service provider"
            )
        ],

        "none_score": scores[
            labels.index(
                "the post does not express a specific request or problem-solving intent"
            )
        ],

        "top_score": top_score,
        "second_score": second_score,
        "margin": margin,
        "ambiguity": ambiguity
    })

# -----------------------------------
# 5. Save results
# -----------------------------------

results_df = pd.DataFrame(results)

results_df.to_csv(
    "reddit_nli_results.csv",
    index=False
)

print("\nDONE")
print("Results saved to reddit_nli_results.csv")

print("\nPrediction counts:")
print(results_df["nli_prediction"].value_counts())