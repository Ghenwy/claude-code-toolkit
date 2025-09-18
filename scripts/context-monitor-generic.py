#!/usr/bin/env python3
"""
Claude Code Context Monitor v2.0 - Generic Version
Real-time context usage monitoring with claude-monitor algorithm replication
"""

import json
import sys
import os
import re
import subprocess
import psutil
from datetime import datetime
import tempfile
import time

def parse_context_from_transcript(transcript_path):
    """ENHANCED context estimation using REAL token data from transcript v3.0."""
    if not transcript_path:
        return {
            'percent': 15,
            'method': 'no_transcript',
            'accurate': False
        }

    if not os.path.exists(transcript_path):
        return {
            'percent': 15,
            'method': 'file_missing',
            'accurate': False
        }

    try:
        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        # Check last 30 lines for Claude's REAL system warnings (most accurate)
        recent_lines = lines[-30:] if len(lines) > 30 else lines

        # PRIORITY 1: Look for Claude system warnings (100% accurate)
        for line in reversed(recent_lines):
            try:
                data = json.loads(line.strip())

                if data.get('type') == 'system_message':
                    content = data.get('content', '')

                    # "Context low (X% remaining)" - MOST ACCURATE
                    match = re.search(r'Context low \((\d+)% remaining\)', content)
                    if match:
                        percent_left = int(match.group(1))
                        return {
                            'percent': 100 - percent_left,
                            'warning': 'low',
                            'method': 'claude_system',
                            'accurate': True
                        }

                    # "Context left until auto-compact: X%" - ACCURATE
                    match = re.search(r'Context left until auto-compact: (\d+)%', content)
                    if match:
                        percent_left = int(match.group(1))
                        return {
                            'percent': 100 - percent_left,
                            'warning': 'auto-compact',
                            'method': 'claude_system',
                            'accurate': True
                        }

            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        # PRIORITY 2: Use REAL token data from messages (MUCH MORE ACCURATE)
        max_tokens_seen = 0
        total_input_tokens = 0
        total_cache_tokens = 0
        message_count = 0

        # Claude Sonnet 4 context limit (200K tokens typical)
        CONTEXT_LIMIT = 200000

        for line in reversed(recent_lines):
            try:
                data = json.loads(line.strip())

                if data.get('type') == 'assistant':
                    message = data.get('message', {})
                    usage = message.get('usage', {})

                    if usage:
                        # Get real token counts
                        input_tokens = usage.get('input_tokens', 0)
                        cache_read = usage.get('cache_read_input_tokens', 0)
                        cache_creation = usage.get('cache_creation_input_tokens', 0)

                        # Track maximum tokens seen (most recent and complete picture)
                        current_total = input_tokens + cache_read + cache_creation
                        if current_total > max_tokens_seen:
                            max_tokens_seen = current_total
                            total_input_tokens = input_tokens
                            total_cache_tokens = cache_read + cache_creation

                        message_count += 1
                        if message_count >= 5:  # Look at last 5 messages for most recent data
                            break

            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        # Calculate real context percentage if we have token data
        if max_tokens_seen > 0:
            real_percent = min(99, (max_tokens_seen / CONTEXT_LIMIT) * 100)

            # Determine accuracy based on data quality
            if total_cache_tokens > 0:
                # Cache tokens indicate active context management - very accurate
                return {
                    'percent': real_percent,
                    'tokens_used': max_tokens_seen,
                    'cache_tokens': total_cache_tokens,
                    'method': 'real_tokens_with_cache',
                    'accurate': True
                }
            else:
                # Input tokens only - moderately accurate
                return {
                    'percent': real_percent,
                    'tokens_used': max_tokens_seen,
                    'method': 'real_tokens_basic',
                    'accurate': True
                }

        # FALLBACK: Improved estimation based on message characteristics
        conversation_depth = 0
        total_content_length = 0

        for line in reversed(recent_lines):
            try:
                data = json.loads(line.strip())
                if data.get('type') in ['assistant', 'user']:
                    conversation_depth += 1

                    # Estimate content length for better calculation
                    message = data.get('message', {})
                    content = message.get('content', [])
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                total_content_length += len(item.get('text', ''))

                    if conversation_depth >= 15:  # Look at more context for better estimation
                        break

            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        if conversation_depth > 0:
            # Enhanced estimation considering conversation depth and content length
            base_percent = min(20, conversation_depth * 1.5)  # More gradual increase
            content_factor = min(30, total_content_length / 1000)  # Content length factor
            estimated_percent = min(85, base_percent + content_factor)

            return {
                'percent': estimated_percent,
                'messages': conversation_depth,
                'content_length': total_content_length,
                'method': 'enhanced_estimate',
                'accurate': False
            }

        return {
            'percent': 15,
            'method': 'default',
            'accurate': False
        }

    except (FileNotFoundError, PermissionError):
        return {
            'percent': 15,
            'method': 'error',
            'accurate': False
        }

