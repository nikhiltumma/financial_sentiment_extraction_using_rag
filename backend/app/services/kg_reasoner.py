
import re

from app.services.ollama_client import generate_json


def format_evidence(evidence: list[dict]) -> str:
    """Format retrieved KG evidence without losing original context."""

    if not evidence:
        return "No evidence was retrieved."

    evidence_blocks = []

    for index, item in enumerate(evidence, start=1):
        evidence_blocks.append(
            f"""
Evidence {index}:
Text: {item.get('text', '')}
Source: {item.get('source', 'Unknown')}
Target: {item.get('target', 'Unknown')}
Relationship: {item.get('relation', 'Unknown')}
Sentiment label: {item.get('sentiment_label', 'Unknown')}
Graph ID: {item.get('graph_id', 'Unknown')}
Expansion type: {item.get('expansion_type', 'Unknown')}
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

    First checks for explicit causal evidence.
    Uses the LLM for other sufficiency decisions.
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

    # Step 2: LLM evaluation for other questions
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

Return valid JSON only:

{{
    "sufficient": true,
    "justification": "Explain why the evidence is sufficient."
}}
"""

    result = generate_json(prompt)

    sufficient = result.get("sufficient")

    if not isinstance(sufficient, bool):
        raise ValueError(
            "LLM returned an invalid sufficiency value."
        )

    return {
        "sufficient": sufficient,
        "justification": result.get("justification", "")
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

    Considers positive and negative financial signals,
    including original document context.
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

IMPORTANT RULES:

1. Use only the supplied evidence.
2. Read structured graph facts and original context.
3. Do not blindly trust graph sentiment labels.
4. Consider positive and negative financial signals.
5. Revenue growth alone does not automatically mean Bullish.
6. Increasing net profit is generally a positive signal.
7. Declining operating margins are generally negative.
8. Increasing operating costs may be negative.
9. Consider explicit causal explanations.
10. If positive and negative signals are balanced, use Neutral.
11. If negative signals clearly dominate, use Bearish.
12. If positive signals clearly dominate, use Bullish.
13. Do not invent financial numbers or explanations.
14. Explain why the evidence supports the classification.

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
        raise ValueError(
            "Invalid sentiment returned by LLM."
        )

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
    is insufficient. Disclose the lack of KG support.
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

    result = generate_json(prompt)

    labels = {
        "Bearish": 0,
        "Bullish": 1,
        "Neutral": 2
    }

    sentiment = result.get("sentiment")

    if sentiment not in labels:
        raise ValueError(
            "Invalid fallback sentiment."
        )

    if result.get("label") != labels[sentiment]:
        raise ValueError(
            "Fallback sentiment label mismatch."
        )

    return {
        "sentiment": sentiment,
        "label": labels[sentiment],
        "reasoning": result.get("reasoning", ""),
        "kg_evidence_supported": False,
        "disclaimer": (
            "This classification is not supported by "
            "sufficient knowledge graph evidence."
        )
    }
