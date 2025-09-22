"""
Chat Models - Enhanced Pydantic models para advanced message features
Implementa CHAT-02 backend features: progressive loading, threading, status tracking
Siguiendo standards/fastapi.yaml y standards/python.yaml
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator, field_validator


class MessageType(str, Enum):
    """Tipos de mensaje para el chat interface"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"


class MessageStatus(str, Enum):
    """Enhanced estado del mensaje con advanced tracking"""
    PENDING = "pending"
    SENDING = "sending"  # Cliente enviando mensaje
    SENT = "sent"        # Mensaje enviado al servidor
    RECEIVED = "received" # Servidor recibió mensaje
    PROCESSING = "processing"  # Servidor procesando
    COMPLETED = "completed"   # Procesamiento completo
    STREAMING = "streaming"   # Respuesta siendo transmitida en chunks
    FAILED = "failed"       # Error en procesamiento
    EDITED = "edited"       # Mensaje fue editado
    DELETED = "deleted"     # Mensaje marcado como eliminado


class ChatMessage(BaseModel):
    """
    Modelo principal para mensajes del chat
    Pydantic v2 optimizado con validation strategy
    """
    id: UUID = Field(default_factory=uuid4, description="ID único del mensaje")
    content: str = Field(..., min_length=0, max_length=50000, description="Contenido del mensaje")
    message_type: MessageType = Field(..., description="Tipo de mensaje")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp UTC")
    status: MessageStatus = Field(default=MessageStatus.PENDING, description="Estado del mensaje")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Metadatos adicionales")

    # Nuevos campos para features avanzadas
    thread_id: Optional[UUID] = Field(default=None, description="ID del hilo de conversación")
    parent_message_id: Optional[UUID] = Field(default=None, description="ID del mensaje padre para threading")
    edit_history: List[Dict[str, Any]] = Field(default_factory=list, description="Historial de ediciones")
    is_bookmarked: bool = Field(default=False, description="Mensaje marcado como bookmark")
    response_time_ms: Optional[int] = Field(default=None, description="Tiempo de respuesta en milisegundos")
    chunk_info: Optional[Dict[str, Any]] = Field(default=None, description="Info para progressive loading")
    search_keywords: List[str] = Field(default_factory=list, description="Keywords para búsqueda")
    export_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos para export")

    @field_validator('content', mode='before')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Enhanced validación de contenido con streaming support"""
        # Permitir contenido vacío para mensajes de streaming
        if v is None:
            raise ValueError("Contenido no puede ser None")
        return v  # No strip para preservar espacios en streaming

    def add_edit_record(self, old_content: str, edit_reason: Optional[str] = None) -> None:
        """Añadir registro de edición al historial"""
        edit_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "old_content": old_content,
            "new_content": self.content,
            "reason": edit_reason,
            "edit_id": str(uuid4())
        }
        self.edit_history.append(edit_record)
        self.status = MessageStatus.EDITED

    def toggle_bookmark(self) -> bool:
        """Toggle bookmark status y retorna nuevo estado"""
        self.is_bookmarked = not self.is_bookmarked
        return self.is_bookmarked

    def set_chunk_info(self, chunk_index: int, total_chunks: int, is_complete: bool = False) -> None:
        """Configurar información de chunk para progressive loading"""
        self.chunk_info = {
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "is_complete": is_complete,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.status = MessageStatus.STREAMING if not is_complete else MessageStatus.COMPLETED

    def extract_search_keywords(self) -> List[str]:
        """Extraer keywords del contenido para indexación de búsqueda"""
        import re
        # Extraer palabras de 3+ caracteres, excluyendo palabras comunes
        stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "has", "her", "was", "one", "our", "out", "day", "get", "use", "man", "new", "now", "way", "may", "say"}
        words = re.findall(r'\b\w{3,}\b', self.content.lower())
        keywords = [word for word in words if word not in stop_words]
        self.search_keywords = list(set(keywords))  # Eliminar duplicados
        return self.search_keywords

    class Config:
        """Pydantic v2 configuration optimizada"""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        validate_assignment = True
        use_enum_values = True


class ChatRequest(BaseModel):
    """Enhanced request model para new chat messages"""
    content: str = Field(..., min_length=1, max_length=50000)
    message_type: MessageType = Field(default=MessageType.USER)
    metadata: Optional[dict[str, Any]] = Field(default=None)

    # Nuevos campos para features avanzadas
    thread_id: Optional[UUID] = Field(default=None, description="ID del thread")
    parent_message_id: Optional[UUID] = Field(default=None, description="ID del mensaje padre")
    enable_progressive_loading: bool = Field(default=False, description="Activar carga progresiva")
    auto_extract_keywords: bool = Field(default=True, description="Auto-extraer keywords")


class MessageUpdateRequest(BaseModel):
    """Request model para actualizar mensajes existentes"""
    message_id: UUID = Field(..., description="ID del mensaje a actualizar")
    new_content: Optional[str] = Field(default=None, description="Nuevo contenido")
    edit_reason: Optional[str] = Field(default=None, description="Razón de la edición")
    toggle_bookmark: Optional[bool] = Field(default=None, description="Toggle bookmark status")


class MessageStatusUpdateRequest(BaseModel):
    """Request model para actualizar status de mensajes"""
    message_id: UUID = Field(..., description="ID del mensaje")
    new_status: MessageStatus = Field(..., description="Nuevo estado")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos adicionales")


class MessageSearchRequest(BaseModel):
    """Request model para búsqueda de mensajes"""
    query: str = Field(..., min_length=1, description="Término de búsqueda")
    session_id: Optional[UUID] = Field(default=None, description="Buscar en session específica")
    message_types: Optional[List[MessageType]] = Field(default=None, description="Filtrar por tipos")
    date_from: Optional[datetime] = Field(default=None, description="Buscar desde fecha")
    date_to: Optional[datetime] = Field(default=None, description="Buscar hasta fecha")
    bookmarked_only: bool = Field(default=False, description="Solo mensajes bookmarked")
    limit: int = Field(default=50, ge=1, le=100, description="Límite de resultados")


class ChatResponse(BaseModel):
    """Enhanced response model para WebSocket/HTTP responses"""
    message: ChatMessage
    success: bool = Field(default=True)
    error: Optional[str] = Field(default=None)

    # Nuevos campos para features avanzadas
    chunk_info: Optional[Dict[str, Any]] = Field(default=None, description="Info de chunking")
    thread_info: Optional[Dict[str, Any]] = Field(default=None, description="Info del thread")
    processing_time_ms: Optional[int] = Field(default=None, description="Tiempo de procesamiento")


class ConnectionStatus(BaseModel):
    """WebSocket connection status tracking"""
    client_id: UUID = Field(default_factory=uuid4)
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    last_heartbeat: Optional[datetime] = Field(default=None)


class MessageChunk(BaseModel):
    """Model para chunks de mensajes largos en progressive loading"""
    chunk_id: UUID = Field(default_factory=uuid4)
    message_id: UUID = Field(..., description="ID del mensaje principal")
    chunk_index: int = Field(..., description="Índice del chunk (0-based)")
    total_chunks: int = Field(..., description="Total de chunks para este mensaje")
    content: str = Field(..., description="Contenido del chunk")
    is_final: bool = Field(default=False, description="Es el último chunk")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StreamingStatus(str, Enum):
    """Estados para streaming en tiempo real"""
    THINKING = "thinking"        # Claude está procesando
    TYPING = "typing"           # Comenzando a escribir respuesta
    STREAMING = "streaming"     # Enviando caracteres
    PAUSED = "paused"          # Pausa temporal
    COMPLETE = "complete"      # Streaming terminado
    ERROR = "error"            # Error durante streaming


class StreamingChunk(BaseModel):
    """Modelo para chunks de streaming caracter por caracter"""
    chunk_id: UUID = Field(default_factory=uuid4)
    message_id: UUID = Field(..., description="ID del mensaje siendo streamificado")
    session_id: UUID = Field(..., description="ID de la session")
    content: str = Field(..., description="Contenido del chunk (caracteres/palabras)")
    chunk_type: str = Field(default="content", description="Tipo: content, status, metadata")
    position: int = Field(..., description="Posición en el mensaje completo")
    is_final: bool = Field(default=False, description="Es el último chunk del mensaje")
    status: StreamingStatus = Field(default=StreamingStatus.STREAMING)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos del chunk")


class StreamingState(BaseModel):
    """Estado del streaming para una session"""
    session_id: UUID = Field(..., description="ID de la session")
    message_id: Optional[UUID] = Field(default=None, description="ID del mensaje actualmente streaming")
    status: StreamingStatus = Field(default=StreamingStatus.THINKING)
    characters_sent: int = Field(default=0, description="Caracteres enviados hasta ahora")
    total_characters: Optional[int] = Field(default=None, description="Total estimado de caracteres")
    words_per_minute: float = Field(default=150.0, description="Velocidad de escritura simulada")
    last_chunk_time: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=False, description="Streaming activo")
    connected_clients: List[UUID] = Field(default_factory=list, description="Clientes conectados")


class StreamingRequest(BaseModel):
    """Request para iniciar streaming"""
    message_content: str = Field(..., min_length=1, description="Contenido a streamificar")
    session_id: UUID = Field(..., description="ID de la session")
    chunk_size: int = Field(default=1, ge=1, le=10, description="Caracteres por chunk")
    delay_ms: int = Field(default=50, ge=10, le=500, description="Delay entre chunks en ms")
    typing_speed_wpm: float = Field(default=150.0, ge=50.0, le=300.0, description="Velocidad de escritura simulada")
    include_thinking_time: bool = Field(default=True, description="Incluir tiempo de 'pensamiento'")


class TypingIndicator(BaseModel):
    """Indicador de escritura para mostrar en UI"""
    session_id: UUID = Field(..., description="ID de la session")
    user_type: str = Field(default="assistant", description="Tipo de usuario escribiendo")
    is_typing: bool = Field(default=True, description="Está escribiendo actualmente")
    message: Optional[str] = Field(default=None, description="Mensaje de estado opcional")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[int] = Field(default=None, description="Duración estimada")


class ConnectionState(BaseModel):
    """Estado de conexión mejorado para streaming"""
    client_id: UUID = Field(default_factory=uuid4)
    session_id: Optional[UUID] = Field(default=None, description="Session asociada")
    connection_type: str = Field(..., description="websocket o sse")
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    supports_streaming: bool = Field(default=True, description="Soporta streaming real-time")
    latency_ms: Optional[float] = Field(default=None, description="Latencia estimada")
    reconnect_count: int = Field(default=0, description="Número de reconexiones")
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Calidad de conexión 0-1")


class MessageSearchResult(BaseModel):
    """Result model para búsquedas de mensajes"""
    message: ChatMessage
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Score de relevancia 0-1")
    matched_keywords: List[str] = Field(default_factory=list)
    context_snippet: str = Field(..., description="Snippet del contexto donde se encontró")


class MessageThread(BaseModel):
    """Model para threading de conversaciones"""
    thread_id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(..., description="Session que contiene este thread")
    root_message_id: UUID = Field(..., description="Mensaje que inició el thread")
    message_ids: List[UUID] = Field(default_factory=list, description="IDs de mensajes en orden cronológico")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    def add_message_to_thread(self, message_id: UUID) -> None:
        """Añadir mensaje al thread"""
        self.message_ids.append(message_id)
        self.last_activity = datetime.utcnow()


class MessageStatistics(BaseModel):
    """Model para estadísticas de mensajes"""
    session_id: UUID = Field(..., description="ID de la session")
    total_messages: int = Field(default=0)
    user_messages: int = Field(default=0)
    assistant_messages: int = Field(default=0)
    average_response_time_ms: Optional[float] = Field(default=None)
    bookmarked_count: int = Field(default=0)
    edited_count: int = Field(default=0)
    failed_count: int = Field(default=0)
    most_used_keywords: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class MessageExport(BaseModel):
    """Model para export de mensajes"""
    export_id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(..., description="Session a exportar")
    format_type: str = Field(..., description="Formato: json, markdown, txt, html")
    include_metadata: bool = Field(default=True)
    include_bookmarks_only: bool = Field(default=False)
    date_range_start: Optional[datetime] = Field(default=None)
    date_range_end: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    file_size_bytes: Optional[int] = Field(default=None)


class ChatSession(BaseModel):
    """Enhanced Session model para advanced chat state management"""
    session_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    messages: list[ChatMessage] = Field(default_factory=list)
    is_active: bool = Field(default=True)

    # Nuevos campos para features avanzadas
    threads: List[MessageThread] = Field(default_factory=list, description="Threads de conversación")
    statistics: Optional[MessageStatistics] = Field(default=None, description="Estadísticas de la session")
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    title: Optional[str] = Field(default=None, description="Título de la conversación")
    description: Optional[str] = Field(default=None, description="Descripción de la session")

    def add_message(self, message: ChatMessage) -> None:
        """Enhanced añadir mensaje con thread tracking"""
        self.messages.append(message)
        self.last_activity = datetime.utcnow()

        # Auto-generar thread si no existe
        if not message.thread_id:
            message.thread_id = self._get_or_create_thread(message)

        # Actualizar estadísticas
        self._update_statistics()

    def get_recent_messages(self, limit: int = 50) -> list[ChatMessage]:
        """Obtener mensajes recientes con limit"""
        return self.messages[-limit:] if self.messages else []

    def get_messages_by_thread(self, thread_id: UUID) -> list[ChatMessage]:
        """Obtener mensajes de un thread específico"""
        return [msg for msg in self.messages if msg.thread_id == thread_id]

    def get_bookmarked_messages(self) -> list[ChatMessage]:
        """Obtener solo mensajes marcados como bookmarks"""
        return [msg for msg in self.messages if msg.is_bookmarked]

    def search_messages(self, query: str) -> List[MessageSearchResult]:
        """Búsqueda básica en mensajes de la session"""
        results = []
        query_lower = query.lower()

        for message in self.messages:
            if query_lower in message.content.lower():
                # Score básico basado en coincidencias
                content_lower = message.content.lower()
                matches = content_lower.count(query_lower)
                score = min(matches / 10.0, 1.0)  # Normalizar a 0-1

                # Crear snippet de contexto
                snippet_start = max(0, content_lower.find(query_lower) - 50)
                snippet_end = min(len(message.content), snippet_start + 150)
                snippet = message.content[snippet_start:snippet_end]

                results.append(MessageSearchResult(
                    message=message,
                    relevance_score=score,
                    matched_keywords=[query],
                    context_snippet=snippet
                ))

        # Ordenar por relevancia
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results

    def _get_or_create_thread(self, message: ChatMessage) -> UUID:
        """Obtener o crear thread para el mensaje"""
        # Lógica simple: alternar entre user/assistant crea un thread
        if not self.messages:  # Primer mensaje
            thread = MessageThread(
                session_id=self.session_id,
                root_message_id=message.id
            )
            self.threads.append(thread)
            return thread.thread_id

        # Buscar thread activo más reciente
        if self.threads:
            latest_thread = max(self.threads, key=lambda t: t.last_activity)
            return latest_thread.thread_id

        # Crear nuevo thread si no existe
        thread = MessageThread(
            session_id=self.session_id,
            root_message_id=message.id
        )
        self.threads.append(thread)
        return thread.thread_id

    def _update_statistics(self) -> None:
        """Actualizar estadísticas de la session"""
        if not self.statistics:
            self.statistics = MessageStatistics(session_id=self.session_id)

        stats = self.statistics
        stats.total_messages = len(self.messages)
        stats.user_messages = len([m for m in self.messages if m.message_type == MessageType.USER])
        stats.assistant_messages = len([m for m in self.messages if m.message_type == MessageType.ASSISTANT])
        stats.bookmarked_count = len([m for m in self.messages if m.is_bookmarked])
        stats.edited_count = len([m for m in self.messages if m.edit_history])
        stats.failed_count = len([m for m in self.messages if m.status == MessageStatus.FAILED])

        # Calcular tiempo promedio de respuesta
        response_times = [m.response_time_ms for m in self.messages if m.response_time_ms]
        if response_times:
            stats.average_response_time_ms = sum(response_times) / len(response_times)

        stats.last_updated = datetime.utcnow()


# Forward references para response models que necesitan las clases definidas arriba
class MessageChunkResponse(BaseModel):
    """Response model específico para chunks de progressive loading"""
    chunk: MessageChunk
    is_complete: bool = Field(..., description="Si el mensaje está completo")
    total_content_length: Optional[int] = Field(default=None, description="Longitud total del contenido")


class MessageHistoryResponse(BaseModel):
    """Enhanced response model para historial de mensajes"""
    session_id: UUID = Field(..., description="ID de la session")
    messages: List[ChatMessage] = Field(..., description="Lista de mensajes")
    total_count: int = Field(..., description="Total de mensajes en la session")
    page: int = Field(default=1, description="Página actual")
    page_size: int = Field(default=50, description="Tamaño de página")
    has_more: bool = Field(..., description="Si hay más páginas")
    threads: List['MessageThread'] = Field(default_factory=list, description="Threads de la session")
    statistics: Optional['MessageStatistics'] = Field(default=None, description="Estadísticas de la session")


# ========================================
# NUEVOS MODELOS PARA CHAT-03: INPUT SYSTEM
# ========================================

class InputHistoryEntry(BaseModel):
    """
    Modelo para entrada individual en el historial de input
    Pydantic v2 optimizado para input tracking y persistence
    """
    id: UUID = Field(default_factory=uuid4, description="ID único de la entrada")
    session_id: UUID = Field(..., description="ID de la session asociada")
    text: str = Field(..., min_length=1, max_length=50000, description="Texto ingresado")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp UTC")

    # Metadatos avanzados para análisis
    command_type: Optional[str] = Field(default=None, description="Tipo de comando detectado")
    input_length: int = Field(default=0, description="Longitud del input en caracteres")
    word_count: int = Field(default=0, description="Número de palabras")
    typing_duration_ms: Optional[int] = Field(default=None, description="Tiempo de escritura en ms")
    cursor_position: Optional[int] = Field(default=None, description="Posición final del cursor")
    is_command: bool = Field(default=False, description="Si es un comando de Claude Code")
    validation_status: str = Field(default="valid", description="Estado de validación")

    @field_validator('text', mode='before')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validación mejorada del texto de entrada"""
        if not v or not v.strip():
            raise ValueError("El texto de entrada no puede estar vacío")
        return v.strip()

    def model_post_init(self, __context) -> None:
        """Post-procesamiento automático tras inicialización (Pydantic v2)"""
        self.input_length = len(self.text)
        self.word_count = len(self.text.split())
        self.is_command = self._detect_command()

    def _detect_command(self) -> bool:
        """Detectar si el input es un comando de Claude Code"""
        command_patterns = ['/A-', '/B-', 'M1-', '/help', '/clear', '/history']
        return any(self.text.strip().startswith(pattern) for pattern in command_patterns)