def get_context_display(context_info):
    """Generate context display with ENHANCED indicators using real token data."""
    if not context_info:
        return "🔵 ???%"

    percent = context_info.get('percent', 0)
    warning = context_info.get('warning')
    accurate = context_info.get('accurate', False)
    method = context_info.get('method', '')
    tokens_used = context_info.get('tokens_used', 0)

    # Color and icon based on usage level
    if warning == 'low' or warning == 'auto-compact':
        # REAL Claude system warnings
        icon, color = "🔴", "\033[31;1m"  # Blinking red
    elif method.startswith('real_tokens') and percent >= 90:
        # Real token data shows very high usage
        icon, color = "🔴", "\033[31m"   # Red
    elif method.startswith('real_tokens') and percent >= 75:
        # Real token data shows high usage
        icon, color = "🟠", "\033[91m"   # Orange
    elif method.startswith('real_tokens') and percent >= 50:
        # Real token data shows moderate usage
        icon, color = "🟡", "\033[33m"   # Yellow
    elif method.startswith('real_tokens'):
        # Real token data shows low usage
        icon, color = "🟢", "\033[32m"   # Green
    elif accurate and percent >= 85:
        # Other accurate methods with high usage
        icon, color = "🟠", "\033[91m"   # Orange
    elif accurate and percent >= 70:
        # Other accurate methods with moderate usage
        icon, color = "🟡", "\033[33m"   # Yellow
    elif accurate:
        # Other accurate methods with low usage
        icon, color = "🟢", "\033[32m"   # Green
    else:
        # Estimated values - less reliable
        if percent >= 80:
            icon, color = "🟠", "\033[91m"   # Orange
        elif percent >= 60:
            icon, color = "🟡", "\033[33m"   # Yellow
        else:
            icon, color = "🟢", "\033[32m"   # Green

    # Create progress bar
    segments = 4
    filled = int((percent / 100) * segments)
    bar = "█" * filled + "▁" * (segments - filled)

    reset = "\033[0m"

    # Enhanced accuracy indicator based on method
    if method.startswith('real_tokens'):
        if 'cache' in method:
            accuracy_indicator = "✓"  # Real tokens with cache - highest accuracy
        else:
            accuracy_indicator = ""   # Real tokens basic - high accuracy
    elif accurate:
        accuracy_indicator = ""       # Other accurate methods
    else:
        accuracy_indicator = "~"      # Estimated

    # Add token count for real data (debugging aid)
    if tokens_used > 0 and method.startswith('real_tokens'):
        token_display = f" ({tokens_used//1000}k)"
    else:
        token_display = ""

    return f"{icon} {color}{bar}{reset} {accuracy_indicator}{percent:.0f}%{token_display}"

