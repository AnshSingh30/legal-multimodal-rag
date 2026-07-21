import sys
import types


def ensure_ragas_importable() -> None:
    """ragas 0.4's legacy LangchainLLMWrapper import path still pulls in
    langchain_community.chat_models.vertexai, which no longer exists in the
    langchain_community version pinned here. Stub it out before importing
    ragas anywhere. Must run before the first `import ragas`."""
    if "langchain_community.chat_models.vertexai" in sys.modules:
        return
    stub = types.ModuleType("langchain_community.chat_models.vertexai")
    stub.ChatVertexAI = type("ChatVertexAI", (object,), {})
    sys.modules["langchain_community.chat_models.vertexai"] = stub
