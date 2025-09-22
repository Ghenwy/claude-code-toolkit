# Claude Code Toolkit - WebUI Chat Interface

**CHAT-01: Basic Chat Interface Setup + SSE Enhancement**

Modern FastAPI + WebSockets + SSE chat interface with terminal-style dark theme.

## Features Completed ✅

### Backend Enhancement
- ✅ **FastAPI backend** with async patterns and strategic DI
- ✅ **WebSocket support** for real-time communication
- ✅ **Server-Sent Events (SSE)** fallback mechanism
- ✅ **Session management** with in-memory storage
- ✅ **Health endpoints** with metrics
- ✅ **CORS middleware** for development
- ✅ **Pydantic v2 models** for validation

### Frontend Implementation
- ✅ **Terminal-style dark theme** following Claude Code aesthetics
- ✅ **Responsive design** optimized for desktop/laptop
- ✅ **Dual real-time support** - WebSocket primary, SSE fallback
- ✅ **Auto-scroll message display** with terminal formatting
- ✅ **Connection status monitoring** with visual indicators
- ✅ **Error handling** with retry mechanisms
- ✅ **Performance monitoring** with latency tracking

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Chat Interface (HTML) |
| `/api` | GET | API Documentation |
| `/health` | GET | Health check with metrics |
| `/api/sessions` | POST | Create new chat session |
| `/api/chat` | POST | Send message via HTTP |
| `/ws/{session_id}` | WebSocket | Real-time WebSocket connection |
| `/api/stream/{session_id}` | GET | Server-Sent Events stream |
| `/api/sessions/{session_id}/history` | GET | Session message history |

## Quick Start

### 1. Start Development Server

```bash
cd webui/
python3 start-dev-server.py
```

### 2. Access Chat Interface

- **Chat Interface**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/api/docs
- **Health Check**: http://127.0.0.1:8000/health

### 3. Using the Chat

1. Open browser to http://127.0.0.1:8000
2. Interface automatically creates session and connects
3. Type messages in the terminal-style input
4. Real-time responses via WebSocket (with SSE fallback)

## Technical Architecture

### Dual Real-time Strategy
```
Primary:   WebSocket (/ws/{session_id})
Fallback:  SSE (/api/stream/{session_id}) + HTTP POST
```

### Frontend Stack
- **HTML5** semantic markup with accessibility support
- **CSS** terminal-style dark theme with grid/flexbox layout
- **JavaScript** ES2024 with async/await patterns
- **Fonts** JetBrains Mono for authentic terminal experience

### Backend Stack
- **FastAPI** with async lifespan management
- **WebSockets** for bidirectional real-time communication
- **SSE** for server-to-client streaming fallback
- **Pydantic v2** for request/response validation
- **Jinja2** for HTML template rendering

## Connection Flow

```
1. Client loads chat.html
2. JavaScript creates session (POST /api/sessions)
3. Attempts WebSocket connection (/ws/{session_id})
4. If WebSocket fails, falls back to SSE (/api/stream/{session_id})
5. Messages sent via WebSocket or HTTP POST
6. Real-time updates via chosen transport
```

## Development Features

### Performance Monitoring
- Connection latency tracking
- Message response times
- Transport type indicator
- Connection status display

### Error Handling
- Automatic reconnection with exponential backoff
- Graceful degradation WebSocket → SSE
- User-friendly error messages
- Network offline detection

### Accessibility
- WCAG 2.1 AA compliance
- Keyboard navigation support
- High contrast mode support
- Reduced motion preferences

## File Structure

```
webui/
├── main.py                 # FastAPI application with SSE
├── start-dev-server.py     # Development server script
├── models/
│   └── chat.py            # Pydantic models
├── services/
│   └── chat_manager.py    # Chat session management
├── templates/
│   └── chat.html          # Chat interface template
├── static/
│   ├── css/
│   │   └── chat.css       # Terminal dark theme styles
│   └── js/
│       └── chat.js        # Dual transport chat client
└── README.md              # This file
```

## Testing

### Manual Testing
1. Start server: `python3 start-dev-server.py`
2. Open browser to http://127.0.0.1:8000
3. Verify chat interface loads with terminal aesthetics
4. Send test messages and verify echo responses
5. Check connection status indicators
6. Test network disconnection/reconnection

### API Testing
```bash
# Create session
curl -X POST http://127.0.0.1:8000/api/sessions

# Send message (replace SESSION_ID)
curl -X POST "http://127.0.0.1:8000/api/chat?session_id=SESSION_ID" \
     -H "Content-Type: application/json" \
     -d '{"content": "Hello!", "message_type": "user"}'

# Check health
curl http://127.0.0.1:8000/health
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBUI_HOST` | `127.0.0.1` | Server host |
| `WEBUI_PORT` | `8000` | Server port |
| `WEBUI_RELOAD` | `true` | Auto-reload in development |
| `WEBUI_LOG_LEVEL` | `info` | Logging level |

## Standards Compliance

- **FastAPI**: Following `standards/fastapi.yaml` patterns
- **Python**: Following `standards/python.yaml` conventions
- **HTML5**: Following `standards/html5.yaml` semantic markup
- **JavaScript**: Following `standards/javascript.yaml` modern patterns

## Next Steps

This completes **CHAT-01 Frontend + SSE Enhancement**. Future iterations could add:

- Authentication and user management
- Message persistence with database
- File upload and media support
- Multiple chat rooms/channels
- Advanced Claude Code integration
- Production deployment configuration

---

**Claude Code Toolkit v2.2.3** - Terminal-style chat interface with dual real-time transport.