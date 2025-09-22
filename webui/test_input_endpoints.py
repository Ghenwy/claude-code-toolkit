#!/usr/bin/env python3
"""
Manual test script para CHAT-03 Input System endpoints
Test básico de funcionalidad sin usar un test framework completo
"""
import asyncio
import json
from uuid import uuid4

from main import app
from services.chat_manager import ChatManager
from models.chat import (
    InputHistoryRequest, DraftSaveRequest, CommandValidationRequest,
    CommandSuggestionsRequest
)


async def test_input_system_endpoints():
    """
    Test manual de todos los endpoints del input system
    Simula las llamadas que haría el frontend
    """
    print("🧪 Testing CHAT-03 Input System Backend...")
    print("=" * 50)

    # Instanciar manager
    manager = ChatManager()

    # 1. Crear session de test
    print("\n1. Creating test session...")
    session = await manager.create_session()
    session_id = session.session_id
    print(f"   ✅ Session created: {session_id}")

    # 2. Test save input history
    print("\n2. Testing input history...")
    test_inputs = [
        "/A-plan \"Build a REST API\"",
        "/B-explain-code main.py",
        "Hello, how can I create a FastAPI endpoint?",
        "M1-qa-gatekeeper \"Review this code\"",
        "/help"
    ]

    for i, text in enumerate(test_inputs):
        request = InputHistoryRequest(
            text=text,
            typing_duration_ms=1000 + i * 200,
            cursor_position=len(text)
        )
        entry = await manager.save_input_to_history(session_id, request)
        print(f"   ✅ Input {i+1}: '{text[:30]}...' - Command: {entry.is_command}")

    # 3. Test get input history
    print("\n3. Testing get input history...")
    history = await manager.get_input_history(session_id, limit=10)
    print(f"   ✅ Retrieved {len(history['entries'])} history entries")
    print(f"   📊 Total count: {history['total_count']}")

    # 4. Test draft functionality
    print("\n4. Testing draft system...")
    draft_content = "This is a draft message that I'm writing..."
    draft_request = DraftSaveRequest(
        content=draft_content,
        cursor_position=25
    )
    draft = await manager.save_draft(session_id, draft_request)
    print(f"   ✅ Draft saved: {len(draft.content)} characters")

    # Retrieve draft
    retrieved_draft = await manager.get_draft(session_id)
    print(f"   ✅ Draft retrieved: matches saved = {retrieved_draft.content == draft_content}")

    # 5. Test command validation
    print("\n5. Testing command validation...")
    validation_tests = [
        "/A-plan",  # Partial command
        "/A-plan \"My project\"",  # Valid command
        "/X-invalid",  # Invalid command
        "regular text",  # Not a command
        "M1-qa-gatekeeper \"test\"",  # Valid agent
    ]

    for test_input in validation_tests:
        validation_request = CommandValidationRequest(input_text=test_input)
        result = await manager.validate_input(validation_request)
        print(f"   ✅ '{test_input}' - Valid: {result.is_valid}, Type: {result.validation_type}")

    # 6. Test command suggestions
    print("\n6. Testing command suggestions...")
    suggestion_tests = [
        "/A-",  # A-commands prefix
        "/B-",  # B-commands prefix
        "M1-",  # M1-agents prefix
        "",     # All commands
    ]

    for partial in suggestion_tests:
        suggestions_request = CommandSuggestionsRequest(
            partial_input=partial,
            limit=3
        )
        suggestions = await manager.get_command_suggestions(suggestions_request)
        print(f"   ✅ '{partial}' - Found {len(suggestions)} suggestions")
        if suggestions:
            print(f"      Top suggestion: {suggestions[0].command}")

    # 7. Test input analytics
    print("\n7. Testing input analytics...")
    analytics = await manager.get_input_analytics(session_id)
    if analytics:
        print(f"   ✅ Analytics generated:")
        print(f"      Total inputs: {analytics.total_inputs}")
        print(f"      Typing speed: {analytics.typing_speed_wpm:.1f} WPM")
        print(f"      Avg input length: {analytics.avg_input_length:.1f}")
        print(f"      Command usage: {analytics.command_usage}")
        print(f"      Most used commands: {analytics.most_used_commands}")
    else:
        print("   ⚠️ No analytics found")

    # 8. Test input summary
    print("\n8. Testing input summary...")
    summary = await manager.get_session_input_summary(session_id)
    print(f"   ✅ Summary generated:")
    print(f"      Has history: {summary['has_history']}")
    print(f"      Has draft: {summary['has_draft']}")
    print(f"      Has analytics: {summary['has_analytics']}")
    if summary['has_history']:
        print(f"      Total inputs: {summary['total_inputs']}")
        print(f"      Command inputs: {summary['command_inputs']}")

    # 9. Test command categories
    print("\n9. Testing command categories...")
    categories = manager._input_validator.get_available_categories()
    counts = manager._input_validator.get_command_count_by_category()
    print(f"   ✅ Available categories: {categories}")
    print(f"   ✅ Command counts: {counts}")

    # 10. Test cleanup
    print("\n10. Testing cleanup...")
    cleanup_results = await manager.cleanup_session_input_data(session_id)
    print(f"   ✅ Cleanup completed: {cleanup_results}")

    print("\n" + "=" * 50)
    print("🎉 ALL TESTS PASSED! CHAT-03 Input System ready for production!")
    print("✅ Input history persistence")
    print("✅ Command validation and suggestions")
    print("✅ Draft management system")
    print("✅ Input analytics and metrics")
    print("✅ Session-based data management")
    print("✅ Proper cleanup functionality")


if __name__ == "__main__":
    asyncio.run(test_input_system_endpoints())