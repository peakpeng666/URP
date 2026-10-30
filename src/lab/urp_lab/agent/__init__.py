"""Research agent of the workbench (CONTRACT §9): an LLM plans, workbench tools act, independent checkers decide."""
from .llm import ModelError, OpenAICompatibleModel, Reply, model_from_env
from .manager import POLICY, AgentManager
from .tools import TOOLS

__all__ = ['AgentManager', 'ModelError', 'OpenAICompatibleModel', 'POLICY', 'Reply', 'TOOLS', 'model_from_env']
