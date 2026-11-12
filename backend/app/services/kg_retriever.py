import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
GRAPH_DIR = PROJECT_ROOT / "knowledge_graphs"
VECTOR_DIR = PROJECT_ROOT / "vector_store"

VECTOR_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class KGRetriever:

    def __init__(self):
        print("Loading multilingual embedding model...")
        self.model = SentenceTransformer(MODEL_NAME)
        self.index = None
        self.evidence = []

    def graph_to_sentences(self, graph: dict[str, Any]) -> list[dict]:
        """Convert graph relationships and entities into searchable evidence."""

        sentences = []

        entities = {
            entity.get("name"): entity
            for entity in graph.get("entities", [])
            if entity.get("name")
        }

        relations = graph.get("relations", [])
        sentiment = graph.get("sentiment_label", "Neutral")
        graph_id = graph.get("graph_id", "unknown")
        source_documents = graph.get("source_documents", [])
        merged_text = graph.get("merged_text", "")

        # Convert relationships into searchable sentences
        for relation in relations:

            source = relation.get("source", "Unknown")
            target = relation.get("target", "Unknown")

            relation_type = relation.get(
                "type",
                relation.get("relation", "related to")
            )

            evidence_text = relation.get("evidence", "")

            source_entity = entities.get(source, {})
            target_entity = entities.get(target, {})

            source_attributes = source_entity.get("attributes", {})
            target_attributes = target_entity.get("attributes", {})

            sentence = (
                f"{source} {relation_type} {target}. "
                f"Source attributes: "
                f"{json.dumps(source_attributes, ensure_ascii=False)}. "
                f"Target attributes: "
                f"{json.dumps(target_attributes, ensure_ascii=False)}. "
                f"Evidence: {evidence_text}"
                f"Original context: {merged_text}"
            )

            sentences.append({
                "text": sentence,
                "source": source,
                "target": target,
                "relation": relation_type,
                "attributes": {
                    "source": source_attributes,
                    "target": target_attributes
                },
                "sentiment_label": sentiment,
                "graph_id": graph_id,
                "source_documents": source_documents
            })

        # Preserve graph entities even when there are no relationships
        if not relations:

            for entity in entities.values():

                name = entity.get("name", "Unknown")
                attributes = entity.get("attributes", {})
                entity_sentiment = entity.get("sentiment", sentiment)

                sentence = (
                    f"{name} has the following financial information: "
                    f"{json.dumps(attributes, ensure_ascii=False)}. "
                    f"Entity sentiment: {entity_sentiment}"
                    f"Original context: {merged_text}"
                )

                sentences.append({
                    "text": sentence,
                    "source": name,
                    "target": None,
                    "relation": "entity_attributes",
                    "attributes": attributes,
                    "sentiment_label": entity_sentiment,
                    "graph_id": graph_id,
                    "source_documents": source_documents
                })

        return sentences

    def load_graphs(self) -> list[dict]:
        """Load generated knowledge graphs from JSON files."""

        graph_files = list(GRAPH_DIR.glob("*.json"))

        if not graph_files:
            raise FileNotFoundError(
                f"No knowledge graph JSON files found in {GRAPH_DIR}"
            )

        all_evidence = []

        for file_path in graph_files:

            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            # Current Phase 3 format: multiple graphs inside "graphs"
            graphs = data.get("graphs", [])

            # Also support a single graph stored directly at root
            if not graphs and "entities" in data:
                graphs = [data]

            for graph in graphs:
                all_evidence.extend(
                    self.graph_to_sentences(graph)
                )

        if not all_evidence:
            raise ValueError(
                "No searchable evidence found in knowledge graphs."
            )

        self.evidence = all_evidence

        return all_evidence

    def build_index(self) -> dict:
        """Generate embeddings and build the FAISS similarity index."""

        if not self.evidence:
            self.load_graphs()

        texts = [item["text"] for item in self.evidence]

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True
        )

        embeddings = np.asarray(embeddings, dtype="float32")

        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)

        faiss.write_index(
            self.index,
            str(VECTOR_DIR / "financial_kg.index")
        )

        with open(
            VECTOR_DIR / "evidence.json",
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                self.evidence,
                file,
                indent=2,
                ensure_ascii=False
            )

        return {
            "status": "success",
            "evidence_count": len(self.evidence),
            "embedding_dimension": embeddings.shape[1],
            "index_type": "FAISS IndexFlatIP"
        }

    def load_index(self):
        """Load an existing FAISS index and its evidence."""

        index_path = VECTOR_DIR / "financial_kg.index"
        evidence_path = VECTOR_DIR / "evidence.json"

        if not index_path.exists() or not evidence_path.exists():
            raise FileNotFoundError(
                "FAISS index not found. Build the index first."
            )

        self.index = faiss.read_index(str(index_path))

        with open(evidence_path, "r", encoding="utf-8") as file:
            self.evidence = json.load(file)

        if self.index.ntotal != len(self.evidence):
            raise ValueError(
                "FAISS index size does not match evidence metadata."
            )

    def search(
        self,
        query: str,
        top_k: int = 5,
        company: str | None = None
    ) -> list[dict]:
        """
        Retrieve relevant financial graph evidence.

        If company is provided, filter results to that company.
        """

        if not query.strip():
            raise ValueError("Search query cannot be empty.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        if self.index is None:
            self.load_index()

        if self.index.ntotal == 0:
            return []

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        query_embedding = np.asarray(
            query_embedding,
            dtype="float32"
        )

        # Search all records when company filtering is requested.
        # This prevents unrelated records from occupying top_k slots.
        search_k = (
            self.index.ntotal
            if company
            else min(top_k, self.index.ntotal)
        )

        scores, indices = self.index.search(
            query_embedding,
            search_k
        )

        results = []

        for score, idx in zip(scores[0], indices[0]):

            if idx < 0:
                continue

            item = self.evidence[int(idx)].copy()

            # Company-level filtering
            if company:
                searchable_content = " ".join([
                    str(item.get("text", "")),
                    str(item.get("source", "")),
                    str(item.get("target", "")),
                    json.dumps(
                        item.get("attributes", {}),
                        ensure_ascii=False
                    ),
                    json.dumps(
                        item.get("source_documents", []),
                        ensure_ascii=False
                    )
                ])

                if company.casefold() not in searchable_content.casefold():
                    continue

            item["similarity_score"] = float(score)
            item["expansion_type"] = "initial"

            results.append(item)

        return results[:top_k]

    def expand_one_hop(
        self,
        retrieved_evidence: list[dict]
    ) -> list[dict]:
        """
        Expand evidence only within the same knowledge graph.
        Prevent unrelated companies from being mixed.
        """

        if not self.evidence:
            self.load_graphs()

        expanded = list(retrieved_evidence)

        seen = {
            (
                item.get("graph_id"),
                item.get("source"),
                item.get("target"),
                item.get("relation")
            )
            for item in expanded
        }

        # Track connected entities separately for each graph
        graph_entities = {}

        for item in retrieved_evidence:

            graph_id = item.get("graph_id")

            if graph_id not in graph_entities:
                graph_entities[graph_id] = set()

            if item.get("source"):
                graph_entities[graph_id].add(item["source"])

            if item.get("target"):
                graph_entities[graph_id].add(item["target"])

        # Expand only within the graph that produced the retrieved evidence
        for item in self.evidence:

            graph_id = item.get("graph_id")
            connected_entities = graph_entities.get(graph_id, set())

            source = item.get("source")
            target = item.get("target")

            if source in connected_entities or target in connected_entities:

                key = (
                    graph_id,
                    source,
                    target,
                    item.get("relation")
                )

                if key not in seen:

                    expanded_item = item.copy()
                    expanded_item["expansion_type"] = "one_hop"

                    expanded.append(expanded_item)
                    seen.add(key)

        return expanded
