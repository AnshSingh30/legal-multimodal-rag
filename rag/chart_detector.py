import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """You are a classifier. Given a user question, respond with ONLY a JSON object:
{{"needs_chart": true/false, "chart_type": "bar|line|pie|scatter|table|none", "reason": "one sentence"}}

Return needs_chart=true if the question asks for: comparisons, trends over time,
distributions, rankings, proportions, or "show me a chart/graph/plot".
Return needs_chart=false for factual questions, definitions, or legal analysis.
"""

def detect_chart_need(question: str) -> dict:
    model = os.getenv("OPENROUTER_MODEL", "cohere/north-mini-code:free")
    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model=model,
        temperature=0,
        default_headers={
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "Legal Multi-Modal RAG"
        }
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{question}")
    ])
    
    chain = prompt | llm
    
    try:
        response = chain.invoke({"question": question})
        # Clean up in case the model returns markdown code blocks
        clean_text = response.content.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        return json.loads(clean_text.strip())
    except Exception as e:
        # Fallback if anything goes wrong
        return {"needs_chart": False, "chart_type": "none", "reason": f"Error detecting chart need: {str(e)}"}
