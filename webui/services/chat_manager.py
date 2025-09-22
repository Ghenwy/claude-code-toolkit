"""
Chat Manager Service - Enhanced message handling infrastructure
Implementa CHAT-02 features: progressive loading, threading, advanced status tracking
Siguiendo standards/fastapi.yaml y standards/python.yaml
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, AsyncGenerator, Any
from uuid import UUID, uuid4

from models.chat import (
    ChatMessage, ChatSession, ConnectionStatus, MessageStatus, MessageType,
    MessageChunk, MessageSearchResult, MessageThread, MessageStatistics,
    MessageExport, MessageSearchRequest, MessageUpdateRequest,
    # CHAT-03 Input System models
    InputHistoryEntry, InputDraft, InputAnalytics, CommandSuggestion,
    InputValidationResult, InputHistoryRequest, DraftSaveRequest,
    CommandValidationRequest, CommandSuggestionsRequest,
    # CHAT-04 Streaming models
    StreamingChunk, StreamingState, StreamingRequest, StreamingStatus,
    TypingIndicator, ConnectionState
)

# Configuración de logging
logger = logging.getLogger(__name__)


class ChatManager:
    """
    Manager principal para chat sessions y WebSocket connections
    Async patterns para I/O-bound operations
    """

    def __init__(self) -> None:
        # In-memory storage para desarrollo - TODO: implementar persistent storage
        self._sessions: Dict[UUID, ChatSession] = {}
        self._connections: Dict[UUID, ConnectionStatus] = {}
        self._active_connections: Dict[UUID, any] = {}  # WebSocket connections

        # Nuevos storages para features avanzadas
        self._message_chunks: Dict[UUID, List[MessageChunk]] = {}  # message_id -> chunks
        self._active_streams: Dict[UUID, Dict] = {}  # message_id -> stream_info
        self._export_jobs: Dict[UUID, MessageExport] = {}  # export_id -> export_job

        # CHAT-03 Input System storage
        self._input_history: Dict[UUID, List[InputHistoryEntry]] = {}  # session_id -> entries
        self._input_drafts: Dict[UUID, InputDraft] = {}  # session_id -> current_draft
        self._input_analytics: Dict[UUID, InputAnalytics] = {}  # session_id -> analytics

        # CHAT-04 Streaming infrastructure
        self._streaming_states: Dict[UUID, StreamingState] = {}  # session_id -> streaming_state
        self._active_streaming_tasks: Dict[UUID, asyncio.Task] = {}  # message_id -> streaming_task
        self._connection_states: Dict[UUID, ConnectionState] = {}  # client_id -> connection_state
        self._typing_indicators: Dict[UUID, TypingIndicator] = {}  # session_id -> typing_indicator

        # Input validator service
        from .input_validator import InputValidator
        self._input_validator = InputValidator()

    async def create_session(self) -> ChatSession:
        """Crear nueva chat session con async support"""
        session = ChatSession()
        self._sessions[session.session_id] = session
        logger.info(f"Nueva chat session creada: {session.session_id}")
        return session

    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        """Obtener session existente con validation"""
        return self._sessions.get(session_id)

    async def add_message_to_session(
        self,
        session_id: UUID,
        content: str,
        message_type: MessageType = MessageType.USER,
        metadata: Optional[dict] = None,
        thread_id: Optional[UUID] = None,
        parent_message_id: Optional[UUID] = None,
        enable_progressive_loading: bool = False,
        auto_extract_keywords: bool = True
    ) -> ChatMessage:
        """
        Enhanced añadir mensaje con advanced features
        Incluye threading, status tracking y keyword extraction
        """
        start_time = time.time()
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Crear mensaje con campos avanzados
        message = ChatMessage(
            content=content,
            message_type=message_type,
            metadata=metadata or {},
            thread_id=thread_id,
            parent_message_id=parent_message_id,
            status=MessageStatus.RECEIVED if message_type == MessageType.USER else MessageStatus.PENDING
        )

        # Auto-extraer keywords si está habilitado
        if auto_extract_keywords:
            message.extract_search_keywords()

        # Configurar progressive loading si está habilitado para mensajes largos
        if enable_progressive_loading and len(content) > 1000:
            await self._setup_progressive_loading(message)

        # Añadir al session (esto maneja threading automáticamente)
        session.add_message(message)

        # Calcular tiempo de respuesta
        processing_time = int((time.time() - start_time) * 1000)
        message.response_time_ms = processing_time

        logger.info(f"Enhanced mensaje añadido a session {session_id}: {message.id} (threading: {bool(thread_id)})")
        return message

    async def process_user_message(
        self,
        session_id: UUID,
        content: str,
        enable_progressive_loading: bool = False,
        thread_id: Optional[UUID] = None,
        enable_streaming: bool = True,
        typing_speed_wpm: float = 150.0
    ) -> ChatMessage:
        """
        Enhanced procesar mensaje con progressive loading y advanced features
        Incluye status tracking detallado y chunking support
        """
        start_time = time.time()

        # Añadir mensaje del usuario con enhanced features
        user_message = await self.add_message_to_session(
            session_id=session_id,
            content=content,
            message_type=MessageType.USER,
            thread_id=thread_id,
            enable_progressive_loading=enable_progressive_loading
        )

        # Update status: user message received
        await self.update_message_status(user_message.id, MessageStatus.COMPLETED)

        # Simular processing async con status updates
        await self.update_message_status(user_message.id, MessageStatus.PROCESSING)
        await asyncio.sleep(0.1)  # Simulate async processing

        # Crear respuesta del assistant con enhanced processing
        response_content = self._generate_enhanced_response(content)

        # Si streaming está habilitado, usar nueva infraestructura
        if enable_streaming:
            assistant_response = await self.start_message_streaming(
                session_id=session_id,
                message_content=response_content,
                typing_speed_wpm=typing_speed_wpm,
                include_thinking_time=True
            )
            # Configurar metadata y threading
            assistant_response.metadata = {"processed_at": datetime.utcnow().isoformat(), "user_message_id": str(user_message.id)}
            assistant_response.thread_id = thread_id or user_message.thread_id
            assistant_response.parent_message_id = user_message.id
        else:
            # Crear mensaje de respuesta tradicional
            assistant_response = await self.add_message_to_session(
                session_id=session_id,
                content=response_content,
                message_type=MessageType.ASSISTANT,
                metadata={"processed_at": datetime.utcnow().isoformat(), "user_message_id": str(user_message.id)},
                thread_id=thread_id or user_message.thread_id,
                parent_message_id=user_message.id,
                enable_progressive_loading=enable_progressive_loading
            )

            # Progressive loading para respuestas largas
            if enable_progressive_loading and len(response_content) > 1000:
                await self._stream_message_chunks(assistant_response)
            else:
                await self.update_message_status(assistant_response.id, MessageStatus.COMPLETED)

        # Calcular tiempo total de procesamiento
        total_time = int((time.time() - start_time) * 1000)
        assistant_response.response_time_ms = total_time

        logger.info(f"Enhanced mensaje procesado para session {session_id} (tiempo: {total_time}ms)")
        return assistant_response

    def _generate_enhanced_response(self, user_content: str) -> str:
        """
        Generar respuesta enhanced basada en el contenido del usuario
        Simula diferentes tipos de respuestas según el contenido
        """
        content_lower = user_content.lower()

        if "hola" in content_lower or "hello" in content_lower:
            return f"¡Hola! He recibido tu mensaje: '{user_content}'. ¿En qué puedo ayudarte hoy? Puedo responder preguntas, generar código, explicar conceptos técnicos y mucho más."

        elif "ayuda" in content_lower or "help" in content_lower:
            return """¡Por supuesto! Aquí tienes algunas formas en las que puedo ayudarte:

