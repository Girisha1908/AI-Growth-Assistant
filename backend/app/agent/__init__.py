"""The agent layer: route a request to a skill, ground it in retrieved
transcript excerpts, run it on whichever LLMProvider is configured.

    request ─▶ router (which skill?) ─▶ retrieval ─▶ gate ─▶ skill ─▶ answer + sources + artifact
"""
