#!/usr/bin/env python3
"""
Development Server Startup Script
Claude Code Toolkit WebUI - CHAT-01

Uvicorn development server con auto-reload y optimizations
Siguiendo standards/fastapi.yaml y standards/python.yaml
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Añadir webui directory al Python path
webui_path = Path(__file__).parent
sys.path.insert(0, str(webui_path))

try:
    import uvicorn
except ImportError:
    print("❌ Error: uvicorn no encontrado. Instala dependencies:")
    print("   pip install -r requirements.txt")
    sys.exit(1)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_requirements() -> bool:
    """
    Verificar que todas las dependencies estén instaladas
    Strategic validation antes de startup
    """
    required_packages = ["fastapi", "uvicorn", "websockets", "pydantic"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        logger.error(f"❌ Missing packages: {', '.join(missing_packages)}")
        logger.info("💡 Install with: pip install -r requirements.txt")
        return False

    return True


async def main() -> None:
    """
    Main async function para server startup
    Modern Python patterns con async support
    """
    logger.info("🚀 Claude Code Toolkit WebUI - Development Server")
    logger.info("📍 CHAT-01: Basic Chat Interface Setup")

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Configuration
    host = os.getenv("WEBUI_HOST", "127.0.0.1")
    port = int(os.getenv("WEBUI_PORT", "8000"))
    reload = os.getenv("WEBUI_RELOAD", "true").lower() == "true"
    log_level = os.getenv("WEBUI_LOG_LEVEL", "info")

    logger.info(f"🔧 Configuration:")
    logger.info(f"   Host: {host}")
    logger.info(f"   Port: {port}")
    logger.info(f"   Reload: {reload}")
    logger.info(f"   Log Level: {log_level}")
    logger.info(f"   Working Directory: {webui_path}")

    # Environment setup
    os.chdir(webui_path)

    try:
        logger.info("⚡ Starting Uvicorn server...")
        logger.info(f"🌐 Access URLs:")
        logger.info(f"   Local: http://{host}:{port}")
        logger.info(f"   API Docs: http://{host}:{port}/api/docs")
        logger.info(f"   Health: http://{host}:{port}/health")

        # Uvicorn server startup con FastAPI optimizations
        config = uvicorn.Config(
            app="main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=True,
            use_colors=True,
            # Performance optimizations para development
            loop="asyncio",
            http="auto",
            # Security headers
            server_header=False,
        )

        server = uvicorn.Server(config)
        await server.serve()

    except KeyboardInterrupt:
        logger.info("🔄 Server shutdown by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)
    finally:
        logger.info("✅ Server stopped")


if __name__ == "__main__":
    # Modern Python async main pattern
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🔄 Shutdown initiated by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)