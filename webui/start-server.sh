#!/bin/bash
# Development Server Startup Script (Shell version)
# Claude Code Toolkit WebUI - CHAT-01

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Claude Code Toolkit WebUI - Development Server${NC}"
echo -e "${BLUE}📍 CHAT-01: Basic Chat Interface Setup${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ Error: main.py not found${NC}"
    echo -e "${YELLOW}💡 Please run this script from the webui/ directory${NC}"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 not found${NC}"
    echo -e "${YELLOW}💡 Please install Python 3.11+${NC}"
    exit 1
fi

# Check requirements
echo -e "${BLUE}🔍 Checking requirements...${NC}"
if ! python3 -c "import fastapi, uvicorn, websockets, pydantic" 2>/dev/null; then
    echo -e "${RED}❌ Missing dependencies${NC}"
    echo -e "${YELLOW}💡 Installing requirements...${NC}"

    # Go to project root to install requirements
    cd ..
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
    else
        echo -e "${RED}❌ requirements.txt not found${NC}"
        exit 1
    fi
    cd webui
fi

# Environment variables (with defaults)
export WEBUI_HOST=${WEBUI_HOST:-"127.0.0.1"}
export WEBUI_PORT=${WEBUI_PORT:-"8000"}
export WEBUI_RELOAD=${WEBUI_RELOAD:-"true"}
export WEBUI_LOG_LEVEL=${WEBUI_LOG_LEVEL:-"info"}

echo -e "${GREEN}✅ Requirements check passed${NC}"
echo ""
echo -e "${BLUE}🔧 Configuration:${NC}"
echo -e "   Host: ${WEBUI_HOST}"
echo -e "   Port: ${WEBUI_PORT}"
echo -e "   Reload: ${WEBUI_RELOAD}"
echo -e "   Log Level: ${WEBUI_LOG_LEVEL}"
echo ""

echo -e "${BLUE}🌐 Access URLs:${NC}"
echo -e "   Local: ${GREEN}http://${WEBUI_HOST}:${WEBUI_PORT}${NC}"
echo -e "   API Docs: ${GREEN}http://${WEBUI_HOST}:${WEBUI_PORT}/api/docs${NC}"
echo -e "   Health: ${GREEN}http://${WEBUI_HOST}:${WEBUI_PORT}/health${NC}"
echo ""

echo -e "${YELLOW}⚡ Starting Uvicorn server...${NC}"
echo -e "${YELLOW}   Press Ctrl+C to stop${NC}"
echo ""

# Start server with uvicorn directly
python3 -m uvicorn main:app \
    --host "${WEBUI_HOST}" \
    --port "${WEBUI_PORT}" \
    --reload \
    --log-level "${WEBUI_LOG_LEVEL}" \
    --access-log