📝 **Generación de código**: Puedo escribir código en múltiples lenguajes
🔧 **Debugging**: Te ayudo a encontrar y corregir errores
📚 **Explicaciones técnicas**: Conceptos de programación, arquitectura, etc.
⚡ **Optimización**: Mejorar rendimiento y calidad del código
🔍 **Code review**: Revisar y sugerir mejoras en tu código

¿Hay algo específico en lo que te gustaría que te ayude?"""

        elif "código" in content_lower or "code" in content_lower:
            return f"""He detectado que preguntas sobre código. Aquí tienes un ejemplo basado en tu mensaje:

```python
# Ejemplo basado en: {user_content}
def process_user_request(request: str) -> str:
    \"\"\"
    Procesa una solicitud del usuario y genera una respuesta contextual
    \"\"\"
    if "código" in request.lower():
        return generate_code_example(request)
    return f"Procesando: {request}"

def generate_code_example(context: str) -> str:
    return f"Código generado para: {context}"
```

¿Te gustaría que desarrolle más algún aspecto específico?"""

        elif len(user_content) > 500:
            return f"""Has enviado un mensaje largo y detallado. He procesado todo el contenido:

**Resumen de tu mensaje:**
- Longitud: {len(user_content)} caracteres
- Palabras clave detectadas: {', '.join(user_content.split()[:5])}...

**Mi respuesta:**
Entiendo tu consulta detallada. Para darte la mejor respuesta posible, podría necesitar que me especifiques:

1. ¿Cuál es el objetivo principal de tu consulta?
2. ¿Hay algún aspecto técnico específico que quieres que profundice?
3. ¿Necesitas ejemplos prácticos o explicaciones teóricas?

Mientras tanto, aquí tienes una respuesta inicial basada en tu mensaje: {user_content[:200]}...

¿Te gustaría que me enfoque en algún punto particular?"""

        else:
            return f"""He procesado tu mensaje: "{user_content}"

**Análisis del mensaje:**
- Tipo: Consulta general
- Longitud: {len(user_content)} caracteres
- Timestamp: {datetime.utcnow().strftime('%H:%M:%S UTC')}

**Mi respuesta:**
Entiendo tu mensaje. Si necesitas ayuda específica con programación, diseño de sistemas, o cualquier tema técnico, estaré encantado de ayudarte.

