
import re

from app.services.ollama_client import generate_json


def format_evidence(evidence: list[dict]) -> str:
    """Format KG evidence while distinguishing graph sentiment
    from the sentiment of individual financial facts.
    """

    if not evidence:
        return "No evidence was retrieved."

    evidence_blocks = []

    for index, item in enumerate(evidence, start=1):

        graph_sentiment = item.get(
            "graph_sentiment_label",
            item.get("sentiment_label", "Unknown")
        )

        evidence_blocks.append(
            f"""
Evidence {index}:

Financial Evidence:
{item.get('text', '')}

Source: {item.get('source', 'Unknown')}
Target: {item.get('target', 'Unknown')}
Relationship: {item.get('relation', 'Unknown')}

Original Graph Sentiment Label: {graph_sentiment}

Graph ID: {item.get('graph_id', 'Unknown')}
Expansion Type: {item.get('expansion_type', 'Unknown')}

IMPORTANT:
The sentiment label above represents the original
knowledge graph's overall sentiment classification.
It is metadata, not proof that every financial fact
in this evidence has the same sentiment.
Evaluate the underlying financial facts independently.
"""
        )

    return "\n".join(evidence_blocks)


def validate_supporting_evidence(
    supporting_evidence,
    evidence: list[dict]
) -> list[str]:
    """Validate supporting evidence and remove malformed entries."""

    if not isinstance(supporting_evidence, list):
        supporting_evidence = []

    cleaned = []

    for item in supporting_evidence:

        if not isinstance(item, str):
            continue

        item = item.strip()

        if len(item) < 20:
            continue

        if item not in cleaned:
            cleaned.append(item)

    # Use actual retrieved evidence if LLM output is malformed
    if not cleaned:

        for item in evidence:
            text = item.get("text", "")

            if isinstance(text, str) and text.strip():
                cleaned.append(text.strip())

    return cleaned[:5]


def normalize_word(word: str) -> str:
    """Apply lightweight normalization for topic matching."""

    word = word.casefold()

    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]

    if len(word) > 4 and word.endswith("ied"):
        return word[:-3] + "y"

    if len(word) > 4 and word.endswith("ed"):
        return word[:-2]

    if len(word) > 4 and word.endswith("es"):
        return word[:-2]

    if len(word) > 3 and word.endswith("s"):
        return word[:-1]

    return word


def has_explicit_causal_evidence(
    query: str,
    evidence: list[dict]
) -> bool:
    """
    Detect explicit causal explanations relevant to the query.

    This is a targeted rule-based safeguard, not a general
    causal reasoning engine.
    """

    query_lower = query.casefold()

    causal_question = any(
        phrase in query_lower
        for phrase in [
            "why",
            "what caused",
            "what is the reason",
            "reason for",
            "cause of"
        ]
    )

    if not causal_question:
        return False

    causal_patterns = [
        r"\bdue to\b",
        r"\bbecause of\b",
        r"\bcaused by\b",
        r"\bresulted from\b",
        r"\battributed to\b",
        r"\bdriven by\b",
        r"\bowing to\b"
    ]

    ignored_words = {
        "why", "did", "does", "was", "were",
        "the", "what", "is", "are", "of",
        "for", "in", "on", "a", "an", "how",
        "company", "from", "to", "and", "by"
    }

    query_terms = {
        normalize_word(word)
        for word in re.findall(r"[a-zA-Z]+", query_lower)
        if len(word) > 2 and word.lower() not in ignored_words
    }

    for item in evidence:

        text = item.get("text", "")

        if not isinstance(text, str):
            continue

        text_lower = text.casefold()

        has_cause = any(
            re.search(pattern, text_lower)
            for pattern in causal_patterns
        )

        if not has_cause:
            continue

        evidence_terms = {
            normalize_word(word)
            for word in re.findall(r"[a-zA-Z]+", text_lower)
        }

        matching_terms = query_terms.intersection(evidence_terms)

        # Require at least two matching topic terms
        if len(matching_terms) >= 2:
            return True

    return False



def check_evidence_sufficiency(
    query: str,
    evidence: list[dict]
) -> dict:
    """
    Determine whether retrieved evidence can answer the question.

    Uses deterministic causal checking first, followed by
    LLM evaluation when required.
    """

    if not evidence:
        return {
            "sufficient": False,
            "justification": "No evidence was retrieved."
        }

    # Step 1: Deterministic causal evidence check
    if has_explicit_causal_evidence(query, evidence):
        return {
            "sufficient": True,
            "justification": (
                "Retrieved evidence explicitly contains "
                "a causal explanation relevant to the question."
            )
        }

    # Step 2: LLM evaluation
    evidence_text = format_evidence(evidence)

    prompt = f"""
You are a financial evidence evaluator.

Determine whether the supplied evidence is sufficient
to answer the user's question.

USER QUESTION:
{query}

RETRIEVED EVIDENCE:
{evidence_text}

RULES:

1. Read all evidence completely.
2. Original document context is valid evidence.
3. Entity attributes are valid evidence.
4. Knowledge graph relationships are valid evidence.
5. Recognize explicit answers and causal explanations.
6. Do not invent missing information.
7. Do not reject evidence because a fact is not
   represented as a graph relationship.
8. Mark sufficient only when the evidence answers
   the actual question.
9. Graph sentiment labels are metadata, not financial facts.

Return valid JSON only:

{{
    "sufficient": true,
    "justification": "Explain why the evidence is sufficient."
}}
"""

    try:
        result = generate_json(prompt)

        sufficient = result.get("sufficient")

        if not isinstance(sufficient, bool):
            raise ValueError(
                "LLM returned an invalid sufficiency value."
            )

        justification = result.get("justification", "")

        if not isinstance(justification, str):
            justification = ""

        return {
            "sufficient": sufficient,
            "justification": justification
        }

    except Exception as error:
        # Fail safely: do not claim evidence is sufficient
        # when the LLM evaluation could not be completed.
        return {
            "sufficient": False,
            "justification": (
                "LLM evidence evaluation failed. "
                "Evidence sufficiency could not be verified. "
                f"Reason: {str(error)}"
            )
        }



