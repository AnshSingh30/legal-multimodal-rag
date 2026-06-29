import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

DEFAULT_MODEL = "cohere/north-mini-code:free"

def _get_llm():
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

SYSTEM_PROMPT = """You are a highly precise legal document QA assistant.

CRITICAL RULES:
1. Answer ONLY using the facts from the provided context below.
2. If the context does not contain enough information to answer the question, you must explicitly say: "The provided documents do not contain the answer." Do not guess or use outside knowledge.
3. For every claim you make, you MUST cite the exact source using the format [Source: filename, Page X].
4. Never extrapolate, hallucinate, or add facts not explicitly present in the documents.

Before answering, briefly state which facts from the context support your answer."""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Context:\n{context}\n\nQuestion: {question}")
])

def format_docs(docs):
    parts = []
    for d in docs:
        src = d.metadata.get("source", "unknown")
        pg  = d.metadata.get("page", "?")
        parts.append(f"[Source: {src}, Page {pg}]\n{d.page_content}")
    return "\n\n---\n\n".join(parts)

# FIX 2: LCEL chain — no deprecated QA chain classes
def build_chain(retriever):
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

from pipeline.chart_detector import detect_chart_need
from pipeline.chart_generator import generate_chart

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

def ask(question: str, retriever) -> dict:
    chain = build_chain(retriever)
    # Retrieve docs separately so we can return them alongside the answer
    docs = retriever.invoke(question)
    
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
    
    # Detect chart need
    chart_info = detect_chart_need(question)
    needs_chart = chart_info.get("needs_chart", False)
    chart_type = chart_info.get("chart_type", "none")
    chart_reason = chart_info.get("reason", "")
    
    chart_fig = None
    if needs_chart and chart_type != "none":
        import streamlit as st
        with st.spinner("Generating chart..."):
            chart_fig = generate_chart(final_answer, chart_type, context_str)
        
    return {
        "answer": final_answer, 
        "source_documents": docs,
        "chart": chart_fig,
        "chart_type": chart_type,
        "chart_reason": chart_reason
    }