¿Hay algo más específico en lo que pueda asistirte?"""

    async def register_connection(self, websocket) -> UUID:
        """Registrar nueva WebSocket connection"""
        client_id = uuid4()
        connection_status = ConnectionStatus(client_id=client_id)

        self._connections[client_id] = connection_status
        self._active_connections[client_id] = websocket

        logger.info(f"WebSocket connection registrada: {client_id}")
        return client_id

    async def unregister_connection(self, client_id: UUID) -> None:
        """Unregister WebSocket connection con cleanup"""
        if client_id in self._connections:
            self._connections[client_id].is_active = False
            del self._connections[client_id]

        if client_id in self._active_connections:
            del self._active_connections[client_id]

        logger.info(f"WebSocket connection eliminada: {client_id}")

    async def broadcast_message(self, message: ChatMessage, exclude_client: Optional[UUID] = None) -> None:
        """
        Broadcast message a todas las active connections
        Async pattern para concurrent operations
        """
        if not self._active_connections:
            return

        # Crear tasks para concurrent broadcasting
        tasks = []
        for client_id, websocket in self._active_connections.items():
            if exclude_client and client_id == exclude_client:
                continue

            task = asyncio.create_task(
                self._send_message_to_client(websocket, message)
            )
            tasks.append(task)

        # Execute all broadcasts concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_message_to_client(self, websocket, message: ChatMessage) -> None:
        """
        Send message a specific client con error handling
        Private method para internal use
        """
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Error enviando mensaje a client: {e}")

    async def get_session_history(
        self,
        session_id: UUID,
        limit: int = 50
    ) -> list[ChatMessage]:
        """Obtener historial de session con limit"""
        session = await self.get_session(session_id)
        if not session:
            return []

        return session.get_recent_messages(limit)

    async def heartbeat(self, client_id: UUID) -> bool:
        """Update heartbeat para connection monitoring"""
        if client_id in self._connections:
            self._connections[client_id].last_heartbeat = datetime.utcnow()
            return True
        return False

    def get_active_connections_count(self) -> int:
        """Obtener número de connections activas"""
        return len(self._active_connections)

    def get_sessions_count(self) -> int:
        """Obtener número de sessions activas"""
        return len(self._sessions)

    # ========================================
    # NUEVOS MÉTODOS PARA CHAT-02 FEATURES
    # ========================================

    async def update_message_status(self, message_id: UUID, new_status: MessageStatus, metadata: Optional[Dict] = None) -> bool:
        """
        Actualizar status de un mensaje específico
        Strategic status tracking para UI updates
        """
        for session in self._sessions.values():
            for message in session.messages:
                if message.id == message_id:
                    old_status = message.status
                    message.status = new_status

                    # Añadir metadata si se proporciona
                    if metadata:
                        if message.metadata:
                            message.metadata.update(metadata)
                        else:
                            message.metadata = metadata

                    logger.info(f"Message status updated: {message_id} ({old_status} → {new_status})")
                    return True

        logger.warning(f"Message not found for status update: {message_id}")
        return False

    async def _setup_progressive_loading(self, message: ChatMessage) -> None:
        """
        Configurar progressive loading para mensajes largos
        Prepara chunks para streaming
        """
        content = message.content
        chunk_size = 200  # Caracteres por chunk
        total_chunks = (len(content) + chunk_size - 1) // chunk_size

        chunks = []
        for i in range(total_chunks):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(content))
            chunk_content = content[start_idx:end_idx]

            chunk = MessageChunk(
                message_id=message.id,
                chunk_index=i,
                total_chunks=total_chunks,
                content=chunk_content,
                is_final=(i == total_chunks - 1)
            )
            chunks.append(chunk)

        self._message_chunks[message.id] = chunks
        message.set_chunk_info(0, total_chunks, False)
        logger.info(f"Progressive loading setup: {total_chunks} chunks para message {message.id}")

    async def _stream_message_chunks(self, message: ChatMessage) -> None:
        """
        Simular streaming de chunks para progressive loading
        En implementación real, esto sería llamado por el LLM
        """
        if message.id not in self._message_chunks:
            return

        chunks = self._message_chunks[message.id]
        message.status = MessageStatus.STREAMING

        for i, chunk in enumerate(chunks):
            # Simular delay entre chunks
            await asyncio.sleep(0.1)

            # Update chunk info
            message.set_chunk_info(i, len(chunks), chunk.is_final)

            # Log progreso
            logger.info(f"Streaming chunk {i+1}/{len(chunks)} para message {message.id}")

            # Si es el último chunk, marcar como completado
            if chunk.is_final:
                message.status = MessageStatus.COMPLETED
                logger.info(f"Progressive loading completado para message {message.id}")

    async def get_message_chunks(self, message_id: UUID) -> List[MessageChunk]:
        """Obtener chunks de un mensaje específico"""
        return self._message_chunks.get(message_id, [])

    async def update_message_content(self, request: MessageUpdateRequest) -> Optional[ChatMessage]:
        """
        Actualizar contenido de un mensaje existente
        Incluye edit history tracking
        """
        for session in self._sessions.values():
            for message in session.messages:
                if message.id == request.message_id:
                    # Guardar contenido anterior
                    old_content = message.content

                    # Actualizar contenido si se proporciona
                    if request.new_content:
                        message.content = request.new_content
                        message.add_edit_record(old_content, request.edit_reason)
                        # Re-extraer keywords
                        message.extract_search_keywords()

                    # Toggle bookmark si se solicita
                    if request.toggle_bookmark is not None:
                        message.toggle_bookmark()

                    logger.info(f"Message updated: {request.message_id}")
                    return message

        logger.warning(f"Message not found for update: {request.message_id}")
        return None

    async def search_messages(self, request: MessageSearchRequest) -> List[MessageSearchResult]:
        """
        Búsqueda avanzada de mensajes con filtros
        Implementa scoring y ranking de resultados
        """
        results = []
        sessions_to_search = []

        # Determinar sessions a buscar
        if request.session_id:
            session = await self.get_session(request.session_id)
            if session:
                sessions_to_search = [session]
        else:
            sessions_to_search = list(self._sessions.values())

        # Buscar en cada session
        for session in sessions_to_search:
            session_results = session.search_messages(request.query)

            # Aplicar filtros adicionales
            filtered_results = []
            for result in session_results:
                message = result.message

                # Filtro por tipo de mensaje
                if request.message_types and message.message_type not in request.message_types:
                    continue

                # Filtro por fecha
                if request.date_from and message.timestamp < request.date_from:
                    continue
                if request.date_to and message.timestamp > request.date_to:
                    continue

                # Filtro por bookmarks
                if request.bookmarked_only and not message.is_bookmarked:
                    continue

                filtered_results.append(result)

            results.extend(filtered_results)

        # Ordenar por relevancia y aplicar límite
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:request.limit]

    async def get_session_statistics(self, session_id: UUID) -> Optional[MessageStatistics]:
        """Obtener estadísticas de una session específica"""
        session = await self.get_session(session_id)
        if not session:
            return None

        # Forzar actualización de estadísticas
        session._update_statistics()
        return session.statistics

    async def get_message_threads(self, session_id: UUID) -> List[MessageThread]:
        """Obtener todos los threads de una session"""
        session = await self.get_session(session_id)
        if not session:
            return []

        return session.threads

    async def get_thread_messages(self, session_id: UUID, thread_id: UUID) -> List[ChatMessage]:
        """Obtener mensajes de un thread específico"""
        session = await self.get_session(session_id)
        if not session:
            return []

        return session.get_messages_by_thread(thread_id)

    async def get_bookmarked_messages(self, session_id: UUID) -> List[ChatMessage]:
        """Obtener mensajes bookmarked de una session"""
        session = await self.get_session(session_id)
        if not session:
            return []

        return session.get_bookmarked_messages()

    async def export_session_messages(self, session_id: UUID, format_type: str = "json", include_metadata: bool = True, bookmarks_only: bool = False) -> Optional[MessageExport]:
        """
        Preparar export de mensajes de una session
        En implementación real, generaría archivo y lo devolvería
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        export_job = MessageExport(
            session_id=session_id,
            format_type=format_type,
            include_metadata=include_metadata,
            include_bookmarks_only=bookmarks_only
        )

        # Calcular tamaño estimado
        messages_to_export = session.get_bookmarked_messages() if bookmarks_only else session.messages
        estimated_size = sum(len(msg.content) for msg in messages_to_export)
        export_job.file_size_bytes = estimated_size

        self._export_jobs[export_job.export_id] = export_job
        logger.info(f"Export job created: {export_job.export_id} para session {session_id}")

        return export_job

    async def get_export_status(self, export_id: UUID) -> Optional[MessageExport]:
        """Obtener status de un job de export"""
        return self._export_jobs.get(export_id)

    async def get_enhanced_session_history(
        self,
        session_id: UUID,
        page: int = 1,
        page_size: int = 50,
        include_threads: bool = True,
        include_statistics: bool = True
    ) -> Optional[Dict]:
        """
        Obtener historial enhanced con paginación y metadata adicional
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        # Calcular paginación
        total_messages = len(session.messages)
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_messages)

        paginated_messages = session.messages[start_idx:end_idx]
        has_more = end_idx < total_messages

        result = {
            "session_id": session_id,
            "messages": [msg.model_dump() for msg in paginated_messages],
            "total_count": total_messages,
            "page": page,
            "page_size": page_size,
            "has_more": has_more
        }

        # Incluir threads si se solicita
        if include_threads:
            result["threads"] = [thread.model_dump() for thread in session.threads]

        # Incluir estadísticas si se solicita
        if include_statistics:
            session._update_statistics()
            result["statistics"] = session.statistics.model_dump() if session.statistics else None

        return result

    # ========================================
    # NUEVOS MÉTODOS PARA CHAT-03: INPUT SYSTEM
    # ========================================

    async def save_input_to_history(
        self,
        session_id: UUID,
        request: InputHistoryRequest
    ) -> InputHistoryEntry:
        """
        Guardar entrada de input al historial con enrichment
        Strategic input tracking para analytics y recovery
        """
        # Crear entrada de historial
        entry = InputHistoryEntry(
            session_id=session_id,
            text=request.text,
            typing_duration_ms=request.typing_duration_ms,
            cursor_position=request.cursor_position
        )

        # Enriquecer entrada con detección de comandos
        enriched_entry = await self._input_validator.enhance_input_history_entry(entry)

        # Inicializar historial si no existe
        if session_id not in self._input_history:
            self._input_history[session_id] = []

        # Añadir al historial
        self._input_history[session_id].append(enriched_entry)

        # Actualizar analytics
        await self._update_input_analytics(session_id, enriched_entry, request.typing_duration_ms or 0)

        logger.info(f"Input saved to history: session {session_id}, command: {enriched_entry.is_command}")
        return enriched_entry

    async def get_input_history(
        self,
        session_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        Obtener historial de inputs con paginación
        Async pattern para large history retrieval
        """
        if session_id not in self._input_history:
            return {
                "session_id": session_id,
                "entries": [],
                "total_count": 0,
                "has_more": False
            }

        # Obtener entries del historial (orden cronológico inverso)
        all_entries = list(reversed(self._input_history[session_id]))
        total_count = len(all_entries)

        # Aplicar paginación
        start_idx = offset
        end_idx = offset + limit
        paginated_entries = all_entries[start_idx:end_idx]

        return {
            "session_id": session_id,
            "entries": paginated_entries,
            "total_count": total_count,
            "has_more": end_idx < total_count
        }

    async def save_draft(
        self,
        session_id: UUID,
        request: DraftSaveRequest
    ) -> InputDraft:
        """
        Guardar draft con auto-save functionality
        Strategic persistence para recovery tras desconexión
        """
        # Obtener draft existente o crear nuevo
        if session_id in self._input_drafts:
            draft = self._input_drafts[session_id]
            draft.update_content(request.content, request.cursor_position)
        else:
            draft = InputDraft(
                session_id=session_id,
                content=request.content,
                cursor_position=request.cursor_position
            )
            self._input_drafts[session_id] = draft

        logger.info(f"Draft saved: session {session_id}, length: {len(request.content)}")
        return draft

    async def get_draft(self, session_id: UUID) -> Optional[InputDraft]:
        """
        Recuperar draft para una session
        Recovery mechanism tras reconnection
        """
        draft = self._input_drafts.get(session_id)

        # Filtrar drafts inactivos o muy antiguos
        if draft and not draft.is_active:
            return None

        # Auto-cleanup de drafts antiguos (más de 24 horas)
        if draft:
            time_diff = datetime.utcnow() - draft.last_saved
            if time_diff.total_seconds() > 86400:  # 24 horas
                self._input_drafts.pop(session_id, None)
                return None

        return draft

    async def clear_draft(self, session_id: UUID) -> bool:
        """Limpiar draft de una session"""
        if session_id in self._input_drafts:
            del self._input_drafts[session_id]
            logger.info(f"Draft cleared for session {session_id}")
            return True
        return False

    async def validate_input(self, request: CommandValidationRequest) -> InputValidationResult:
        """
        Validar input para comandos de Claude Code
        Real-time validation con suggestions
        """
        return await self._input_validator.validate_input(
            request.input_text,
            request.partial
        )

    async def get_command_suggestions(
        self,
        request: CommandSuggestionsRequest
    ) -> List[CommandSuggestion]:
        """
        Obtener sugerencias de comandos para autocompletado
        Strategic suggestion engine para UX enhancement
        """
        return await self._input_validator.get_command_suggestions(
            request.partial_input,
            request.limit,
            request.category_filter
        )

    async def get_input_analytics(self, session_id: UUID) -> Optional[InputAnalytics]:
        """
        Obtener analytics de input para una session
        Insights de comportamiento y métricas
        """
        analytics = self._input_analytics.get(session_id)

        # Actualizar métricas en tiempo real
        if analytics and session_id in self._input_history:
            self._refresh_analytics_metrics(analytics, self._input_history[session_id])

        return analytics

    async def _update_input_analytics(
        self,
        session_id: UUID,
        entry: InputHistoryEntry,
        typing_duration_ms: int
    ) -> None:
        """
        Actualizar analytics con nuevo input event
        Private method para internal analytics tracking
        """
        # Inicializar analytics si no existe
        if session_id not in self._input_analytics:
            self._input_analytics[session_id] = InputAnalytics(session_id=session_id)

        analytics = self._input_analytics[session_id]
        analytics.add_input_event(entry, typing_duration_ms)

        logger.debug(f"Analytics updated: session {session_id}, total inputs: {analytics.total_inputs}")

    def _refresh_analytics_metrics(
        self,
        analytics: InputAnalytics,
        history_entries: List[InputHistoryEntry]
    ) -> None:
        """
        Refrescar métricas de analytics basadas en historial completo
        Performance optimizada para large datasets
        """
        if not history_entries:
            return

        # Calcular frecuencia de inputs
        if analytics.first_input_time and analytics.last_input_time:
            duration_minutes = (analytics.last_input_time - analytics.first_input_time).total_seconds() / 60
            if duration_minutes > 0:
                analytics.input_frequency_per_minute = analytics.total_inputs / duration_minutes

        # Calcular precisión de comandos
        command_entries = [e for e in history_entries if e.is_command]
        valid_commands = [e for e in command_entries if e.validation_status == "valid"]
        if command_entries:
            analytics.command_accuracy = len(valid_commands) / len(command_entries)

    async def get_session_input_summary(self, session_id: UUID) -> Dict:
        """
        Obtener resumen completo de input para una session
        Combined view de history, drafts y analytics
        """
        summary = {
            "session_id": session_id,
            "has_history": session_id in self._input_history,
            "has_draft": session_id in self._input_drafts,
            "has_analytics": session_id in self._input_analytics
        }

        # Añadir conteos básicos
        if summary["has_history"]:
            history_count = len(self._input_history[session_id])
            command_count = len([e for e in self._input_history[session_id] if e.is_command])
            summary.update({
                "total_inputs": history_count,
                "command_inputs": command_count,
                "regular_inputs": history_count - command_count
            })

        # Añadir info de draft
        if summary["has_draft"]:
            draft = self._input_drafts[session_id]
            summary.update({
                "draft_length": len(draft.content),
                "draft_last_saved": draft.last_saved,
                "draft_is_empty": draft.is_empty()
            })

        # Añadir métricas clave de analytics
        if summary["has_analytics"]:
            analytics = self._input_analytics[session_id]
            summary.update({
                "typing_speed_wpm": analytics.typing_speed_wpm,
                "avg_input_length": analytics.avg_input_length,
                "most_used_commands": analytics.most_used_commands[:3]
            })

        return summary

    async def cleanup_session_input_data(self, session_id: UUID) -> Dict[str, bool]:
        """
        Cleanup de datos de input para una session
        Strategic cleanup para memory management
        """
        cleanup_results = {
            "history_cleared": False,
            "draft_cleared": False,
            "analytics_cleared": False
        }

        # Limpiar historial
        if session_id in self._input_history:
            del self._input_history[session_id]
            cleanup_results["history_cleared"] = True

        # Limpiar draft
        if session_id in self._input_drafts:
            del self._input_drafts[session_id]
            cleanup_results["draft_cleared"] = True

        # Limpiar analytics
        if session_id in self._input_analytics:
            del self._input_analytics[session_id]
            cleanup_results["analytics_cleared"] = True

        logger.info(f"Input data cleanup completed for session {session_id}: {cleanup_results}")
        return cleanup_results

    # ========================================
    # CHAT-04: STREAMING INFRASTRUCTURE
    # ========================================

    async def start_message_streaming(
        self,
        session_id: UUID,
        message_content: str,
        typing_speed_wpm: float = 150.0,
        include_thinking_time: bool = True
    ) -> ChatMessage:
        """
        Iniciar streaming de mensaje caracter por caracter
        Simula escritura humana con Claude Code terminal style
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Crear mensaje para streaming con contenido inicial
        message = ChatMessage(
            content="",  # Contenido vacío permitido para streaming
            message_type=MessageType.ASSISTANT,
            status=MessageStatus.STREAMING
        )

        # Añadir al session inmediatamente
        session.add_message(message)

        # Configurar estado de streaming
        streaming_state = StreamingState(
            session_id=session_id,
            message_id=message.id,
            status=StreamingStatus.THINKING,
            total_characters=len(message_content),
            words_per_minute=typing_speed_wpm,
            is_active=True
        )
        self._streaming_states[session_id] = streaming_state

        # Mostrar typing indicator si está habilitado el thinking time
        if include_thinking_time:
            await self._set_typing_indicator(session_id, "Claude está pensando...", 2000)
            await asyncio.sleep(1.5)  # Tiempo de pensamiento simulado

        # Iniciar task de streaming
        streaming_task = asyncio.create_task(
            self._stream_message_content(message, message_content, typing_speed_wpm, session_id)
        )
        self._active_streaming_tasks[message.id] = streaming_task

        logger.info(f"Streaming iniciado: session {session_id}, message {message.id}")
        return message

    async def _stream_message_content(
        self,
        message: ChatMessage,
        full_content: str,
        typing_speed_wpm: float,
        session_id: UUID
    ) -> None:
        """
        Streamificar contenido caracter por caracter
        Implementa async generator patterns para smooth delivery
        """
        streaming_state = None
        try:
            # Calcular delay entre caracteres basado en WPM
            chars_per_second = (typing_speed_wpm * 5) / 60  # ~5 chars por palabra
            delay_per_char = 1.0 / chars_per_second

            # Actualizar estado
            streaming_state = self._streaming_states.get(session_id)
            if streaming_state:
                streaming_state.status = StreamingStatus.STREAMING
                streaming_state.message_id = message.id

            # Stream caracter por caracter
            current_content = ""
            for i, char in enumerate(full_content):
                current_content += char
                message.content = current_content

                # Crear chunk para este caracter
                chunk = StreamingChunk(
                    message_id=message.id,
                    session_id=session_id,
                    content=char,
                    position=i,
                    is_final=(i == len(full_content) - 1),
                    status=StreamingStatus.STREAMING if i < len(full_content) - 1 else StreamingStatus.COMPLETE
                )

                # Broadcast chunk a clients conectados
                await self._broadcast_streaming_chunk(chunk)

                # Actualizar estado de streaming
                if streaming_state:
                    streaming_state.characters_sent = i + 1
                    streaming_state.last_chunk_time = datetime.utcnow()

                # Delay entre caracteres con variación natural
                natural_delay = delay_per_char * (0.8 + 0.4 * asyncio.get_event_loop().time() % 1)
                await asyncio.sleep(natural_delay)

            # Finalizar streaming
            message.status = MessageStatus.COMPLETED
            if streaming_state:
                streaming_state.status = StreamingStatus.COMPLETE
                streaming_state.is_active = False

            logger.info(f"Streaming completado: message {message.id}, {len(full_content)} caracteres")

        except asyncio.CancelledError:
            logger.info(f"Streaming cancelado: message {message.id}")
            message.status = MessageStatus.FAILED
            if streaming_state:
                streaming_state.status = StreamingStatus.ERROR
                streaming_state.is_active = False
        except Exception as e:
            logger.error(f"Error durante streaming: {e}")
            message.status = MessageStatus.FAILED
            if streaming_state:
                streaming_state.status = StreamingStatus.ERROR
                streaming_state.is_active = False
        finally:
            # Cleanup
            self._active_streaming_tasks.pop(message.id, None)
            await self._clear_typing_indicator(session_id)

    async def _broadcast_streaming_chunk(self, chunk: StreamingChunk) -> None:
        """
        Broadcast streaming chunk a todos los clients conectados
        Async pattern para concurrent delivery
        """
        if not self._active_connections:
            return

        # Crear data para broadcast
        chunk_data = {
            "type": "streaming_chunk",
            "data": chunk.model_dump()
        }

        # Crear tasks para concurrent broadcasting
        tasks = []
        for client_id, websocket in self._active_connections.items():
            # Verificar si el client está suscrito a esta session
            connection_state = self._connection_states.get(client_id)
            if connection_state and connection_state.session_id == chunk.session_id:
                task = asyncio.create_task(
                    self._send_chunk_to_client(websocket, chunk_data)
                )
                tasks.append(task)

        # Execute all broadcasts concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_chunk_to_client(self, websocket, chunk_data: dict) -> None:
        """
        Enviar chunk a specific client con error handling
        Private method para internal streaming
        """
        try:
            import json
            await websocket.send_text(json.dumps(chunk_data))
        except Exception as e:
            logger.error(f"Error enviando chunk a client: {e}")

    async def _set_typing_indicator(
        self,
        session_id: UUID,
        message: str = "Claude está escribiendo...",
        duration_ms: Optional[int] = None
    ) -> None:
        """
        Mostrar typing indicator para UX enhancement
        """
        indicator = TypingIndicator(
            session_id=session_id,
            is_typing=True,
            message=message,
            duration_ms=duration_ms
        )
        self._typing_indicators[session_id] = indicator

        # Broadcast typing indicator
        await self._broadcast_typing_indicator(indicator)
        logger.debug(f"Typing indicator set: {session_id} - {message}")

    async def _clear_typing_indicator(self, session_id: UUID) -> None:
        """Limpiar typing indicator"""
        if session_id in self._typing_indicators:
            indicator = self._typing_indicators[session_id]
            indicator.is_typing = False
            await self._broadcast_typing_indicator(indicator)
            del self._typing_indicators[session_id]
            logger.debug(f"Typing indicator cleared: {session_id}")

    async def _broadcast_typing_indicator(self, indicator: TypingIndicator) -> None:
        """Broadcast typing indicator a clients conectados"""
        if not self._active_connections:
            return

        # Crear data para broadcast
        indicator_data = {
            "type": "typing_indicator",
            "data": indicator.model_dump()
        }

        # Broadcast a clients de esta session
        tasks = []
        for client_id, websocket in self._active_connections.items():
            connection_state = self._connection_states.get(client_id)
            if connection_state and connection_state.session_id == indicator.session_id:
                task = asyncio.create_task(
                    self._send_chunk_to_client(websocket, indicator_data)
                )
                tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def register_streaming_connection(
        self,
        websocket,
        session_id: UUID,
        connection_type: str = "websocket"
    ) -> UUID:
        """
        Registrar connection para streaming con enhanced tracking
        """
        client_id = uuid4()

        # Crear enhanced connection status
        connection_state = ConnectionState(
            client_id=client_id,
            session_id=session_id,
            connection_type=connection_type,
            supports_streaming=True
        )

        # Registrar en ambos sistemas
        self._connection_states[client_id] = connection_state
        self._active_connections[client_id] = websocket

        # Legacy connection status
        legacy_status = ConnectionStatus(client_id=client_id)
        self._connections[client_id] = legacy_status

        # Añadir a streaming state si existe
        if session_id in self._streaming_states:
            streaming_state = self._streaming_states[session_id]
            if client_id not in streaming_state.connected_clients:
                streaming_state.connected_clients.append(client_id)

        logger.info(f"Streaming connection registered: {client_id} -> session {session_id}")
        return client_id

    async def unregister_streaming_connection(self, client_id: UUID) -> None:
        """
        Unregister connection con streaming cleanup
        """
        # Obtener connection state antes de cleanup
        connection_state = self._connection_states.get(client_id)
        session_id = connection_state.session_id if connection_state else None

        # Legacy cleanup
        await self.unregister_connection(client_id)

        # Enhanced cleanup
        self._connection_states.pop(client_id, None)

        # Remover de streaming state
        if session_id and session_id in self._streaming_states:
            streaming_state = self._streaming_states[session_id]
            if client_id in streaming_state.connected_clients:
                streaming_state.connected_clients.remove(client_id)

        logger.info(f"Streaming connection unregistered: {client_id}")

    async def get_streaming_state(self, session_id: UUID) -> Optional[StreamingState]:
        """Obtener estado actual de streaming para una session"""
        return self._streaming_states.get(session_id)

    async def cancel_streaming(self, session_id: UUID) -> bool:
        """
        Cancelar streaming activo para una session
        """
        streaming_state = self._streaming_states.get(session_id)
        if not streaming_state or not streaming_state.is_active:
            return False

        # Cancelar task de streaming
        if streaming_state.message_id and streaming_state.message_id in self._active_streaming_tasks:
            task = self._active_streaming_tasks[streaming_state.message_id]
            task.cancel()

        # Actualizar estado
        streaming_state.status = StreamingStatus.ERROR
        streaming_state.is_active = False

        # Limpiar typing indicator
        await self._clear_typing_indicator(session_id)

        logger.info(f"Streaming cancelled for session {session_id}")
        return True

    async def get_active_streaming_sessions(self) -> List[UUID]:
        """Obtener lista de sessions con streaming activo"""
        return [
            session_id for session_id, state in self._streaming_states.items()
            if state.is_active
        ]

    async def cleanup_streaming_session(self, session_id: UUID) -> Dict[str, bool]:
        """
        Cleanup completo de datos de streaming para una session
        """
        cleanup_results = {
            "streaming_state_cleared": False,
            "typing_indicator_cleared": False,
            "active_tasks_cancelled": False
        }

        # Cancelar streaming activo
        if await self.cancel_streaming(session_id):
            cleanup_results["active_tasks_cancelled"] = True

        # Limpiar streaming state
        if session_id in self._streaming_states:
            del self._streaming_states[session_id]
            cleanup_results["streaming_state_cleared"] = True

        # Limpiar typing indicator
        if session_id in self._typing_indicators:
            del self._typing_indicators[session_id]
            cleanup_results["typing_indicator_cleared"] = True

        logger.info(f"Streaming cleanup completed for session {session_id}: {cleanup_results}")
        return cleanup_results

    # ========================================
    # CONNECTION MANAGEMENT & AUTO-RECONNECTION
    # ========================================

    async def update_connection_quality(
        self,
        client_id: UUID,
        latency_ms: float,
        success_rate: float = 1.0
    ) -> None:
        """
        Actualizar métricas de calidad de conexión
        Para monitoring y auto-reconnection logic
        """
        connection_state = self._connection_states.get(client_id)
        if not connection_state:
            return

        # Actualizar latencia
        connection_state.latency_ms = latency_ms
        connection_state.last_activity = datetime.utcnow()

        # Calcular quality score basado en latencia y success rate
        # Quality score: 1.0 = perfecto, 0.0 = muy malo
        latency_score = max(0.0, 1.0 - (latency_ms / 2000.0))  # 2000ms = score 0
        connection_state.quality_score = (latency_score + success_rate) / 2.0

        logger.debug(f"Connection quality updated: {client_id} - latency: {latency_ms}ms, score: {connection_state.quality_score:.2f}")

    async def check_connection_health(self, client_id: UUID) -> Dict[str, Any]:
        """
        Verificar salud de una conexión específica
        Retorna métricas y recomendaciones
        """
        connection_state = self._connection_states.get(client_id)
        if not connection_state:
            return {"error": "Connection not found", "healthy": False}

        # Calcular tiempo sin actividad
        time_since_activity = (datetime.utcnow() - connection_state.last_activity).total_seconds()

        # Determinar salud basada en múltiples factores
        is_healthy = (
            connection_state.is_active and
            connection_state.quality_score > 0.3 and
            time_since_activity < 300  # 5 minutos
        )

        health_info = {
            "client_id": str(client_id),
            "is_healthy": is_healthy,
            "quality_score": connection_state.quality_score,
            "latency_ms": connection_state.latency_ms,
            "time_since_activity_seconds": int(time_since_activity),
            "connection_type": connection_state.connection_type,
            "supports_streaming": connection_state.supports_streaming,
            "reconnect_count": connection_state.reconnect_count,
            "connected_duration_seconds": int((datetime.utcnow() - connection_state.connected_at).total_seconds())
        }

        # Añadir recomendaciones
        recommendations = []
        if connection_state.quality_score < 0.5:
            recommendations.append("Consider reconnecting due to poor quality")
        if time_since_activity > 60:
            recommendations.append("Connection appears idle")
        if connection_state.reconnect_count > 3:
            recommendations.append("High reconnection count - check network stability")

        health_info["recommendations"] = recommendations
        return health_info

    async def handle_connection_drop(
        self,
        client_id: UUID,
        reason: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Manejar desconexión con cleanup graceful
        Prepara datos para auto-reconnection
        """
        connection_state = self._connection_states.get(client_id)
        if not connection_state:
            return {"error": "Connection not found"}

        session_id = connection_state.session_id

        # Marcar como inactiva
        connection_state.is_active = False

        # Crear info para reconnection
        reconnection_info = {
            "client_id": str(client_id),
            "session_id": str(session_id) if session_id else None,
            "connection_type": connection_state.connection_type,
            "disconnect_reason": reason,
            "disconnect_time": datetime.utcnow().isoformat(),
            "was_streaming": session_id in self._streaming_states if session_id else False,
            "connection_duration_seconds": int((datetime.utcnow() - connection_state.connected_at).total_seconds()),
            "quality_score_at_disconnect": connection_state.quality_score
        }

        # Si había streaming activo, pausarlo (no cancelarlo)
        if session_id and session_id in self._streaming_states:
            streaming_state = self._streaming_states[session_id]
            if streaming_state.is_active:
                streaming_state.status = StreamingStatus.PAUSED
                await self._set_typing_indicator(session_id, "Conexión perdida, reintentando...", None)
                reconnection_info["streaming_paused"] = True

        # Cleanup but keep state for potential reconnection
        await self.unregister_streaming_connection(client_id)

        logger.info(f"Connection dropped handled: {client_id} - reason: {reason}")
        return reconnection_info

    async def attempt_reconnection(
        self,
        websocket,
        session_id: UUID,
        previous_client_id: Optional[UUID] = None,
        connection_type: str = "websocket"
    ) -> Dict[str, Any]:
        """
        Intentar reconexión con recovery de estado
        """
        try:
            # Registrar nueva conexión
            new_client_id = await self.register_streaming_connection(
                websocket, session_id, connection_type
            )

            # Si había connection anterior, incrementar contador
            if previous_client_id and previous_client_id in self._connection_states:
                old_state = self._connection_states[previous_client_id]
                new_state = self._connection_states[new_client_id]
                new_state.reconnect_count = old_state.reconnect_count + 1

            # Verificar si hay streaming pausado para resumir
            streaming_resumed = False
            if session_id in self._streaming_states:
                streaming_state = self._streaming_states[session_id]
                if streaming_state.status == StreamingStatus.PAUSED:
                    streaming_state.status = StreamingStatus.STREAMING
                    streaming_state.connected_clients.append(new_client_id)
                    await self._clear_typing_indicator(session_id)
                    streaming_resumed = True

            reconnection_result = {
                "success": True,
                "new_client_id": str(new_client_id),
                "session_id": str(session_id),
                "streaming_resumed": streaming_resumed,
                "reconnection_time": datetime.utcnow().isoformat(),
                "reconnect_count": self._connection_states[new_client_id].reconnect_count
            }

            logger.info(f"Reconnection successful: {new_client_id} -> session {session_id}")
            return reconnection_result

        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": str(session_id)
            }

    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas generales de conexiones
        Para monitoring y debugging
        """
        total_connections = len(self._connection_states)
        active_connections = sum(1 for conn in self._connection_states.values() if conn.is_active)
        websocket_connections = sum(1 for conn in self._connection_states.values() if conn.connection_type == "websocket")
        sse_connections = sum(1 for conn in self._connection_states.values() if conn.connection_type == "sse")

        # Calcular métricas de calidad
        quality_scores = [conn.quality_score for conn in self._connection_states.values() if conn.is_active]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        # Latencias
        latencies = [conn.latency_ms for conn in self._connection_states.values() if conn.latency_ms and conn.is_active]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        # Reconexiones
        total_reconnects = sum(conn.reconnect_count for conn in self._connection_states.values())

        return {
            "total_connections": total_connections,
            "active_connections": active_connections,
            "connection_types": {
                "websocket": websocket_connections,
                "sse": sse_connections
            },
            "quality_metrics": {
                "average_quality_score": round(avg_quality, 3),
                "average_latency_ms": round(avg_latency, 1),
                "total_reconnections": total_reconnects
            },
            "streaming_stats": {
                "active_streaming_sessions": len([s for s in self._streaming_states.values() if s.is_active]),
                "paused_streaming_sessions": len([s for s in self._streaming_states.values() if s.status == StreamingStatus.PAUSED])
            },
            "generated_at": datetime.utcnow().isoformat()
        }

    async def cleanup_stale_connections(self, max_idle_minutes: int = 30) -> Dict[str, int]:
        """
        Cleanup de conexiones inactivas
        Background task para memory management
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_idle_minutes)

        stale_connections = []
        for client_id, connection_state in self._connection_states.items():
            if (not connection_state.is_active or
                connection_state.last_activity < cutoff_time):
                stale_connections.append(client_id)

        # Cleanup
        cleaned_count = 0
        for client_id in stale_connections:
            await self.unregister_streaming_connection(client_id)
            cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} stale connections")
        return {
            "cleaned_connections": cleaned_count,
            "cutoff_time": cutoff_time.isoformat(),
            "remaining_active": len([c for c in self._connection_states.values() if c.is_active])
        }