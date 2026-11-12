
from app.services.kg_retriever import KGRetriever

retriever = KGRetriever()

# Build FAISS index
index_result = retriever.build_index()

print("\nINDEX RESULT:")
print(index_result)

# Initial retrieval
query = "Why did ABC Technologies operating margin decline?"

initial_results = retriever.search(query, top_k=3)

print("\nINITIAL RETRIEVAL:")

for item in initial_results:
    print(
        item["source"],
        "->",
        item["target"],
        "|",
        item["similarity_score"]
    )

# One-hop expansion
expanded_results = retriever.expand_one_hop(initial_results)

print("\nEXPANDED EVIDENCE:")

for i, item in enumerate(expanded_results, start=1):
    print(f"\nResult {i}")
    print("Evidence:", item["text"])
    print("Graph:", item["graph_id"])
    print("Expansion:", item.get("expansion_type", "initial"))
    print("Sentiment:", item["sentiment_label"])

print("\nInitial evidence count:", len(initial_results))
print("Expanded evidence count:", len(expanded_results))