def get_directory_display(workspace_data):
    """Get directory display name."""
    current_dir = workspace_data.get('current_dir', '')
    project_dir = workspace_data.get('project_dir', '')

    if current_dir and project_dir:
        if current_dir.startswith(project_dir):
            rel_path = current_dir[len(project_dir):].lstrip('/')
            return rel_path or os.path.basename(project_dir)
        else:
            return os.path.basename(current_dir)
    elif project_dir:
        return os.path.basename(project_dir)
    elif current_dir:
        return os.path.basename(current_dir)
    else:
        return "unknown"

def get_git_info():
    """Get Git branch information robustly."""
    try:
        # Get current branch
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            branch = result.stdout.strip()

            # Get commit status (ahead/behind)
            status_result = subprocess.run(['git', 'status', '--porcelain', '-b'],
                                         capture_output=True, text=True, timeout=2)

            if status_result.returncode == 0:
                status_lines = status_result.stdout.strip().split('\n')
                if status_lines:
                    # Parse first line for ahead/behind info
                    first_line = status_lines[0]
                    ahead_behind = ""
                    if 'ahead' in first_line:
                        ahead_match = re.search(r'ahead (\d+)', first_line)
                        if ahead_match:
                            ahead_behind += f"↑{ahead_match.group(1)}"
                    if 'behind' in first_line:
                        behind_match = re.search(r'behind (\d+)', first_line)
                        if behind_match:
                            ahead_behind += f"↓{behind_match.group(1)}"

                    # Count modified files
                    modified_count = len([line for line in status_lines[1:] if line.strip()])
                    if modified_count > 0:
                        ahead_behind += f" *{modified_count}"

                    if ahead_behind:
                        return f"🌿{branch}{ahead_behind}"
                    else:
                        return f"🌿{branch}"

            return f"🌿{branch}"
        else:
            return "🌿-"
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return "🌿-"

