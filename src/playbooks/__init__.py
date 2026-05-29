"""Biblioteca de playbooks de outbound + seletor Gemini."""

from .library import PlaybookLibrary, load_playbooks
from .selector import select_playbooks_for_lead

__all__ = ["PlaybookLibrary", "load_playbooks", "select_playbooks_for_lead"]
