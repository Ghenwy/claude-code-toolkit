"""
Claude Code Toolkit WebUI - FastAPI Main Application
CHAT-01: Basic Chat Interface Setup + SSE Enhancement

Implementa FastAPI + WebSockets + SSE para real-time communication
Siguiendo standards/fastapi.yaml y standards/python.yaml
"""
import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import List, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from models.chat import (
    ChatRequest, ChatResponse, ChatSession, MessageType, MessageStatus,
    MessageUpdateRequest, MessageStatusUpdateRequest, MessageSearchRequest,
    MessageHistoryResponse, MessageSearchResult, MessageStatistics,
    MessageChunkResponse, MessageExport,
    # CHAT-03 Input System models
    InputHistoryEntry, InputDraft, InputAnalytics, CommandSuggestion,
    InputValidationResult, InputHistoryRequest, InputHistoryResponse,
    DraftSaveRequest, CommandValidationRequest, CommandSuggestionsRequest,
    # CHAT-04 Streaming models
    StreamingChunk, StreamingState, StreamingRequest, StreamingStatus,
    TypingIndicator, ConnectionState
)
from services.chat_manager import ChatManager

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global chat manager instance (strategic DI)
chat_manager = ChatManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager para startup/shutdown
    Async patterns para resource management
    """
    logger.info("🚀 Claude Code Toolkit WebUI iniciando...")

    # Startup
    logger.info("✅ Chat Manager inicializado")
    logger.info("✅ WebSocket endpoints listos")

    yield

    # Shutdown
    logger.info("🔄 Cerrando aplicación...")
    logger.info("✅ Aplicación cerrada correctamente")


# FastAPI app con async lifespan
app = FastAPI(
    title="Claude Code Toolkit WebUI",
    description="Real-time chat interface para Claude Code",
    version="2.2.3",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS middleware para development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files serving
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates setup
templates = Jinja2Templates(directory="templates")


# Dependency injection para chat manager
async def get_chat_manager() -> ChatManager:
    """Strategic dependency injection para ChatManager"""
    return chat_manager


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - Chat Interface"""
    from datetime import datetime
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "timestamp": datetime.utcnow().strftime("%H:%M:%S UTC")
        }
    )


