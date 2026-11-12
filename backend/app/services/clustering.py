
from collections import defaultdict

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from app.services.ollama_client import generate_response


SENTIMENTS = {"Bearish", "Bullish", "Neutral"}


def classify_sentiment(text: str) -> str:
    """Classify a financial text into the three project labels."""

    prompt = f"""
You are a financial sentiment classification system.

Classify the overall financial sentiment of the text.

Allowed labels:
- Bearish
- Bullish
- Neutral

Consider numerical context, recent events, comparisons,
causes, risks and uncertainty.

Return only one label. Do not add an explanation.

Text:
{text}
"""

    result = generate_response(prompt).strip().lower()

    if "bearish" in result:
        return "Bearish"
    if "bullish" in result:
        return "Bullish"
    if "neutral" in result:
        return "Neutral"

    return "Neutral"


def create_sentiment_clusters(documents: list) -> list:
    """
    Group texts by sentiment and apply K-Means
    within each sentiment group.
    """

    groups = defaultdict(list)

    for document in documents:
        text = document["text"]

        sentiment = document.get("sentiment_label")

        if sentiment not in SENTIMENTS:
            sentiment = classify_sentiment(text)

        groups[sentiment].append({
            **document,
            "sentiment_label": sentiment
        })

    clusters = []

    for sentiment, items in groups.items():

        texts = [item["text"] for item in items]

        if len(texts) == 1:
            clusters.append({
                "sentiment": sentiment,
                "documents": items
            })
            continue

        vectorizer = TfidfVectorizer(
            max_features=3000,
            ngram_range=(1, 2)
        )

        matrix = vectorizer.fit_transform(texts)

        # Small MVP heuristic; avoid too many tiny clusters.
        cluster_count = min(3, len(texts))

        model = KMeans(
            n_clusters=cluster_count,
            random_state=42,
            n_init=10
        )

        labels = model.fit_predict(matrix)

        for cluster_id in sorted(set(labels)):
            cluster_documents = [
                items[index]
                for index, label in enumerate(labels)
                if label == cluster_id
            ]

            clusters.append({
                "sentiment": sentiment,
                "documents": cluster_documents
            })

    return clusters