class InputDraft(BaseModel):
    """
    Modelo para drafts/borradores de input con auto-save
    Persistencia para recuperación tras desconexión
    """
    id: UUID = Field(default_factory=uuid4, description="ID único del draft")
    session_id: UUID = Field(..., description="ID de la session asociada")
    content: str = Field(default="", max_length=50000, description="Contenido del draft")
    cursor_position: int = Field(default=0, ge=0, description="Posición del cursor")
    last_saved: datetime = Field(default_factory=datetime.utcnow, description="Último guardado")

    # Metadatos adicionales para recovery
    auto_saved: bool = Field(default=True, description="Si fue guardado automáticamente")
    word_count: int = Field(default=0, description="Número de palabras")
    character_count: int = Field(default=0, description="Número de caracteres")
    is_active: bool = Field(default=True, description="Si el draft está activo")

    def update_content(self, new_content: str, cursor_pos: int = 0) -> None:
        """Actualizar contenido del draft con metadatos"""
        self.content = new_content
        self.cursor_position = cursor_pos
        self.last_saved = datetime.utcnow()
        self.word_count = len(new_content.split()) if new_content else 0
        self.character_count = len(new_content)

    def is_empty(self) -> bool:
        """Verificar si el draft está vacío"""
        return not self.content.strip()


