"""
purpose_agents package

Exposes the two sprint-workers so they can be imported as

    from purpose_agents import agent_backend, agent_frontend
"""

from importlib import import_module

agent_backend  = import_module(".agent_backend",  __name__)
agent_frontend = import_module(".agent_frontend", __name__)

__all__ = ["agent_backend", "agent_frontend"]
