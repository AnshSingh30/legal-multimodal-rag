import os
import re
from typing import Any, Optional

import plotly.graph_objects as go
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = "cohere/north-mini-code:free"

def _get_llm() -> ChatOpenAI:
    """Build LLM lazily so env vars from dotenv are guaranteed to be loaded."""
    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
    api_key = os.getenv("OPENROUTER_API_KEY")
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        model=model,
        temperature=0,
        default_headers={
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "Legal Multi-Modal RAG"
        }
    )

NO_ANSWER_PHRASE = "The provided documents do not contain the answer."
NO_CITATION_FALLBACK = (
    "The provided documents do not contain a verifiable citation for this claim; "
    "unable to produce a grounded answer."
)

SYSTEM_PROMPT = f"""You are a highly precise legal document QA assistant.

CRITICAL RULES:
1. Answer ONLY using the facts from the provided context below.
2. If the context does not contain enough information to answer the question, you must explicitly say: "{NO_ANSWER_PHRASE}" Do not guess or use outside knowledge.
3. For every claim you make, you MUST attach a citation using the exact format [Citation: doc_id=<doc_id>, page=<page>], copying the <doc_id> and <page> values exactly from the context block that supports the claim. Never invent a doc_id or page value.
4. Never extrapolate, hallucinate, or add facts not explicitly present in the documents.

Before answering, briefly state which facts from the context support your answer."""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Context:\n{context}\n\nQuestion: {question}")
])

def format_docs(docs: list[Document]) -> str:
    parts = []
    for d in docs:
        doc_id = d.metadata.get("doc_id", "unknown")
        pg = d.metadata.get("page", "?")
        src = d.metadata.get("source", "unknown")
        parts.append(f"[doc_id={doc_id}, page={pg}, source={src}]\n{d.page_content}")
    return "\n\n---\n\n".join(parts)

# FIX 2: LCEL chain — no deprecated QA chain classes
def build_chain(retriever: BaseRetriever) -> Runnable:
    llm = _get_llm()
    return (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

from rag.chart_detector import detect_chart_need
from rag.chart_generator import generate_chart

CRITIQUE_PROMPT = """You are a strict fact-checker.
Review the following "Initial Answer" to the "Question", checking it against the "Context".
If the Initial Answer contains facts, statements, or numbers not present in the Context, REWRITE the answer to remove those hallucinations.
If the Initial Answer is entirely unsupported, state: "The provided documents do not contain the answer."
Otherwise, if the Initial Answer is perfectly faithful to the Context, output it exactly as it is without adding extra commentary.

Question: {question}

Context:
{context}

Initial Answer:
{initial_answer}

Final Faithfully Corrected Answer:"""

critique_prompt = ChatPromptTemplate.from_template(CRITIQUE_PROMPT)

REGEN_PROMPT = """Your previous answer to the "Question" either had no citations, or cited a doc_id/page
that does not appear in the "Context" below. Rewrite the answer using ONLY facts from the Context, and
attach a citation [Citation: doc_id=<doc_id>, page=<page>] — using the exact doc_id/page values shown in
the Context's [doc_id=..., page=..., source=...] headers — to every claim. If no context block supports
an answer, respond exactly: "The provided documents do not contain the answer."

Question: {question}

Context:
{context}

Previous (Invalid) Answer:
{previous_answer}

Corrected Answer:"""

regen_prompt = ChatPromptTemplate.from_template(REGEN_PROMPT)

_CITATION_RE = re.compile(r"\[Citation:\s*doc_id=([^,\]]+),\s*page=([^\]]+)\]")


def _extract_citations(answer: str) -> set[tuple[str, str]]:
    return {(doc_id.strip(), page.strip()) for doc_id, page in _CITATION_RE.findall(answer)}


def _is_grounded(answer: str, valid_keys: set[tuple[str, str]]) -> bool:
    if answer.strip().startswith(NO_ANSWER_PHRASE):
        return True
    cited = _extract_citations(answer)
    return len(cited) > 0 and cited.issubset(valid_keys)


def ask(question: str, retriever: BaseRetriever) -> dict[str, Any]:
    chain = build_chain(retriever)
    # Retrieve docs separately so we can return them alongside the answer
    docs = retriever.invoke(question)
    valid_keys = {(str(d.metadata.get("doc_id", "")), str(d.metadata.get("page", ""))) for d in docs}

    # 1. Generate Initial Answer
    initial_answer = chain.invoke(question)

    # 2. Self-Correction (Critique)
    llm = _get_llm()
    critique_chain = critique_prompt | llm | StrOutputParser()
    context_str = format_docs(docs)

    final_answer = critique_chain.invoke({
        "question": question,
        "context": context_str,
        "initial_answer": initial_answer
    })

    # 3. Citation validation — regenerate once if claims aren't grounded in a real
    # (doc_id, page) from the retrieved context, then fall back to an explicit
    # refusal rather than ever returning an uncited/mis-cited claim.
    if not _is_grounded(final_answer, valid_keys):
        regen_chain = regen_prompt | llm | StrOutputParser()
        final_answer = regen_chain.invoke({
            "question": question,
            "context": context_str,
            "previous_answer": final_answer
        })

    if _is_grounded(final_answer, valid_keys):
        cited_keys = _extract_citations(final_answer)
        citations = [
            d for d in docs
            if (str(d.metadata.get("doc_id", "")), str(d.metadata.get("page", ""))) in cited_keys
        ]
    else:
        final_answer = NO_CITATION_FALLBACK
        citations = []

    # Detect chart need
    chart_info = detect_chart_need(question)
    needs_chart = chart_info.get("needs_chart", False)
    chart_type = chart_info.get("chart_type", "none")
    chart_reason = chart_info.get("reason", "")

    chart_fig: Optional[go.Figure] = None
    if needs_chart and chart_type != "none":
        chart_fig = generate_chart(final_answer, chart_type, context_str)

    return {
        "answer": final_answer,
        "source_documents": docs,
        "citations": citations,
        "chart": chart_fig,
        "chart_type": chart_type,
        "chart_reason": chart_reason
    }