class CommandSuggestion(BaseModel):
    """
    Modelo para sugerencias de comandos de Claude Code
    Autocompletado inteligente basado en contexto
    """
    command: str = Field(..., description="Comando sugerido")
    description: str = Field(..., description="Descripción del comando")
    category: str = Field(..., description="Categoría: A-commands, B-commands, M1-agents")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Nivel de confianza")
    usage_hint: str = Field(..., description="Hint de uso del comando")
    parameters: List[str] = Field(default_factory=list, description="Parámetros esperados")
    examples: List[str] = Field(default_factory=list, description="Ejemplos de uso")


class InputValidationResult(BaseModel):
    """
    Resultado de validación de input para comandos de Claude Code
    Validación en tiempo real con sugerencias
    """
    is_valid: bool = Field(..., description="Si el input es válido")
    validation_type: str = Field(..., description="Tipo de validación realizada")
    errors: List[str] = Field(default_factory=list, description="Errores encontrados")
    warnings: List[str] = Field(default_factory=list, description="Advertencias")
    suggestions: List[CommandSuggestion] = Field(default_factory=list, description="Sugerencias")
    corrected_input: Optional[str] = Field(default=None, description="Input corregido sugerido")


class InputAnalytics(BaseModel):
    """
    Modelo para analytics y métricas de input del usuario
    Tracking avanzado para insights de comportamiento
    """
    session_id: UUID = Field(..., description="ID de la session")

    # Métricas de tipeo
    typing_speed_wpm: float = Field(default=0.0, description="Velocidad de tipeo en WPM")
    avg_input_length: float = Field(default=0.0, description="Longitud promedio de inputs")
    total_inputs: int = Field(default=0, description="Total de inputs realizados")
    total_characters: int = Field(default=0, description="Total de caracteres escritos")

    # Métricas de comandos
    command_usage: Dict[str, int] = Field(default_factory=dict, description="Uso de comandos")
    most_used_commands: List[str] = Field(default_factory=list, description="Comandos más usados")
    command_accuracy: float = Field(default=0.0, description="Precisión en comandos")

    # Métricas de sesión
    session_duration_ms: int = Field(default=0, description="Duración de la sesión en ms")
    input_frequency_per_minute: float = Field(default=0.0, description="Frecuencia de inputs por minuto")
    pause_times: List[int] = Field(default_factory=list, description="Tiempos de pausa entre inputs")

    # Metadatos temporales
    first_input_time: Optional[datetime] = Field(default=None, description="Primer input de la sesión")
    last_input_time: Optional[datetime] = Field(default=None, description="Último input de la sesión")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Última actualización")

    def add_input_event(self, input_entry: InputHistoryEntry, typing_duration_ms: int) -> None:
        """Registrar nuevo evento de input para analytics"""
        self.total_inputs += 1
        self.total_characters += input_entry.input_length

        # Actualizar velocidad de tipeo
        if typing_duration_ms > 0:
            wpm = (input_entry.word_count / (typing_duration_ms / 1000)) * 60
            self.typing_speed_wpm = (self.typing_speed_wpm * (self.total_inputs - 1) + wpm) / self.total_inputs

        # Actualizar longitud promedio
        self.avg_input_length = self.total_characters / self.total_inputs

        # Tracking de comandos
        if input_entry.is_command and input_entry.command_type:
            self.command_usage[input_entry.command_type] = self.command_usage.get(input_entry.command_type, 0) + 1
            self._update_most_used_commands()

        # Actualizar timestamps
        if not self.first_input_time:
            self.first_input_time = input_entry.timestamp
        self.last_input_time = input_entry.timestamp
        self.last_updated = datetime.utcnow()

        # Calcular duración de sesión
        if self.first_input_time:
            duration = (input_entry.timestamp - self.first_input_time).total_seconds() * 1000
            self.session_duration_ms = int(duration)

    def _update_most_used_commands(self) -> None:
        """Actualizar lista de comandos más usados"""
        sorted_commands = sorted(self.command_usage.items(), key=lambda x: x[1], reverse=True)
        self.most_used_commands = [cmd for cmd, _ in sorted_commands[:10]]


