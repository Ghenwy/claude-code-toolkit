"""
WebUI Models Module
Pydantic models for message validation and data structures
Incluye models para CHAT-03 Input System features
"""

from .chat import (
    # Core chat models
    ChatMessage, ChatSession, ChatRequest, ChatResponse,
    MessageType, MessageStatus, ConnectionStatus,
    MessageUpdateRequest, MessageStatusUpdateRequest,
    MessageSearchRequest, MessageSearchResult,
    MessageHistoryResponse, MessageStatistics,
    MessageChunk, MessageChunkResponse, MessageThread,
    MessageExport,

    # CHAT-03 Input System models
    InputHistoryEntry, InputDraft, CommandSuggestion,
    InputValidationResult, InputAnalytics,
    InputHistoryRequest, InputHistoryResponse,
    DraftSaveRequest, CommandValidationRequest,
    CommandSuggestionsRequest
)

__all__ = [
    # Core chat models
    "ChatMessage", "ChatSession", "ChatRequest", "ChatResponse",
    "MessageType", "MessageStatus", "ConnectionStatus",
    "MessageUpdateRequest", "MessageStatusUpdateRequest",
    "MessageSearchRequest", "MessageSearchResult",
    "MessageHistoryResponse", "MessageStatistics",
    "MessageChunk", "MessageChunkResponse", "MessageThread",
    "MessageExport",

    # CHAT-03 Input System models
    "InputHistoryEntry", "InputDraft", "CommandSuggestion",
    "InputValidationResult", "InputAnalytics",
    "InputHistoryRequest", "InputHistoryResponse",
    "DraftSaveRequest", "CommandValidationRequest",
    "CommandSuggestionsRequest"
]