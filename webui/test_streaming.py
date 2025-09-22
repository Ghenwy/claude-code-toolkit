#!/usr/bin/env python3
"""
Test script para validar CHAT-04 streaming functionality
Prueba manualmente el backend streaming infrastructure
"""
import asyncio
import json
import time
from uuid import UUID
import sys
import os

# Añadir el directorio webui al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.chat_manager import ChatManager
from models.chat import StreamingRequest, MessageType


class StreamingTester:
    """Tester para streaming functionality"""

    def __init__(self):
        self.manager = ChatManager()
        self.session = None
        self.client_id = None

    async def setup(self):
        """Setup inicial del test"""
        print("🚀 Configurando test environment...")

        # Crear session
        self.session = await self.manager.create_session()
        print(f"✅ Session creada: {self.session.session_id}")

        return True

    async def test_basic_streaming(self):
        """Test básico de streaming caracter por caracter"""
        print("\n📝 Test 1: Streaming básico...")

        test_content = "Hola! Este es un mensaje de prueba para validar el streaming caracter por caracter."

        # Iniciar streaming
        start_time = time.time()
        message = await self.manager.start_message_streaming(
            session_id=self.session.session_id,
            message_content=test_content,
            typing_speed_wpm=300.0,  # Rápido para testing
            include_thinking_time=True
        )

        print(f"✅ Streaming iniciado: message_id = {message.id}")

        # Esperar a que termine
        streaming_state = await self.manager.get_streaming_state(self.session.session_id)
        while streaming_state and streaming_state.is_active:
            await asyncio.sleep(0.1)
            streaming_state = await self.manager.get_streaming_state(self.session.session_id)

        end_time = time.time()
        duration = end_time - start_time

        # Validar resultado
        final_message = None
        for msg in self.session.messages:
            if msg.id == message.id:
                final_message = msg
                break

        if final_message and final_message.content == test_content:
            print(f"✅ Streaming completado correctamente en {duration:.2f}s")
            print(f"   Contenido final: {len(final_message.content)} caracteres")
            return True
        else:
            print(f"❌ Error: contenido final no coincide")
            return False

    async def test_typing_indicators(self):
        """Test de typing indicators"""
        print("\n⌨️  Test 2: Typing indicators...")

        # Set typing indicator
        await self.manager._set_typing_indicator(
            self.session.session_id,
            "Claude está pensando en una respuesta...",
            3000
        )

        # Verificar que se guardó
        indicator = self.manager._typing_indicators.get(self.session.session_id)
        if indicator and indicator.is_typing:
            print("✅ Typing indicator configurado correctamente")

            # Limpiar
            await self.manager._clear_typing_indicator(self.session.session_id)

            # Verificar que se limpió
            if self.session.session_id not in self.manager._typing_indicators:
                print("✅ Typing indicator limpiado correctamente")
                return True
            else:
                print("❌ Error: typing indicator no se limpió")
                return False
        else:
            print("❌ Error: typing indicator no se configuró")
            return False

    async def test_connection_management(self):
        """Test de connection management"""
        print("\n🔗 Test 3: Connection management...")

        # Simular conexión (mock websocket)
        class MockWebSocket:
            def __init__(self):
                self.sent_messages = []

            async def send_text(self, data):
                self.sent_messages.append(data)

        mock_ws = MockWebSocket()

        # Registrar conexión
        client_id = await self.manager.register_streaming_connection(
            mock_ws, self.session.session_id, "websocket"
        )

        print(f"✅ Conexión registrada: {client_id}")

        # Actualizar quality metrics
        await self.manager.update_connection_quality(client_id, 45.5, 0.95)

        # Verificar health
        health_info = await self.manager.check_connection_health(client_id)
        if health_info.get("is_healthy"):
            print("✅ Connection health verificado")
        else:
            print("❌ Connection health check falló")
            return False

        # Cleanup
        await self.manager.unregister_streaming_connection(client_id)
        print("✅ Conexión limpiada")

        return True

    async def test_performance(self):
        """Test de performance con mensaje largo"""
        print("\n⚡ Test 4: Performance con mensaje largo...")

        # Crear mensaje largo
        long_content = "Este es un test de performance. " * 50  # ~1500 caracteres

        start_time = time.time()
        message = await self.manager.start_message_streaming(
            session_id=self.session.session_id,
            message_content=long_content,
            typing_speed_wpm=500.0,  # Muy rápido
            include_thinking_time=False
        )

        # Esperar a que termine
        streaming_state = await self.manager.get_streaming_state(self.session.session_id)
        while streaming_state and streaming_state.is_active:
            await asyncio.sleep(0.05)
            streaming_state = await self.manager.get_streaming_state(self.session.session_id)

        end_time = time.time()
        duration = end_time - start_time
        chars_per_second = len(long_content) / duration

        print(f"✅ Performance test completado:")
        print(f"   Caracteres: {len(long_content)}")
        print(f"   Tiempo: {duration:.2f}s")
        print(f"   Velocidad: {chars_per_second:.1f} chars/s")

        # Validar que es razonable (para streaming realista)
        if chars_per_second > 20:  # Al menos 20 chars/s (realista para typing)
            print("✅ Performance aceptable para streaming realista")
            return True
        else:
            print("❌ Performance demasiado lenta incluso para streaming")
            return False

    async def test_connection_stats(self):
        """Test de estadísticas de conexión"""
        print("\n📊 Test 5: Connection statistics...")

        stats = await self.manager.get_connection_stats()

        expected_keys = [
            "total_connections", "active_connections", "connection_types",
            "quality_metrics", "streaming_stats", "generated_at"
        ]

        for key in expected_keys:
            if key not in stats:
                print(f"❌ Falta key en stats: {key}")
                return False

        print("✅ Connection stats generadas correctamente")
        print(f"   Total connections: {stats['total_connections']}")
        print(f"   Active connections: {stats['active_connections']}")
        print(f"   Active streaming sessions: {stats['streaming_stats']['active_streaming_sessions']}")

        return True

    async def run_all_tests(self):
        """Ejecutar todos los tests"""
        print("🧪 Iniciando CHAT-04 Streaming Tests...")
        print("=" * 50)

        # Setup
        if not await self.setup():
            print("❌ Setup falló")
            return False

        # Lista de tests
        tests = [
            ("Streaming Básico", self.test_basic_streaming),
            ("Typing Indicators", self.test_typing_indicators),
            ("Connection Management", self.test_connection_management),
            ("Performance", self.test_performance),
            ("Connection Stats", self.test_connection_stats)
        ]

        results = {}

        # Ejecutar tests
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results[test_name] = result
                if result:
                    print(f"✅ {test_name}: PASS")
                else:
                    print(f"❌ {test_name}: FAIL")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
                results[test_name] = False

        # Resumen
        print("\n" + "=" * 50)
        print("📋 RESUMEN DE TESTS:")

        passed = sum(1 for result in results.values() if result)
        total = len(results)

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")

        print(f"\n🎯 Resultado final: {passed}/{total} tests pasaron")

        if passed == total:
            print("🎉 ¡Todos los tests pasaron! CHAT-04 streaming está funcionando correctamente.")
            return True
        else:
            print("⚠️  Algunos tests fallaron. Revisar implementación.")
            return False


async def main():
    """Función principal del test"""
    tester = StreamingTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrumpidos por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(1)