def answer_financial_question(
    query: str,
    evidence: list[dict]
) -> dict:
    """Generate a direct answer using retrieved KG evidence."""

    evidence_text = format_evidence(evidence)

    prompt = f"""
You are a financial question-answering assistant.

Answer the user's question using only the supplied evidence.

USER QUESTION:
{query}

RETRIEVED EVIDENCE:
{evidence_text}

RULES:

1. Answer the exact question asked.
2. Use structured KG facts and original document context.
3. Include relevant financial numbers when available.
4. Explain causal relationships only when explicitly supported.
5. Do not invent financial facts, causes, or numbers.
6. If evidence is insufficient, explain what is missing.
7. Keep the answer clear and concise.
8. Return complete supporting evidence statements.
9. Do not return dictionaries, empty objects, symbols,
   or incomplete strings in supporting_evidence.

Return valid JSON only:

{{
    "answer": "The direct answer to the user's question.",
    "supporting_evidence": [
        "A complete statement from the retrieved evidence."
    ]
}}
"""

    result = generate_json(prompt)

    answer = result.get("answer")

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(
            "LLM returned an invalid financial answer."
        )

    supporting_evidence = validate_supporting_evidence(
        result.get("supporting_evidence", []),
        evidence
    )

    return {
        "answer": answer.strip(),
        "supporting_evidence": supporting_evidence
    }




def classify_financial_sentiment(
    query: str,
    evidence: list[dict]
) -> dict:
    """
    Classify financial sentiment using retrieved evidence.

    Evaluates actual financial signals independently of
    original knowledge graph sentiment labels.
    """

    evidence_text = format_evidence(evidence)

    prompt = f"""
You are a financial sentiment analysis expert.

Analyze the supplied financial evidence and classify
the overall financial sentiment relevant to the user's question.

USER QUESTION:
{query}

KNOWLEDGE GRAPH EVIDENCE:
{evidence_text}

CLASSIFICATION LABELS:
0 = Bearish
1 = Bullish
2 = Neutral

IMPORTANT CLASSIFICATION RULES:

1. Use only the supplied evidence.
2. Read structured graph facts and original context.
3. Consider all relevant positive and negative financial signals.
4. Revenue growth alone does not automatically mean Bullish.
5. Increasing net profit is generally a positive signal.
6. Declining operating margins are generally negative.
7. Increasing operating costs may be negative.
8. Consider explicit causal explanations.
9. If positive and negative signals are balanced, use Neutral.
10. If negative signals clearly dominate, use Bearish.
11. If positive signals clearly dominate, use Bullish.
12. Do not invent financial numbers or explanations.

GRAPH SENTIMENT CONFLICT HANDLING — CRITICAL:

1. Original Graph Sentiment Labels are metadata, not verified
   financial facts.
2. Never use a graph sentiment label as direct evidence
   for classifying the company's financial performance.
3. Never assume that every fact in a Bullish graph is positive.
4. Never assume that every fact in a Bearish graph is negative.
5. Evaluate the actual financial facts in each evidence record.
6. If different graphs have conflicting sentiment labels,
   independently inspect the financial facts from each graph.
7. A graph labelled Bullish may contain negative financial signals.
8. A graph labelled Bearish may contain positive financial signals.
9. Do not count graph sentiment labels as additional positive
   or negative signals.
10. Base the final classification on the combined financial
    evidence, not on the majority of graph sentiment labels.
11. If evidence from different graphs contradicts each other,
    acknowledge the contradiction and explain how it affects
    the final classification.
12. Do not resolve a conflict by automatically preferring
    the latest retrieved graph or the graph with more records.

NUMERICAL ACCURACY RULES — VERY IMPORTANT:

1. Carefully inspect every numerical comparison in the evidence.
2. Preserve the exact original values and their order.
3. If a value changes from 18% to 17.5%, describe it as a
   decrease from 18% to 17.5%.
4. If a value changes from 120 crore to 145 crore,
   describe it as an increase from 120 crore to 145 crore.
5. Never reverse the direction of an increase or decrease.
6. Do not assume a previous value unless it is explicitly
   available in the evidence.
7. Do not confuse the current value with the previous value.
8. If the direction of a change cannot be established,
   describe only the available value without claiming an increase
   or decrease.
9. Before returning the reasoning, verify every numerical
   comparison against the original evidence.

POSITIVE AND NEGATIVE SIGNAL ACCOUNTING:

1. Identify every relevant positive financial signal.
2. Identify every relevant negative financial signal.
3. Do not omit revenue growth when it appears in the evidence.
4. Do not describe one signal as the only positive or negative
   signal unless all retrieved evidence supports that statement.
5. Explicitly acknowledge mixed financial performance.
6. Explain why the negative or positive signals dominate.
7. Do not count the same financial fact multiple times merely
   because it appears in different evidence records.

IMPORTANT DISTINCTION:

Answering the user's specific question and classifying
overall financial sentiment are different tasks.

Do not classify the entire company as Bearish only
because one financial metric declined.

Consider all relevant financial signals.

SUPPORTING EVIDENCE RULES:

1. Return complete, meaningful evidence statements.
2. Use only facts present in retrieved evidence.
3. Do not return dictionaries or objects.
4. Do not return empty strings, symbols, or fragments.
5. Return supporting statements when evidence exists.
6. Include relevant positive and negative evidence.
7. Do not treat graph sentiment labels as supporting
   financial evidence.

Return valid JSON only:

{{
    "sentiment": "Neutral",
    "label": 2,
    "confidence": 0.85,
    "reasoning": "Explain the positive and negative signals.",
    "supporting_evidence": [
        "Relevant complete financial evidence."
    ]
}}
"""

    result = generate_json(prompt)

    sentiment_labels = {
        "Bearish": 0,
        "Bullish": 1,
        "Neutral": 2
    }

    sentiment = result.get("sentiment")
    label = result.get("label")

    if sentiment not in sentiment_labels:
        raise ValueError("Invalid sentiment returned by LLM.")

    if label != sentiment_labels[sentiment]:
        raise ValueError(
            "Sentiment and numerical label do not match."
        )

    confidence = result.get("confidence")

    if (
        not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or not 0 <= confidence <= 1
    ):
        confidence = None

    supporting_evidence = validate_supporting_evidence(
        result.get("supporting_evidence", []),
        evidence
    )

    return {
        "sentiment": sentiment,
        "label": label,
        "confidence": confidence,
        "reasoning": result.get("reasoning", ""),
        "supporting_evidence": supporting_evidence
    }