def get_claude_session_data_claude_monitor_exact():
    """EXACT replication of claude-monitor algorithm - v2.0 implementation."""
    try:
        import glob
        import json
        from datetime import datetime, timedelta, timezone

        # Use generic home directory
        claude_dir = os.path.expanduser('~/.claude')

        # EXACT claude-monitor parameters
        hours_back = 192  # 8 days like DataManager
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=hours_back)

        # Find JSONL files (same pattern as claude-monitor)
        recent_files = []
        patterns = [
            os.path.join(claude_dir, '*.jsonl'),
            os.path.join(claude_dir, 'projects', '*', '*.jsonl')
        ]

        for pattern in patterns:
            for file_path in glob.glob(pattern):
                if os.path.isfile(file_path):
                    recent_files.append(file_path)

        if not recent_files:
            return {}

        # Load usage entries with EXACT claude-monitor deduplication
        all_entries = []
        processed_hashes = set()  # CRITICAL: Deduplication like claude-monitor

        for file_path in recent_files:
            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        if line.strip():
                            try:
                                data = json.loads(line.strip())
                                if data.get('type') == 'assistant':
                                    timestamp_str = data.get('timestamp')
                                    if timestamp_str:
                                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

                                        # Only include entries within hours_back window
                                        if timestamp >= cutoff_time:
                                            # EXACT deduplication logic from claude-monitor
                                            message = data.get("message", {})
                                            message_id = data.get("message_id") or (
                                                message.get("id") if isinstance(message, dict) else None
                                            )
                                            request_id = data.get("requestId") or data.get("request_id")

                                            # Create unique hash for deduplication
                                            unique_hash = None
                                            if message_id and request_id:
                                                unique_hash = f"{message_id}:{request_id}"

                                            # Skip if already processed (EXACT claude-monitor logic)
                                            if unique_hash and unique_hash in processed_hashes:
                                                continue

                                            usage = data.get('message', {}).get('usage', {})
                                            if usage:
                                                # EXACT token counting like claude-monitor
                                                input_tokens = usage.get('input_tokens', 0)
                                                output_tokens = usage.get('output_tokens', 0)

                                                # Skip entries with no valid tokens (claude-monitor validation)
                                                if input_tokens == 0 and output_tokens == 0:
                                                    continue

                                                entry = {
                                                    'timestamp': timestamp,
                                                    'input_tokens': input_tokens,
                                                    'output_tokens': output_tokens,
                                                    'total_tokens': input_tokens + output_tokens,  # EXACT calculation
                                                    'message_id': message_id or "",
                                                    'request_id': request_id or "unknown",
                                                    'file': file_path
                                                }
                                                all_entries.append(entry)

                                                # Add to processed hashes
                                                if unique_hash:
                                                    processed_hashes.add(unique_hash)
                            except:
                                continue
            except:
                continue

        if not all_entries:
            return {}

        # Sort by timestamp (like SessionAnalyzer)
        all_entries.sort(key=lambda x: x['timestamp'])

        # Transform to blocks (replicating SessionAnalyzer.transform_to_blocks)
        session_blocks = []
        current_block = None
        session_duration = timedelta(hours=5)  # EXACT session_duration_hours=5

        for entry in all_entries:
            entry_time = entry['timestamp']

            # EXACT rolling block detection logic from claude-monitor
            should_create_new_block = (
                current_block is None or
                entry_time >= current_block['end_time'] or
                (current_block['entries'] and
                 entry_time - current_block['entries'][-1]['timestamp'] >= timedelta(hours=2))
            )

            if should_create_new_block:
                # Finalize previous block
                if current_block and current_block['entries']:
                    current_block['actual_end_time'] = current_block['entries'][-1]['timestamp']
                    session_blocks.append(current_block)

                # Create new rolling block
                start_time = entry_time.replace(minute=0, second=0, microsecond=0)  # Hour rounding
                end_time = start_time + session_duration

                current_block = {
                    'id': start_time.isoformat(),
                    'start_time': start_time,
                    'end_time': end_time,
                    'entries': [],
                    'total_tokens': 0,
                    'is_active': False
                }

            # Add entry to current block
            current_block['entries'].append(entry)
            current_block['total_tokens'] += entry['total_tokens']

        # Finalize last block
        if current_block and current_block['entries']:
            current_block['actual_end_time'] = current_block['entries'][-1]['timestamp']
            session_blocks.append(current_block)

        # Mark active blocks (EXACT logic from claude-monitor)
        for block in session_blocks:
            # Block must be future AND have recent activity (within 30 minutes)
            if (block['end_time'] > now and
                len(block['entries']) >= 3 and
                block['entries'] and
                (now - block['entries'][-1]['timestamp']).total_seconds() <= 1800):
                block['is_active'] = True

        # Find active blocks
        active_blocks = [b for b in session_blocks if b['is_active']]

        if active_blocks:
            # Most recent active block
            current_session = max(active_blocks, key=lambda x: x['start_time'])

            return {
                'reset_time': current_session['end_time'].astimezone().strftime('%H:%M'),
                'cost_percent': (current_session['total_tokens'] / 88000) * 100,
                'tokens_used': current_session['total_tokens'],
                'session_active': True,
                'block_id': current_session['id'],
                'session_blocks': len(session_blocks),
                'approach': 'claude_monitor_exact'
            }
        else:
            # No active session
            if session_blocks:
                latest_block = max(session_blocks, key=lambda x: x['start_time'])
                return {
                    'reset_time': 'EXPIRED',
                    'cost_percent': 100.0,
                    'tokens_used': latest_block['total_tokens'],
                    'session_active': False,
                    'approach': 'claude_monitor_exact'
                }

        return {}

    except Exception:
        return {}

def get_claude_session_reset():
    """Get Claude session reset time using exact claude-monitor replication."""
    session_data = get_claude_session_data_claude_monitor_exact()
    if not session_data:
        return "L.R. @ --:--"

    reset_time = session_data.get('reset_time', '')
    approach = session_data.get('approach', 'original')

    if reset_time == 'EXPIRED':
        return "L.R. EXPIRED"
    elif reset_time:
        return f"L.R. @ {reset_time}🕐"
    else:
        return "L.R. @ --:--"