# Request/Response models para nuevas APIs

class InputHistoryRequest(BaseModel):
    """Request para guardar entrada en el historial"""
    text: str = Field(..., min_length=1, max_length=50000)
    typing_duration_ms: Optional[int] = Field(default=None)
    cursor_position: Optional[int] = Field(default=None)


class InputHistoryResponse(BaseModel):
    """Response para historial de inputs"""
    session_id: UUID = Field(..., description="ID de la session")
    entries: List[InputHistoryEntry] = Field(..., description="Entradas del historial")
    total_count: int = Field(..., description="Total de entradas")
    has_more: bool = Field(..., description="Si hay más entradas")


class DraftSaveRequest(BaseModel):
    """Request para guardar draft"""
    content: str = Field(default="", max_length=50000)
    cursor_position: int = Field(default=0, ge=0)


class CommandValidationRequest(BaseModel):
    """Request para validar comando"""
    input_text: str = Field(..., min_length=1, max_length=1000)
    partial: bool = Field(default=False, description="Si es validación parcial (autocompletado)")


class CommandSuggestionsRequest(BaseModel):
    """Request para obtener sugerencias de comandos"""
    partial_input: str = Field(default="", max_length=100)
    limit: int = Field(default=10, ge=1, le=50)
    category_filter: Optional[str] = Field(default=None, description="Filtrar por categoría")