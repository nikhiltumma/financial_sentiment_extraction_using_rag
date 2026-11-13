
import sys
from pathlib import Path

# Add backend directory to Python path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.kg_retriever import KGRetriever


# ==========================================
# 1. PRECISION@K
# ==========================================


def precision_at_k(retrieved, relevant, k):

    if k <= 0:
        raise ValueError("k must be greater than zero.")

    retrieved_k = retrieved[:k]

    if not retrieved_k:
        return 0.0

    relevant_count = sum(
        1 for graph_id in retrieved_k
        if graph_id in relevant
    )

    # Avoid penalizing retrieval when fewer than K
    # unique candidate graphs are available.
    denominator = len(retrieved_k)

    return relevant_count / denominator



# ==========================================
# 2. RECALL@K
# ==========================================

def recall_at_k(retrieved, relevant, k):

    if k <= 0:
        raise ValueError("k must be greater than zero.")

    if not relevant:
        return 0.0

    retrieved_k = set(retrieved[:k])

    relevant_retrieved = retrieved_k.intersection(relevant)

    return len(relevant_retrieved) / len(relevant)


# ==========================================
# 3. MEAN RECIPROCAL RANK
# ==========================================

def mean_reciprocal_rank(retrieved, relevant):

    for rank, graph_id in enumerate(retrieved, start=1):

        if graph_id in relevant:
            return 1.0 / rank

    return 0.0


# ==========================================
# 4. RETRIEVAL EVALUATION
# ==========================================

def evaluate_retrieval(retriever, test_cases, k=5):

    if k <= 0:
        raise ValueError("k must be greater than zero.")

    if not test_cases:
        print("No evaluation test cases found.")
        return

    precision_scores = []
    recall_scores = []
    reciprocal_ranks = []

    print("\n========== RETRIEVAL EVALUATION ==========")

    for index, test in enumerate(test_cases, start=1):

        query = test["query"]
        relevant_graphs = set(test["relevant_graph_ids"])

        # Retrieve evidence with company filtering
        results = retriever.search(
            query=query,
            top_k=20,
            company=test.get("company")
        )

        # Keep unique graph IDs in retrieval order
        retrieved_graphs = list(dict.fromkeys(
            item["graph_id"]
            for item in results
            if item.get("graph_id")
        ))

        # Calculate metrics
        precision = precision_at_k(
            retrieved_graphs,
            relevant_graphs,
            k
        )

        recall = recall_at_k(
            retrieved_graphs,
            relevant_graphs,
            k
        )

        mrr = mean_reciprocal_rank(
            retrieved_graphs,
            relevant_graphs
        )

        precision_scores.append(precision)
        recall_scores.append(recall)
        reciprocal_ranks.append(mrr)

        # Display individual results
        print(f"\n----------- TEST CASE {index} -----------")

        print("Query:", query)
        print("Company:", test.get("company"))

        print("Retrieved graphs:", retrieved_graphs[:k])
        print("Relevant graphs:", sorted(relevant_graphs))

        print(f"Precision@{k}: {precision:.4f}")
        print(f"Recall@{k}: {recall:.4f}")
        print(f"MRR: {mrr:.4f}")

    # ======================================
    # 5. OVERALL RESULTS
    # ======================================

    count = len(test_cases)

    mean_precision = sum(precision_scores) / count
    mean_recall = sum(recall_scores) / count
    mean_mrr = sum(reciprocal_ranks) / count

    print("\n========== OVERALL RESULTS ==========")

    print(f"Total test queries: {count}")

    print(f"Mean Precision@{k}: {mean_precision:.4f}")
    print(f"Mean Recall@{k}: {mean_recall:.4f}")
    print(f"Mean MRR: {mean_mrr:.4f}")

    print("\n========== EVALUATION COMPLETED ==========")


# ==========================================
# 6. MAIN
# ==========================================

if __name__ == "__main__":

    retriever = KGRetriever()

    # Ground-truth relevance labels based on
    # manually inspected knowledge graph evidence.

    test_cases = [

        {
            "query": "Why did ABC Technologies Q4 operating margin decline?",
            "company": "ABC Technologies",
            "relevant_graph_ids": [
                "kg_1712b4ff513f"
            ]
        },

        {
            "query": "How much did ABC Technologies net profit increase?",
            "company": "ABC Technologies",
            "relevant_graph_ids": [
                "kg_1712b4ff513f"
            ]
        },

        {
            "query": "What revenue growth does ABC Technologies expect next year?",
            "company": "ABC Technologies",
            "relevant_graph_ids": [
                "kg_2f35c55f53e0"
            ]
        },

        {
            "query": "What are investors concerned about at ABC Technologies?",
            "company": "ABC Technologies",
            "relevant_graph_ids": [
                "kg_2f35c55f53e0"
            ]
        },

        {
            "query": "How much did Surya Technologies cloud services revenue grow?",
            "company": "Surya Technologies Limited",
            "relevant_graph_ids": [
                "kg_7520dcb1fcfd"
            ]
        },

        {
            "query": "How much did Surya Technologies Q4 revenue increase?",
            "company": "Surya Technologies Limited",
            "relevant_graph_ids": [
                "kg_7520dcb1fcfd"
            ]
        },

        {
            "query": "Why did Surya Technologies operating margin decline?",
            "company": "Surya Technologies Limited",
            "relevant_graph_ids": [
                "kg_7520dcb1fcfd"
            ]
        },

        {
            "query": "How much did Surya Technologies net profit increase?",
            "company": "Surya Technologies Limited",
            "relevant_graph_ids": [
                "kg_7520dcb1fcfd"
            ]
        }

    ]

    evaluate_retrieval(
        retriever=retriever,
        test_cases=test_cases,
        k=5
    )