def get_cost_usage():
    """Get Claude cost usage with exact claude-monitor replication."""
    session_data = get_claude_session_data_claude_monitor_exact()
    if not session_data or 'cost_percent' not in session_data:
        return "C.U. 🔵??%"

    percent = session_data.get('cost_percent', 0)
    session_active = session_data.get('session_active', False)
    approach = session_data.get('approach', 'original')

    # Special handling for expired sessions
    if not session_active:
        return "C.U. 🔴█████EXP"

    # Normalize display percentage for better visual representation
    display_percent = min(100, percent / 1.50)

    # Color and icon based on cost usage level (claude-monitor compatible)
    if percent >= 95:
        icon, color = "🔴", "\033[31;1m"  # Blinking red
    elif percent >= 90:
        icon, color = "🔴", "\033[31m"    # Red
    elif percent >= 75:
        icon, color = "🟠", "\033[91m"   # Orange
    elif percent >= 60:
        icon, color = "🟡", "\033[33m"   # Yellow
    else:
        icon, color = "🟢", "\033[32m"   # Green

    # Create progress bar
    segments = 4
    filled = int((display_percent / 100) * segments)
    bar = "█" * filled + "▁" * (segments - filled)

    reset = "\033[0m"

    return f"C.U. {icon} {color}{bar}{reset} {display_percent:.0f}%"

def get_live_datetime():
    """Get current date and time in compact format."""
    try:
        now = datetime.now()
        return f"⌚ {now.strftime('%H:%M %b %d')}"
    except Exception:
        return "⌚ --:--"

def main():
    try:
        # Read JSON input from Claude Code
        data = json.load(sys.stdin)

        # Extract information
        model_name = data.get('model', {}).get('display_name', 'Claude')
        workspace = data.get('workspace', {})
        transcript_path = data.get('transcript_path', '')

        # Parse context usage
        context_info = parse_context_from_transcript(transcript_path)

        # Build status components
        context_display = get_context_display(context_info)
        directory = get_directory_display(workspace)

        # Get additional system information
        git_info = get_git_info()

        # Get claude-monitor exact metrics
        claude_reset = get_claude_session_reset()  # L.R. @ time⚡
        cost_usage = get_cost_usage()  # C.U. with percentage⚡
        live_datetime = get_live_datetime()

        # Build 3 clean sections (v2.0 structure)

        # Section 1: Project Context (removed model display)
        section1 = f"\033[93m📁 {directory}\033[0m {git_info}"

        # Section 2: Claude Context
        section2 = f"{context_display}"

        # Section 3: Real Claude Session Data⚡
        section3 = f"{claude_reset} {cost_usage} {live_datetime}"

        # Combine all sections with || separators (exactly 3 sections)
        separator = " \033[90m|\033[0m "
        status_line = f"{section1}{separator}{section2}{separator}{section3}"

        print(status_line)

    except Exception as e:
        # Fallback display on any error
        try:
            git_fallback = get_git_info()
            claude_reset_fallback = get_claude_session_reset()
            cost_usage_fallback = get_cost_usage()
            datetime_fallback = get_live_datetime()

            # Structured fallback with 3 sections (removed model display)
            section1_fallback = f"\033[93m📁 {os.path.basename(os.getcwd())}\033[0m {git_fallback}"
            section2_fallback = f"\033[31m[Error]\033[0m"
            section3_fallback = f"{claude_reset_fallback} {cost_usage_fallback} {datetime_fallback}"

            separator = " \033[90m|\033[0m "
            fallback_line = f"{section1_fallback}{separator}{section2_fallback}{separator}{section3_fallback}"
            print(fallback_line)
        except:
            # Ultimate fallback (3 sections structure maintained, removed model display)
            separator = " \033[90m|\033[0m "
            print(f"\033[93m📁 {os.path.basename(os.getcwd())}\033[0m 🌿-{separator}\033[31m[Error: {str(e)[:20]}]\033[0m{separator}L.R. @ --:-- C.U. 🔵 ??% ⌚ --:--")

if __name__ == "__main__":
    main()