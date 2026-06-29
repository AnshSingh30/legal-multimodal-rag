import os
import json
import plotly.graph_objects as go
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """You are a data extraction assistant. Given a RAG answer and source context,
extract the structured data needed to build a chart.

Respond ONLY with valid JSON:
{{
  "title": "chart title",
  "x_label": "label",
  "y_label": "label",
  "data": [
    {{"label": "Category A", "value": 42}},
    {{"label": "Category B", "value": 17}}
  ]
}}

If you cannot extract numeric data, respond: {{"error": "no_numeric_data"}}
"""

def generate_chart(answer: str, chart_type: str, context: str):
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
        ("human", "Answer: {answer}\n\nContext: {context}")
    ])
    
    chain = prompt | llm
    
    try:
        response = chain.invoke({"answer": answer, "context": context})
        
        clean_text = response.content.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        data_dict = json.loads(clean_text.strip())
    except Exception as e:
        print(f"Error parsing JSON from LLM: {e}")
        return None
        
    if "error" in data_dict:
        return None
        
    title = data_dict.get("title", "")
    x_label = data_dict.get("x_label", "")
    y_label = data_dict.get("y_label", "")
    data = data_dict.get("data", [])
    
    if not data:
        return None
        
    labels = [str(item.get("label", "")) for item in data]
    
    # Try to convert values to float
    try:
        values = [float(item.get("value", 0)) for item in data]
    except ValueError:
        return None
        
    fig = go.Figure()
    
    if chart_type == "bar":
        fig.add_trace(go.Bar(x=labels, y=values))
    elif chart_type == "line":
        fig.add_trace(go.Scatter(x=labels, y=values, mode="lines+markers"))
    elif chart_type == "pie":
        fig.add_trace(go.Pie(labels=labels, values=values))
    elif chart_type == "scatter":
        fig.add_trace(go.Scatter(x=labels, y=values, mode="markers"))
    elif chart_type == "table":
        fig.add_trace(go.Table(
            header=dict(values=[x_label, y_label], fill_color='paleturquoise', align='left'),
            cells=dict(values=[labels, values], fill_color='lavender', align='left')
        ))
    else:
        return None
        
    fig.update_layout(
        title=title,
        xaxis_title=x_label if chart_type != "pie" and chart_type != "table" else None,
        yaxis_title=y_label if chart_type != "pie" and chart_type != "table" else None,
        template="plotly_white",
        plot_bgcolor="white",
        paper_bgcolor="white"
    )
    
    return fig