def classify_with_fallback(
    query: str,
    evidence: list[dict]
) -> dict:
    """
    Generate a fallback classification when KG evidence
    is insufficient.

    If the LLM is unavailable or returns invalid output,
    return a controlled Neutral classification.
    """

    evidence_summary = format_evidence(evidence)

    prompt = f"""
You are a financial sentiment analysis assistant.

The knowledge graph evidence has been evaluated as
insufficient to answer the user's question conclusively.

USER QUESTION:
{query}

AVAILABLE EVIDENCE:
{evidence_summary}

RULES:

1. Do not claim that the knowledge graph supports a conclusion.
2. Do not invent company-specific facts.
3. Do not invent financial numbers or causal explanations.
4. Explain what information is missing.
5. If available signals are mixed or inconclusive, use Neutral.
6. Distinguish general financial interpretation from
   evidence-supported conclusions.
7. Graph sentiment labels are metadata, not financial facts.

LABELS:

0 = Bearish
1 = Bullish
2 = Neutral

Return valid JSON only:

{{
    "sentiment": "Neutral",
    "label": 2,
    "reasoning": "Explain the limitations and assessment.",
    "kg_evidence_supported": false,
    "disclaimer": "This classification is not supported by sufficient knowledge graph evidence."
}}
"""

    labels = {
        "Bearish": 0,
        "Bullish": 1,
        "Neutral": 2
    }

    try:
        result = generate_json(prompt)

        sentiment = result.get("sentiment")
        label = result.get("label")

        if sentiment not in labels:
            raise ValueError("Invalid fallback sentiment.")

        if label != labels[sentiment]:
            raise ValueError(
                "Fallback sentiment label mismatch."
            )

        reasoning = result.get("reasoning", "")

        if not isinstance(reasoning, str) or not reasoning.strip():
            reasoning = (
                "The available knowledge graph evidence "
                "is insufficient for a reliable conclusion."
            )

        return {
            "sentiment": sentiment,
            "label": labels[sentiment],
            "reasoning": reasoning,
            "kg_evidence_supported": False,
            "disclaimer": (
                "This classification is not supported by "
                "sufficient knowledge graph evidence."
            )
        }

    except Exception:
        # Deterministic fallback when LLM generation fails
        return {
            "sentiment": "Neutral",
            "label": 2,
            "reasoning": (
                "The available evidence is insufficient, "
                "and the LLM fallback service could not "
                "complete the classification."
            ),
            "kg_evidence_supported": False,
            "disclaimer": (
                "This is a default Neutral fallback because "
                "sufficient evidence or LLM classification "
                "was unavailable."
            )
        }

