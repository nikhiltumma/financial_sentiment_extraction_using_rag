
from app.services.kg_retriever import KGRetriever

from app.services.kg_reasoner import (
    check_evidence_sufficiency,
    classify_financial_sentiment,
    classify_with_fallback
)

retriever = KGRetriever()

query = "Why did ABC Technologies operating margin decline?"

# 1. Retrieve evidence
initial_evidence = retriever.search(query, top_k=3)

# 2. Expand evidence
expanded_evidence = retriever.expand_one_hop(initial_evidence)

# 3. Check sufficiency
sufficiency = check_evidence_sufficiency(
    query,
    expanded_evidence
)

print("\nSUFFICIENCY RESULT:")
print(sufficiency)

# 4. Final classification or fallback
if sufficiency["sufficient"]:

    result = classify_financial_sentiment(
        query,
        expanded_evidence
    )

else:

    result = classify_with_fallback(
        query,
        expanded_evidence
    )

print("\nFINAL RESULT:")
print(result)