@app.get("/api", response_class=HTMLResponse)
async def api_docs():
    """API Documentation endpoint"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Claude Code Toolkit WebUI - API</title>
        <meta charset="utf-8">
        <style>
            body { font-family: 'JetBrains Mono', monospace; margin: 40px; background: #0d1117; color: #c9d1d9; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { background: #21262d; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #30363d; }
            .endpoints { background: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #21262d; }
            code { background: #21262d; padding: 2px 6px; border-radius: 3px; color: #79c0ff; }
            h1 { color: #58a6ff; }
            h2 { color: #f0883e; }
            h3 { color: #56d364; }
            li { margin: 8px 0; }
            a { color: #58a6ff; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Claude Code Toolkit WebUI - API</h1>
            <div class="status">
                <h2>✅ Estado: Activo</h2>
                <p><strong>Versión:</strong> 2.2.3 (CHAT-04 Streaming Enhanced)</p>
                <p><strong>Branch:</strong> feature/streaming</p>
                <p><strong>Features:</strong> FastAPI + Real-time Streaming + Connection Management + Character-by-character Typing</p>
            </div>

            <div class="endpoints">
                <h2>📚 API Endpoints Disponibles</h2>

                <h3>🏠 Core Endpoints</h3>
                <ul>
                    <li><code>GET /</code> - <a href="/">Chat Interface</a></li>
                    <li><code>GET /api</code> - Esta página</li>
                    <li><code>GET /api/docs</code> - <a href="/api/docs">Swagger UI documentation</a></li>
                    <li><code>GET /health</code> - Health check</li>
                </ul>

                <h3>💬 Chat Management</h3>
                <ul>
                    <li><code>POST /api/sessions</code> - Crear nueva chat session</li>
                    <li><code>POST /api/chat</code> - Enviar mensaje con progressive loading y threading</li>
                    <li><code>WS /ws/{session_id}</code> - WebSocket connection</li>
                    <li><code>GET /api/stream/{session_id}</code> - Server-Sent Events stream</li>
                    <li><code>GET /api/sessions/{session_id}/history</code> - Enhanced session history con paginación</li>
                </ul>

                <h3>📝 Message Management</h3>
                <ul>
                    <li><code>PUT /api/messages/{message_id}/status</code> - Actualizar status de mensaje</li>
                    <li><code>PUT /api/messages/{message_id}</code> - Editar contenido de mensaje</li>
                    <li><code>POST /api/messages/{message_id}/bookmark</code> - Toggle bookmark</li>
                    <li><code>GET /api/messages/{message_id}/history</code> - Historial de ediciones</li>
                    <li><code>GET /api/messages/{message_id}/chunks</code> - Chunks para progressive loading</li>
                </ul>

                <h3>🔍 Search & Threading</h3>
                <ul>
                    <li><code>POST /api/search</code> - Búsqueda avanzada de mensajes</li>
                    <li><code>GET /api/sessions/{session_id}/threads</code> - Threads de conversación</li>
                    <li><code>GET /api/sessions/{session_id}/threads/{thread_id}/messages</code> - Mensajes por thread</li>
                    <li><code>GET /api/sessions/{session_id}/bookmarks</code> - Mensajes bookmarked</li>
                </ul>

                <h3>📊 Analytics & Export</h3>
                <ul>
                    <li><code>GET /api/sessions/{session_id}/statistics</code> - Estadísticas de conversación</li>
                    <li><code>POST /api/sessions/{session_id}/export</code> - Crear job de export</li>
                    <li><code>GET /api/exports/{export_id}</code> - Status de export job</li>
                </ul>

                <h3>🎯 CHAT-03: Input System Features</h3>
                <ul>
                    <li><code>GET /api/sessions/{id}/input-history</code> - Retrieve input history con paginación</li>
                    <li><code>POST /api/sessions/{id}/input-history</code> - Save input con command detection</li>
                    <li><code>POST /api/validate-input</code> - Validate Claude Code command syntax</li>
                    <li><code>POST /api/sessions/{id}/draft</code> - Save draft con auto-save</li>
                    <li><code>GET /api/sessions/{id}/draft</code> - Retrieve draft para recovery</li>
                    <li><code>DELETE /api/sessions/{id}/draft</code> - Clear draft</li>
                    <li><code>GET /api/commands/suggestions</code> - Get command suggestions</li>
                    <li><code>GET /api/sessions/{id}/input-analytics</code> - Get input metrics</li>
                    <li><code>GET /api/sessions/{id}/input-summary</code> - Combined input data view</li>
                    <li><code>GET /api/commands/categories</code> - Available command categories</li>
                </ul>

                <h3>🚀 CHAT-04: Real-time Streaming Features</h3>
                <ul>
                    <li><code>POST /api/sessions/{id}/stream</code> - Start character-by-character streaming</li>
                    <li><code>GET /api/sessions/{id}/stream/status</code> - Get streaming status and progress</li>
                    <li><code>POST /api/sessions/{id}/stream/cancel</code> - Cancel active streaming</li>
                    <li><code>GET /api/streaming/active</code> - List all active streaming sessions</li>
                    <li><code>GET /api/stream/enhanced/{id}</code> - Enhanced SSE endpoint with streaming support</li>
                    <li><code>POST /api/sessions/{id}/typing</code> - Control typing indicators manually</li>
                </ul>

                <h3>🔗 Connection Management</h3>
                <ul>
                    <li><code>GET /api/connections/stats</code> - Connection statistics and health metrics</li>
                    <li><code>POST /api/connections/{id}/quality</code> - Update connection quality metrics</li>
                    <li><code>GET /api/connections/{id}/health</code> - Check connection health</li>
                    <li><code>POST /api/connections/{id}/reconnect</code> - Handle reconnection requests</li>
                    <li><code>POST /api/connections/cleanup</code> - Cleanup stale connections</li>
                </ul>

                <h3>🧪 Testing Real-time Communication</h3>
                <p>Para testing manual de conexiones:</p>
                <ol>
                    <li>Crear session: <code>POST /api/sessions</code></li>
                    <li>WebSocket: <code>ws://localhost:8000/ws/{session_id}</code></li>
                    <li>SSE Stream: <code>GET /api/stream/{session_id}</code></li>
                    <li>Enviar mensaje: <code>{"content": "Hello!", "message_type": "user"}</code></li>
                </ol>

                <h3>🎨 Frontend Features</h3>
                <ul>
                    <li>Terminal-style dark theme interface</li>
                    <li>Dual real-time: WebSocket primary, SSE fallback</li>
                    <li>Auto-scroll message display</li>
                    <li>Connection status monitoring</li>
                    <li>Responsive design for desktop/laptop</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/health")
async def health_check(manager: ChatManager = Depends(get_chat_manager)):
    """Health check endpoint con metrics"""
    return {
        "status": "healthy",
        "timestamp": "2025-09-21",
        "version": "2.2.3",
        "component": "webui-backend",
        "metrics": {
            "active_connections": manager.get_active_connections_count(),
            "active_sessions": manager.get_sessions_count()
        }
    }


@app.post("/api/sessions", response_model=dict)
async def create_chat_session(manager: ChatManager = Depends(get_chat_manager)):
    """
    Crear nueva chat session
    Returns session_id para WebSocket connection
    """
    try:
        session = await manager.create_session()
        logger.info(f"Nueva session creada: {session.session_id}")

        return {
            "session_id": str(session.session_id),
            "created_at": session.created_at.isoformat(),
            "websocket_url": f"/ws/{session.session_id}"
        }
    except Exception as e:
        logger.error(f"Error creando session: {e}")
        raise HTTPException(status_code=500, detail="Error creating session")


@app.post("/api/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    session_id: str = Query(..., description="Session ID"),
    enable_streaming: bool = Query(True, description="Enable character-by-character streaming"),
    typing_speed_wpm: float = Query(150.0, ge=50.0, le=300.0, description="Typing speed for streaming"),
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Enhanced enviar mensaje con progressive loading y threading support
    Incluye advanced features de CHAT-02
    """
    try:
        session_uuid = UUID(session_id)
        start_time = time.time()

        # Procesar mensaje con características avanzadas incluyendo streaming
        message = await manager.process_user_message(
            session_id=session_uuid,
            content=request.content,
            enable_progressive_loading=request.enable_progressive_loading,
            thread_id=request.thread_id,
            enable_streaming=enable_streaming,
            typing_speed_wpm=typing_speed_wpm
        )

        # Calcular tiempo de procesamiento
        processing_time = int((time.time() - start_time) * 1000)

        # Crear response enhanced
        response = ChatResponse(
            message=message,
            processing_time_ms=processing_time
        )

        # Añadir chunk info si progressive loading está habilitado
        if request.enable_progressive_loading and message.chunk_info:
            response.chunk_info = message.chunk_info

        # Añadir thread info si hay threading
        if message.thread_id:
            response.thread_info = {
                "thread_id": str(message.thread_id),
                "parent_message_id": str(message.parent_message_id) if message.parent_message_id else None
            }

        return response

    except ValueError as e:
        logger.error(f"Invalid session ID: {e}")
        raise HTTPException(status_code=400, detail="Invalid session ID")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail="Error processing message")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    WebSocket endpoint para real-time chat
    Implementa async patterns y proper error handling
    """
    try:
        # Validate session_id
        session_uuid = UUID(session_id)
        session = await manager.get_session(session_uuid)

        if not session:
            await websocket.close(code=4004, reason="Session not found")
            return

        # Accept WebSocket connection
        await websocket.accept()

        # Register enhanced streaming connection
        client_id = await manager.register_streaming_connection(websocket, session_uuid, "websocket")
        logger.info(f"WebSocket connected - Session: {session_id}, Client: {client_id}")

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                logger.info(f"Received message: {data}")

                # Parse and validate message
                try:
                    import json
                    message_data = json.loads(data)

                    # Process message
                    response_message = await manager.process_user_message(
                        session_id=session_uuid,
                        content=message_data.get("content", "")
                    )

                    # Send response back to client
                    await websocket.send_text(response_message.model_dump_json())

                    # Broadcast to other clients (si hay múltiples connections)
                    await manager.broadcast_message(response_message, exclude_client=client_id)

                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "error": "Invalid JSON format",
                        "type": "validation_error"
                    }))
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    await websocket.send_text(json.dumps({
                        "error": str(e),
                        "type": "processing_error"
                    }))

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected - Client: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Cleanup enhanced streaming connection
            await manager.unregister_streaming_connection(client_id)

    except ValueError:
        await websocket.close(code=4400, reason="Invalid session ID format")
    except Exception as e:
        logger.error(f"WebSocket endpoint error: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close(code=4500, reason="Internal server error")


@app.get("/api/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    page: int = Query(1, ge=1, description="Página (1-based)"),
    page_size: int = Query(50, ge=1, le=100, description="Tamaño de página"),
    include_threads: bool = Query(True, description="Incluir información de threads"),
    include_statistics: bool = Query(True, description="Incluir estadísticas"),
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Enhanced obtener historial con paginación y metadata adicional
    Incluye threads, estadísticas y progressive loading info
    """
    try:
        session_uuid = UUID(session_id)
        result = await manager.get_enhanced_session_history(
            session_uuid, page, page_size, include_threads, include_statistics
        )

        if not result:
            raise HTTPException(status_code=404, detail="Session not found")

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error getting enhanced session history: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving history")


