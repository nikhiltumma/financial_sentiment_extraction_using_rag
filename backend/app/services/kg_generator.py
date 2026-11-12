
import json
import uuid
from pathlib import Path

from app.services.ollama_client import generate_json, generate_response


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GRAPH_DIR = PROJECT_ROOT / "knowledge_graphs"

GRAPH_DIR.mkdir(parents=True, exist_ok=True)


def merge_cluster(cluster: dict) -> str:
    """Merge related financial texts into one coherent article."""

    texts = [
        item["text"]
        for item in cluster["documents"]
    ]

    if len(texts) == 1:
        return texts[0]

    prompt = f"""
You are an assistant helping merge financial texts.

Merge the following texts into one coherent financial article.

Instructions:
1. Remove duplicate information.
2. Preserve important numerical values.
3. Preserve dates and time references.
4. Do not invent financial facts.
5. If statements contradict each other, clearly preserve
   the disagreement instead of inventing a resolution.
6. Preserve the original meaning.

Sentiment group: {cluster["sentiment"]}

Texts:
{json.dumps(texts, ensure_ascii=False, indent=2)}

Return only the merged article.
"""

    return generate_response(prompt).strip()


def extract_knowledge_graph(
    merged_text: str,
    sentiment: str,
    source_documents: list
) -> dict:
    """Extract financial entities and relations as JSON."""

    prompt = f"""
You are an expert financial knowledge graph extraction system.

Extract a financial knowledge graph from the provided article.

Analyze these five perspectives:

1. Numerical Context:
   Identify financial figures, percentages, prices,
   revenue, profit, losses and other metrics.

2. Temporal Prompting:
   Identify dates, quarters, financial years and
   the time period of each event.

3. Comparative Analysis:
   Identify comparisons between companies,
   periods, estimates and financial performance.

4. Causal Attribution:
   Identify causes, business decisions and events
   that influence financial performance.

5. Risk and Uncertainty Analysis:
   Identify financial risks, threats, uncertainty
   and possible negative outcomes.

Return valid JSON with exactly this structure:

{{
  "entities": [
    {{
      "name": "Entity Name",
      "type": "Company / Metric / Event / Person / Other",
      "attributes": {{
        "key": "value"
      }},
      "sentiment": "Bullish / Bearish / Neutral"
    }}
  ],
  "relations": [
    {{
      "source": "Source Entity",
      "target": "Target Entity",
      "type": "relationship type",
      "sentiment": "Bullish / Bearish / Neutral",
      "distance": 1,
      "evidence": "Supporting text from the article"
    }}
  ],
  "sentiment_label": "{sentiment}"
}}

Rules:
- Use only information supported by the article.
- Do not invent entities, relationships or values.
- Every relation must reference entities in the entities list.
- Direct relationships must have distance 1.
- Use a suitable sentiment for each entity and relation.
- Keep numerical values and dates in entity attributes.
- Include evidence for each relation.
- If information is missing, use an empty value or omit
  the unsupported entity/relation.
- Output JSON only.

Article:
{merged_text}
"""

    graph = generate_json(prompt)

    if not isinstance(graph.get("entities"), list):
        raise ValueError("Invalid graph: entities must be a list.")

    if not isinstance(graph.get("relations"), list):
        raise ValueError("Invalid graph: relations must be a list.")

    graph["sentiment_label"] = sentiment

    # Attach source-document provenance to the graph.
    graph["source_documents"] = [
        {
            "document_id": doc.get("document_id"),
            "source_name": doc.get("source_name"),
            "language": doc.get("language")
        }
        for doc in source_documents
    ]

    graph["graph_id"] = f"kg_{uuid.uuid4().hex[:12]}"

    return graph


def validate_graph(graph: dict) -> dict:
    """Check graph structure and remove invalid references."""

    entity_names = {
        entity.get("name")
        for entity in graph["entities"]
        if entity.get("name")
    }

    valid_relations = []

    for relation in graph["relations"]:
        if (
            relation.get("source") in entity_names
            and relation.get("target") in entity_names
        ):
            relation.setdefault("distance", 1)
            valid_relations.append(relation)

    graph["relations"] = valid_relations

    return graph


def generate_knowledge_graph(documents: list) -> dict:
    """Run clustering, merging and graph extraction."""

    from app.services.clustering import create_sentiment_clusters

    if not documents:
        raise ValueError("No documents provided.")

    clusters = create_sentiment_clusters(documents)

    all_graphs = []

    for cluster in clusters:
        merged_text = merge_cluster(cluster)

        graph = extract_knowledge_graph(
            merged_text=merged_text,
            sentiment=cluster["sentiment"],
            source_documents=cluster["documents"]
        )

        graph = validate_graph(graph)

        graph["merged_text"] = merged_text

        all_graphs.append(graph)

    result = {
        "generation_status": "success",
        "cluster_count": len(clusters),
        "graph_count": len(all_graphs),
        "graphs": all_graphs
    }

    output_file = GRAPH_DIR / (
        f"financial_kg_{uuid.uuid4().hex[:10]}.json"
    )

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )

    result["saved_file"] = str(output_file)

    return result
