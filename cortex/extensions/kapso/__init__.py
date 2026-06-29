"""
KAPSO Extension for CORTEX-Persist
Provides integration with Kapso WhatsApp API.
"""

from .gateway import KapsoGateway
from .types import WhatsAppMessage, WhatsAppTemplate, TextMessage

__all__ = [
    "KapsoGateway",
    "WhatsAppMessage",
    "WhatsAppTemplate",
    "TextMessage"
]