@app.get("/api/stream/{session_id}")
async def sse_endpoint(
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Server-Sent Events endpoint para real-time message streaming
    Fallback mechanism para WebSocket connection issues
    """
    try:
        session_uuid = UUID(session_id)
        session = await manager.get_session(session_uuid)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        async def event_stream():
            """
            Generator para SSE stream con async polling
            Implementa async patterns para non-blocking operations
            """
            last_message_count = len(session.messages)

            while True:
                try:
                    # Check for new messages
                    current_session = await manager.get_session(session_uuid)
                    if not current_session:
                        break

                    current_count = len(current_session.messages)

                    # Si hay nuevos mensajes, enviarlos
                    if current_count > last_message_count:
                        new_messages = current_session.messages[last_message_count:]

                        for message in new_messages:
                            data = json.dumps({
                                "type": "message",
                                "data": message.model_dump()
                            })
                            yield f"data: {data}\n\n"

                        last_message_count = current_count

                    # Heartbeat para mantener connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': asyncio.get_event_loop().time()})}\n\n"

                    # Non-blocking sleep
                    await asyncio.sleep(1.0)

                except Exception as e:
                    logger.error(f"SSE stream error: {e}")
                    error_data = json.dumps({
                        "type": "error",
                        "message": str(e)
                    })
                    yield f"data: {error_data}\n\n"
                    break

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"SSE endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Error starting SSE stream")


# ========================================
# NUEVOS ENDPOINTS PARA CHAT-02 FEATURES
# ========================================

@app.put("/api/messages/{message_id}/status")
async def update_message_status(
    message_id: str,
    request: MessageStatusUpdateRequest,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Actualizar status de un mensaje específico
    Para tracking detallado del estado de mensajes
    """
    try:
        message_uuid = UUID(message_id)
        success = await manager.update_message_status(
            message_uuid, request.new_status, request.metadata
        )

        if not success:
            raise HTTPException(status_code=404, detail="Message not found")

        return {
            "success": True,
            "message_id": message_id,
            "new_status": request.new_status.value,
            "updated_at": time.time()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    except Exception as e:
        logger.error(f"Error updating message status: {e}")
        raise HTTPException(status_code=500, detail="Error updating status")


@app.put("/api/messages/{message_id}")
async def update_message(
    message_id: str,
    request: MessageUpdateRequest,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Actualizar contenido de mensaje o toggle bookmark
    Incluye edit history tracking
    """
    try:
        # Validar que el message_id en URL coincida con el del request
        message_uuid = UUID(message_id)
        if request.message_id != message_uuid:
            raise HTTPException(status_code=400, detail="Message ID mismatch")

        updated_message = await manager.update_message_content(request)

        if not updated_message:
            raise HTTPException(status_code=404, detail="Message not found")

        return {
            "success": True,
            "message": updated_message.model_dump(),
            "updated_at": time.time()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    except Exception as e:
        logger.error(f"Error updating message: {e}")
        raise HTTPException(status_code=500, detail="Error updating message")


@app.post("/api/messages/{message_id}/bookmark")
async def toggle_message_bookmark(
    message_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Toggle bookmark status de un mensaje
    Shortcut endpoint para bookmarking rápido
    """
    try:
        message_uuid = UUID(message_id)
        request = MessageUpdateRequest(
            message_id=message_uuid,
            toggle_bookmark=True
        )

        updated_message = await manager.update_message_content(request)

        if not updated_message:
            raise HTTPException(status_code=404, detail="Message not found")

        return {
            "success": True,
            "message_id": message_id,
            "is_bookmarked": updated_message.is_bookmarked,
            "updated_at": time.time()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    except Exception as e:
        logger.error(f"Error toggling bookmark: {e}")
        raise HTTPException(status_code=500, detail="Error toggling bookmark")


@app.get("/api/messages/{message_id}/history")
async def get_message_edit_history(
    message_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Obtener historial de ediciones de un mensaje
    Para tracking de cambios y auditoría
    """
    try:
        message_uuid = UUID(message_id)

        # Buscar mensaje en todas las sessions
        for session in manager._sessions.values():
            for message in session.messages:
                if message.id == message_uuid:
                    return {
                        "message_id": message_id,
                        "edit_history": message.edit_history,
                        "total_edits": len(message.edit_history),
                        "current_status": message.status.value
                    }

        raise HTTPException(status_code=404, detail="Message not found")

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    except Exception as e:
        logger.error(f"Error getting message history: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving history")


@app.post("/api/search", response_model=List[MessageSearchResult])
async def search_messages(
    request: MessageSearchRequest,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Búsqueda avanzada de mensajes con filtros
    Incluye ranking por relevancia y filtros múltiples
    """
    try:
        results = await manager.search_messages(request)

        return results

    except Exception as e:
        logger.error(f"Error searching messages: {e}")
        raise HTTPException(status_code=500, detail="Error performing search")


@app.get("/api/sessions/{session_id}/threads")
async def get_session_threads(
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Obtener todos los threads de una session
    Para navegación de conversaciones
    """
    try:
        session_uuid = UUID(session_id)
        threads = await manager.get_message_threads(session_uuid)

        return {
            "session_id": session_id,
            "threads": [thread.model_dump() for thread in threads],
            "total_threads": len(threads)
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error getting session threads: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving threads")


@app.get("/api/sessions/{session_id}/threads/{thread_id}/messages")
async def get_thread_messages(
    session_id: str,
    thread_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Obtener mensajes de un thread específico
    Para vista de conversación por thread
    """
    try:
        session_uuid = UUID(session_id)
        thread_uuid = UUID(thread_id)
        messages = await manager.get_thread_messages(session_uuid, thread_uuid)

        return {
            "session_id": session_id,
            "thread_id": thread_id,
            "messages": [msg.model_dump() for msg in messages],
            "count": len(messages)
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except Exception as e:
        logger.error(f"Error getting thread messages: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving messages")


@app.get("/api/sessions/{session_id}/bookmarks")
async def get_bookmarked_messages(
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Obtener mensajes bookmarked de una session
    Para acceso rápido a mensajes importantes
    """
    try:
        session_uuid = UUID(session_id)
        bookmarked = await manager.get_bookmarked_messages(session_uuid)

        return {
            "session_id": session_id,
            "bookmarked_messages": [msg.model_dump() for msg in bookmarked],
            "count": len(bookmarked)
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error getting bookmarked messages: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving bookmarks")


@app.get("/api/sessions/{session_id}/statistics")
async def get_session_statistics(
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Obtener estadísticas detalladas de una session
    Para analytics y métricas de conversación
    """
    try:
        session_uuid = UUID(session_id)
        stats = await manager.get_session_statistics(session_uuid)

        if not stats:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "session_id": session_id,
            "statistics": stats.model_dump(),
            "generated_at": time.time()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error getting session statistics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")


@app.post("/api/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    format_type: str = Query("json", description="Formato: json, markdown, txt, html"),
    include_metadata: bool = Query(True, description="Incluir metadatos"),
    bookmarks_only: bool = Query(False, description="Solo mensajes bookmarked"),
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Crear job de export para mensajes de session
    Prepara datos para descarga en diferentes formatos
    """
    try:
        session_uuid = UUID(session_id)
        export_job = await manager.export_session_messages(
            session_uuid, format_type, include_metadata, bookmarks_only
        )

        if not export_job:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "export_id": str(export_job.export_id),
            "session_id": session_id,
            "format": format_type,
            "status": "prepared",
            "estimated_size_bytes": export_job.file_size_bytes,
            "created_at": export_job.created_at.isoformat()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error creating export job: {e}")
        raise HTTPException(status_code=500, detail="Error creating export")


@app.get("/api/exports/{export_id}")
async def get_export_status(
    export_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Obtener status de un job de export
    Para polling del progreso de export
    """
    try:
        export_uuid = UUID(export_id)
        export_job = await manager.get_export_status(export_uuid)

        if not export_job:
            raise HTTPException(status_code=404, detail="Export job not found")

        return {
            "export_id": export_id,
            "status": "ready",  # En implementación real sería dinámico
            "format": export_job.format_type,
            "file_size_bytes": export_job.file_size_bytes,
            "created_at": export_job.created_at.isoformat(),
            "download_url": f"/api/exports/{export_id}/download"  # Endpoint futuro
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid export ID format")
    except Exception as e:
        logger.error(f"Error getting export status: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving export status")


@app.get("/api/messages/{message_id}/chunks")
async def get_message_chunks(
    message_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Obtener chunks de un mensaje para progressive loading
    Para reconstrucción de mensajes largos
    """
    try:
        message_uuid = UUID(message_id)
        chunks = await manager.get_message_chunks(message_uuid)

        return {
            "message_id": message_id,
            "chunks": [chunk.model_dump() for chunk in chunks],
            "total_chunks": len(chunks),
            "is_complete": all(chunk.is_final for chunk in chunks[-1:]) if chunks else False
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    except Exception as e:
        logger.error(f"Error getting message chunks: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving chunks")


# ========================================
# NUEVOS ENDPOINTS PARA CHAT-03: INPUT SYSTEM
# ========================================

@app.get("/api/sessions/{session_id}/input-history")
async def get_input_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=100, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Retrieve input history para una session con paginación
    Enhanced input tracking y recovery functionality
    """
    try:
        session_uuid = UUID(session_id)
        result = await manager.get_input_history(session_uuid, limit, offset)

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error getting input history: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving input history")


@app.post("/api/sessions/{session_id}/input-history")
async def save_input_history(
    session_id: str,
    request: InputHistoryRequest,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Save input entry al historial con command detection
    Strategic input tracking para analytics y recovery
    """
    try:
        session_uuid = UUID(session_id)

        # Verificar que la session existe
        session = await manager.get_session(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        entry = await manager.save_input_to_history(session_uuid, request)

        return {
            "success": True,
            "entry": entry.model_dump(),
            "session_id": session_id,
            "is_command": entry.is_command,
            "command_type": entry.command_type
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error saving input history: {e}")
        raise HTTPException(status_code=500, detail="Error saving input")


@app.post("/api/validate-input")
async def validate_input(
    request: CommandValidationRequest,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Validate command syntax y provide suggestions
    Real-time validation para Claude Code commands
    """
    try:
        validation_result = await manager.validate_input(request)

        return {
            "validation": validation_result.model_dump(),
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Error validating input: {e}")
        raise HTTPException(status_code=500, detail="Error validating input")


@app.post("/api/sessions/{session_id}/draft")
async def save_draft(
    session_id: str,
    request: DraftSaveRequest,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Save draft con auto-save functionality
    Strategic persistence para recovery tras desconexión
    """
    try:
        session_uuid = UUID(session_id)

        # Verificar que la session existe
        session = await manager.get_session(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        draft = await manager.save_draft(session_uuid, request)

        return {
            "success": True,
            "draft": draft.model_dump(),
            "session_id": session_id,
            "auto_saved": draft.auto_saved
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error saving draft: {e}")
        raise HTTPException(status_code=500, detail="Error saving draft")


@app.get("/api/sessions/{session_id}/draft")
async def get_draft(
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Retrieve draft para recovery tras reconnection
    Auto-cleanup de drafts antiguos incluido
    """
    try:
        session_uuid = UUID(session_id)
        draft = await manager.get_draft(session_uuid)

        if not draft:
            return {
                "success": True,
                "has_draft": False,
                "draft": None,
                "session_id": session_id
            }

        return {
            "success": True,
            "has_draft": True,
            "draft": draft.model_dump(),
            "session_id": session_id,
            "is_empty": draft.is_empty()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error getting draft: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving draft")


@app.delete("/api/sessions/{session_id}/draft")
async def clear_draft(
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Clear draft para una session
    Manual cleanup option para users
    """
    try:
        session_uuid = UUID(session_id)
        cleared = await manager.clear_draft(session_uuid)

        return {
            "success": True,
            "cleared": cleared,
            "session_id": session_id
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error clearing draft: {e}")
        raise HTTPException(status_code=500, detail="Error clearing draft")


@app.get("/api/commands/suggestions")
async def get_command_suggestions(
    request: CommandSuggestionsRequest = Depends(),
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Get command suggestions para autocompletado
    Strategic suggestion engine con categoría filtering
    """
    try:
        suggestions = await manager.get_command_suggestions(request)

        return {
            "suggestions": [s.model_dump() for s in suggestions],
            "total_count": len(suggestions),
            "partial_input": request.partial_input,
            "category_filter": request.category_filter
        }

    except Exception as e:
        logger.error(f"Error getting command suggestions: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving suggestions")


@app.get("/api/sessions/{session_id}/input-analytics")
async def get_input_analytics(
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Get input analytics y métricas para una session
    Insights de comportamiento y typing patterns
    """
    try:
        session_uuid = UUID(session_id)
        analytics = await manager.get_input_analytics(session_uuid)

        if not analytics:
            return {
                "success": True,
                "has_analytics": False,
                "analytics": None,
                "session_id": session_id
            }

        return {
            "success": True,
            "has_analytics": True,
            "analytics": analytics.model_dump(),
            "session_id": session_id,
            "generated_at": time.time()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error getting input analytics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving analytics")


@app.get("/api/sessions/{session_id}/input-summary")
async def get_session_input_summary(
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Get comprehensive input summary para una session
    Combined view de history, drafts, y analytics
    """
    try:
        session_uuid = UUID(session_id)
        summary = await manager.get_session_input_summary(session_uuid)

        return {
            "success": True,
            "summary": summary,
            "generated_at": time.time()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error getting input summary: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving summary")


@app.get("/api/commands/categories")
async def get_command_categories(
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Get available command categories
    Reference info para filtering y documentation
    """
    try:
        categories = manager._input_validator.get_available_categories()
        counts = manager._input_validator.get_command_count_by_category()

        return {
            "categories": categories,
            "category_counts": counts,
            "total_commands": sum(counts.values())
        }

    except Exception as e:
        logger.error(f"Error getting command categories: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving categories")


# ========================================
# CHAT-04: STREAMING ENDPOINTS
# ========================================

@app.post("/api/sessions/{session_id}/stream")
async def start_streaming_message(
    session_id: str,
    request: StreamingRequest,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Iniciar streaming de mensaje caracter por caracter
    CHAT-04 endpoint para real-time message streaming
    """
    try:
        session_uuid = UUID(session_id)

        # Verificar que la session existe
        session = await manager.get_session(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Verificar que request session_id coincide
        if request.session_id != session_uuid:
            raise HTTPException(status_code=400, detail="Session ID mismatch")

        # Iniciar streaming
        message = await manager.start_message_streaming(
            session_id=session_uuid,
            message_content=request.message_content,
            typing_speed_wpm=request.typing_speed_wpm,
            include_thinking_time=request.include_thinking_time
        )

        return {
            "success": True,
            "message_id": str(message.id),
            "session_id": session_id,
            "streaming_started": True,
            "estimated_duration_ms": int((len(request.message_content) / (request.typing_speed_wpm * 5 / 60)) * 1000),
            "character_count": len(request.message_content)
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error starting streaming: {e}")
        raise HTTPException(status_code=500, detail="Error starting streaming")


@app.get("/api/sessions/{session_id}/stream/status")
async def get_streaming_status(
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Obtener estado actual del streaming para una session
    """
    try:
        session_uuid = UUID(session_id)
        streaming_state = await manager.get_streaming_state(session_uuid)

        if not streaming_state:
            return {
                "session_id": session_id,
                "is_streaming": False,
                "status": "idle"
            }

        return {
            "session_id": session_id,
            "is_streaming": streaming_state.is_active,
            "status": streaming_state.status.value,
            "progress": {
                "characters_sent": streaming_state.characters_sent,
                "total_characters": streaming_state.total_characters,
                "percentage": (streaming_state.characters_sent / streaming_state.total_characters * 100) if streaming_state.total_characters else 0
            },
            "connected_clients": len(streaming_state.connected_clients),
            "typing_speed_wpm": streaming_state.words_per_minute,
            "last_activity": streaming_state.last_chunk_time.isoformat()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error getting streaming status: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving streaming status")


@app.post("/api/sessions/{session_id}/stream/cancel")
async def cancel_streaming(
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Cancelar streaming activo para una session
    """
    try:
        session_uuid = UUID(session_id)
        cancelled = await manager.cancel_streaming(session_uuid)

        return {
            "success": True,
            "cancelled": cancelled,
            "session_id": session_id,
            "timestamp": time.time()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error cancelling streaming: {e}")
        raise HTTPException(status_code=500, detail="Error cancelling streaming")


@app.get("/api/streaming/active")
async def get_active_streaming_sessions(
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Obtener lista de sessions con streaming activo
    Para monitoring y debugging
    """
    try:
        active_sessions = await manager.get_active_streaming_sessions()

        return {
            "active_streaming_sessions": [str(session_id) for session_id in active_sessions],
            "count": len(active_sessions),
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Error getting active streaming sessions: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving active sessions")


@app.get("/api/stream/enhanced/{session_id}")
async def enhanced_sse_endpoint(
    session_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Enhanced Server-Sent Events endpoint con streaming support
    Fallback mejorado para WebSocket con real-time streaming
    """
    try:
        session_uuid = UUID(session_id)
        session = await manager.get_session(session_uuid)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        async def enhanced_event_stream():
            """
            Generator enhanced para SSE stream con streaming chunks
            """
            last_message_count = len(session.messages)
            last_chunk_time = datetime.utcnow()

            while True:
                try:
                    # Check for streaming chunks
                    streaming_state = await manager.get_streaming_state(session_uuid)
                    if streaming_state and streaming_state.is_active:
                        # Send streaming status updates
                        status_data = json.dumps({
                            "type": "streaming_status",
                            "data": {
                                "status": streaming_state.status.value,
                                "characters_sent": streaming_state.characters_sent,
                                "total_characters": streaming_state.total_characters,
                                "is_active": streaming_state.is_active
                            }
                        })
                        yield f"data: {status_data}\n\n"

                    # Check for new messages (traditional)
                    current_session = await manager.get_session(session_uuid)
                    if not current_session:
                        break

                    current_count = len(current_session.messages)

                    # Si hay nuevos mensajes, enviarlos
                    if current_count > last_message_count:
                        new_messages = current_session.messages[last_message_count:]

                        for message in new_messages:
                            data = json.dumps({
                                "type": "message",
                                "data": message.model_dump()
                            })
                            yield f"data: {data}\n\n"

                        last_message_count = current_count

                    # Enhanced heartbeat con connection quality
                    heartbeat_data = json.dumps({
                        "type": "heartbeat",
                        "timestamp": asyncio.get_event_loop().time(),
                        "session_id": session_id,
                        "connection_type": "sse_enhanced"
                    })
                    yield f"data: {heartbeat_data}\n\n"

                    # Non-blocking sleep
                    await asyncio.sleep(0.5)  # Faster polling para streaming

                except Exception as e:
                    logger.error(f"Enhanced SSE stream error: {e}")
                    error_data = json.dumps({
                        "type": "error",
                        "message": str(e),
                        "timestamp": time.time()
                    })
                    yield f"data: {error_data}\n\n"
                    break

        return StreamingResponse(
            enhanced_event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
                "X-Accel-Buffering": "no"  # Nginx optimization para real-time
            }
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Enhanced SSE endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Error starting enhanced SSE stream")


@app.post("/api/sessions/{session_id}/typing")
async def set_typing_indicator(
    session_id: str,
    is_typing: bool = True,
    message: str = "Claude está escribiendo...",
    duration_ms: Optional[int] = None,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Controlar typing indicator manualmente
    Para testing y control fino del UX
    """
    try:
        session_uuid = UUID(session_id)

        if is_typing:
            await manager._set_typing_indicator(session_uuid, message, duration_ms)
        else:
            await manager._clear_typing_indicator(session_uuid)

        return {
            "success": True,
            "typing_indicator_set": is_typing,
            "session_id": session_id,
            "message": message
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"Error setting typing indicator: {e}")
        raise HTTPException(status_code=500, detail="Error setting typing indicator")


@app.get("/api/connections/stats")
async def get_connection_statistics(
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Obtener estadísticas de conexiones para monitoring
    """
    try:
        stats = await manager.get_connection_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting connection stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving connection statistics")


@app.post("/api/connections/{client_id}/quality")
async def update_connection_quality(
    client_id: str,
    latency_ms: float = Query(..., ge=0, le=10000, description="Latency in milliseconds"),
    success_rate: float = Query(1.0, ge=0.0, le=1.0, description="Success rate 0-1"),
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Actualizar métricas de calidad de conexión
    Para client-side monitoring integration
    """
    try:
        client_uuid = UUID(client_id)
        await manager.update_connection_quality(client_uuid, latency_ms, success_rate)

        return {
            "success": True,
            "client_id": client_id,
            "updated_metrics": {
                "latency_ms": latency_ms,
                "success_rate": success_rate
            },
            "timestamp": time.time()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid client ID format")
    except Exception as e:
        logger.error(f"Error updating connection quality: {e}")
        raise HTTPException(status_code=500, detail="Error updating connection quality")


@app.get("/api/connections/{client_id}/health")
async def check_connection_health(
    client_id: str,
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Verificar salud de una conexión específica
    """
    try:
        client_uuid = UUID(client_id)
        health_info = await manager.check_connection_health(client_uuid)

        return health_info

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid client ID format")
    except Exception as e:
        logger.error(f"Error checking connection health: {e}")
        raise HTTPException(status_code=500, detail="Error checking connection health")


@app.post("/api/connections/{client_id}/reconnect")
async def handle_reconnection_request(
    client_id: str,
    session_id: str = Query(..., description="Session ID to reconnect to"),
    connection_type: str = Query("websocket", description="Connection type"),
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Endpoint para solicitar reconexión
    Note: Este endpoint prepara la reconexión, el client debe establecer nuevo WebSocket
    """
    try:
        client_uuid = UUID(client_id)
        session_uuid = UUID(session_id)

        # Verificar que la session existe
        session = await manager.get_session(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Simular preparación de reconexión
        # En implementación real, esto coordinaría con el frontend
        reconnection_info = {
            "success": True,
            "reconnection_prepared": True,
            "client_id": client_id,
            "session_id": session_id,
            "connection_type": connection_type,
            "websocket_url": f"/ws/{session_id}",
            "sse_fallback_url": f"/api/stream/enhanced/{session_id}",
            "instructions": "Establish new WebSocket connection using the provided URL",
            "timestamp": time.time()
        }

        return reconnection_info

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except Exception as e:
        logger.error(f"Error handling reconnection request: {e}")
        raise HTTPException(status_code=500, detail="Error handling reconnection")


@app.post("/api/connections/cleanup")
async def cleanup_stale_connections(
    max_idle_minutes: int = Query(30, ge=1, le=1440, description="Max idle time in minutes"),
    manager: ChatManager = Depends(get_chat_manager)
):
    """
    Limpiar conexiones inactivas manualmente
    Para administrative cleanup
    """
    try:
        cleanup_result = await manager.cleanup_stale_connections(max_idle_minutes)

        return {
            "success": True,
            "cleanup_result": cleanup_result,
            "max_idle_minutes": max_idle_minutes
        }

    except Exception as e:
        logger.error(f"Error cleaning up connections: {e}")
        raise HTTPException(status_code=500, detail="Error cleaning up connections")


if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting Claude Code Toolkit WebUI...")
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # Development only
        log_level="info"
    )