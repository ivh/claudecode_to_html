#!/usr/bin/env python3
"""
Convert Claude Code session logs (.jsonl) to HTML.

Usage: python claudecode_to_html.py input.jsonl [output.html]
"""

import json
import sys
import os
import re
import difflib
from html import escape
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class SessionRenderer:
    """Renders Claude Code session logs as HTML."""

    TOOL_COLORS = {
        'Read': '#3b82f6',     # blue
        'Write': '#10b981',    # green
        'Edit': '#f59e0b',     # orange
        'Bash': '#22c55e',     # green
        'Grep': '#8b5cf6',     # purple
        'Glob': '#ec4899',     # pink
        'Task': '#06b6d4',     # cyan
        'WebFetch': '#14b8a6', # teal
        'WebSearch': '#f97316',# orange
        'TodoWrite': '#a855f7',# purple
        'default': '#6b7280'   # gray
    }

    def __init__(self, jsonl_path: str):
        self.jsonl_path = jsonl_path
        self.messages = []
        self.load_messages()

    def load_messages(self):
        """Load and parse JSONL file."""
        with open(self.jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get('type') in ['user', 'assistant', 'system']:
                        self.messages.append(data)
                except json.JSONDecodeError:
                    continue

    def calculate_session_timing(self) -> Dict[str, Any]:
        """Calculate session timing statistics."""
        if not self.messages:
            return {
                'total_duration': timedelta(0),
                'claude_working_time': timedelta(0),
                'waiting_for_user_time': timedelta(0)
            }

        # Extract messages with timestamps
        timestamped_messages = []
        for msg in self.messages:
            timestamp_str = msg.get('timestamp')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    timestamped_messages.append({
                        'type': msg.get('type'),
                        'timestamp': timestamp
                    })
                except (ValueError, AttributeError):
                    continue

        if len(timestamped_messages) < 2:
            return {
                'total_duration': timedelta(0),
                'claude_working_time': timedelta(0),
                'waiting_for_user_time': timedelta(0)
            }

        # Calculate total session duration
        first_timestamp = timestamped_messages[0]['timestamp']
        last_timestamp = timestamped_messages[-1]['timestamp']
        total_duration = last_timestamp - first_timestamp

        # Calculate Claude working time and waiting for user time
        claude_working_time = timedelta(0)
        waiting_for_user_time = timedelta(0)

        for i in range(1, len(timestamped_messages)):
            prev_msg = timestamped_messages[i - 1]
            curr_msg = timestamped_messages[i]
            time_diff = curr_msg['timestamp'] - prev_msg['timestamp']

            # If previous message was from user, next message is Claude working
            if prev_msg['type'] == 'user' and curr_msg['type'] == 'assistant':
                claude_working_time += time_diff
            # If previous message was from assistant, next message is waiting for user
            elif prev_msg['type'] == 'assistant' and curr_msg['type'] == 'user':
                waiting_for_user_time += time_diff

        return {
            'total_duration': total_duration,
            'claude_working_time': claude_working_time,
            'waiting_for_user_time': waiting_for_user_time
        }

    def format_timedelta(self, td: timedelta) -> str:
        """Format a timedelta in a human-readable way."""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        return ' '.join(parts)

    def render_markdown(self, text: str) -> str:
        """Simple markdown to HTML conversion."""
        if not text:
            return ''

        # Process code blocks FIRST (before escaping)
        code_blocks = []
        def save_code_block(match):
            code_blocks.append(match.group(0))
            return f'___CODE_BLOCK_{len(code_blocks) - 1}___'

        text = re.sub(r'```(\w+)?\n(.*?)```', save_code_block, text, flags=re.DOTALL)

        # Process markdown on the text (WITHOUT code blocks)
        # Headers (process before escaping so we can convert them)
        text = re.sub(r'^### (.+)$', r'___H3_START___\1___H3_END___', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'___H2_START___\1___H2_END___', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'___H1_START___\1___H1_END___', text, flags=re.MULTILINE)

        # Now escape the remaining text
        html = escape(text)

        # Convert header placeholders to HTML (after escaping)
        html = html.replace('___H3_START___', '<h3>').replace('___H3_END___', '</h3>')
        html = html.replace('___H2_START___', '<h2>').replace('___H2_END___', '</h2>')
        html = html.replace('___H1_START___', '<h1>').replace('___H1_END___', '</h1>')

        # Inline code
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

        # Bold
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

        # Italic
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Line breaks (do this BEFORE restoring code blocks so breaks aren't added inside code)
        html = html.replace('\n', '<br>\n')

        # Restore code blocks with proper HTML
        for i, block in enumerate(code_blocks):
            match = re.match(r'```(\w+)?\n(.*?)```', block, flags=re.DOTALL)
            if match:
                lang = match.group(1) or ''
                code = escape(match.group(2))
                # Don't add <br> tags - code blocks preserve their own newlines
                html = html.replace(f'___CODE_BLOCK_{i}___<br>\n',
                                   f'<pre><code class="language-{lang}">{code}</code></pre>')

        return html

    def render_tool_use(self, tool: Dict[str, Any]) -> str:
        """Render a tool use block."""
        tool_name = tool.get('name', 'Unknown')
        tool_input = tool.get('input', {})
        color = self.TOOL_COLORS.get(tool_name, self.TOOL_COLORS['default'])

        # Format input parameters
        params = []
        for key, value in tool_input.items():
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + '...'
            params.append(f'{key}={repr(value)}')

        params_str = ', '.join(params) if params else ''

        return f'''
        <div class="tool-use">
            <div class="tool-header">
                <span class="tool-dot" style="background-color: {color}"></span>
                <span class="tool-name">{escape(tool_name)}</span>
                {f'<span class="tool-params">{escape(params_str)}</span>' if params_str else ''}
            </div>
        </div>
        '''

    def render_edit_diff(self, old_string: str, new_string: str, file_path: str = '') -> str:
        """Render a diff for Edit tool results."""
        # Generate unified diff
        old_lines = old_string.splitlines(keepends=True)
        new_lines = new_string.splitlines(keepends=True)

        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))

        if not diff:
            return '<div class="tool-result"><pre><code>No changes</code></pre></div>'

        # Skip the diff header lines (---, +++, @@)
        diff_body = []
        old_line_num = 0
        new_line_num = 0

        for line in diff[2:]:  # Skip first two lines (--- and +++)
            if line.startswith('@@'):
                # Parse line numbers from @@ -old_start,old_count +new_start,new_count @@
                match = re.match(r'@@ -(\d+),?\d* \+(\d+),?\d* @@', line)
                if match:
                    old_line_num = int(match.group(1)) - 1
                    new_line_num = int(match.group(2)) - 1
                continue

            if line.startswith('-'):
                old_line_num += 1
                diff_body.append({
                    'type': 'delete',
                    'old_line': old_line_num,
                    'new_line': '',
                    'content': line[1:]
                })
            elif line.startswith('+'):
                new_line_num += 1
                diff_body.append({
                    'type': 'add',
                    'old_line': '',
                    'new_line': new_line_num,
                    'content': line[1:]
                })
            else:
                # Context line
                old_line_num += 1
                new_line_num += 1
                diff_body.append({
                    'type': 'context',
                    'old_line': old_line_num,
                    'new_line': new_line_num,
                    'content': line[1:] if line.startswith(' ') else line
                })

        # Build HTML
        html_lines = []
        if file_path:
            html_lines.append(f'<div class="diff-file-header">• Edit {escape(file_path)}</div>')

        # Check if we should collapse
        total_lines = len(diff_body)
        should_collapse = total_lines > 10

        if should_collapse:
            # Show first 5 lines
            preview_html = self._render_diff_lines(diff_body[:5])
            full_html = self._render_diff_lines(diff_body)
            hidden_count = total_lines - 5

            return f'''
            <div class="edit-diff collapsible">
                {html_lines[0] if html_lines else ''}
                <div class="diff-preview">
                    {preview_html}
                    <div class="diff-expand-link" onclick="this.parentElement.parentElement.classList.toggle('expanded')">
                        Show full diff ({hidden_count} more lines)
                    </div>
                </div>
                <div class="diff-full">
                    {full_html}
                </div>
            </div>
            '''
        else:
            diff_html = self._render_diff_lines(diff_body)
            return f'''
            <div class="edit-diff">
                {html_lines[0] if html_lines else ''}
                {diff_html}
            </div>
            '''

    def _render_diff_lines(self, diff_lines: List[Dict[str, Any]]) -> str:
        """Render diff lines as HTML."""
        html = '<div class="diff-lines">'
        for line in diff_lines:
            line_type = line['type']
            old_num = line['old_line']
            new_num = line['new_line']
            content = escape(line['content'].rstrip('\n'))

            if line_type == 'delete':
                prefix = '-'
                css_class = 'diff-del'
            elif line_type == 'add':
                prefix = '+'
                css_class = 'diff-add'
            else:
                prefix = ''
                css_class = 'diff-context'

            html += f'''<div class="diff-line {css_class}">
                <span class="diff-line-num old">{old_num if old_num else ''}</span>
                <span class="diff-line-num new">{new_num if new_num else ''}</span>
                <span class="diff-prefix">{prefix}</span>
                <span class="diff-content">{content}</span>
            </div>'''

        html += '</div>'
        return html

    def render_tool_result(self, result: Dict[str, Any], tool_name: str = '', tool_input: Dict[str, Any] = None) -> str:
        """Render a tool result block."""
        # Handle Edit tool specially - show diff
        if tool_name == 'Edit' and tool_input:
            old_string = tool_input.get('old_string', '')
            new_string = tool_input.get('new_string', '')
            file_path = tool_input.get('file_path', '')
            return self.render_edit_diff(old_string, new_string, file_path)

        content = result.get('content', '')

        # Handle list content (for structured results)
        if isinstance(content, list):
            # For now, just join text items
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                elif isinstance(item, str):
                    text_parts.append(item)
            content = '\n'.join(text_parts)

        if not content:
            return ''

        # Check if it's a long file read (has line numbers)
        is_file_content = '→' in content and '\n' in content
        lines = content.split('\n')

        # Bash and Grep should be collapsed by default, showing only 3 lines
        if tool_name in ['Bash', 'Grep']:
            if len(lines) > 3:
                preview_lines = lines[:3]
                preview = '\n'.join(preview_lines)

                return f'''
                <div class="tool-result collapsible">
                    <div class="tool-result-preview" onclick="this.parentElement.classList.toggle('expanded')">
                        <pre><code>{escape(preview)}</code></pre>
                        <div class="expand-hint">Click to show full output ({len(lines)} lines)</div>
                    </div>
                    <div class="tool-result-full">
                        <pre><code>{escape(content)}</code></pre>
                    </div>
                </div>
                '''

        # Long file content (Read tool)
        is_long = is_file_content and len(lines) > 20
        if is_long:
            # Show first 10 and last 5 lines
            preview_lines = lines[:10] + ['... (content hidden) ...'] + lines[-5:]
            preview = '\n'.join(preview_lines)

            return f'''
            <div class="tool-result collapsible">
                <div class="tool-result-preview" onclick="this.parentElement.classList.toggle('expanded')">
                    <pre><code>{escape(preview)}</code></pre>
                    <div class="expand-hint">Click to show full content ({len(lines)} lines)</div>
                </div>
                <div class="tool-result-full">
                    <pre><code>{escape(content)}</code></pre>
                </div>
            </div>
            '''
        else:
            return f'''
            <div class="tool-result">
                <pre><code>{escape(content)}</code></pre>
            </div>
            '''

    def render_diff(self, content: str) -> str:
        """Render a diff with expand/collapse for long diffs."""
        lines = content.split('\n')
        if len(lines) > 20:
            preview = '\n'.join(lines[:15])
            hidden_count = len(lines) - 15
            return f'''
            <div class="diff-block collapsible">
                <pre class="diff-preview"><code>{escape(preview)}</code></pre>
                <div class="expand-link" onclick="this.parentElement.classList.toggle('expanded')">
                    Show full diff ({hidden_count} more lines)
                </div>
                <pre class="diff-full"><code>{escape(content)}</code></pre>
            </div>
            '''
        return f'<pre class="diff-block"><code>{escape(content)}</code></pre>'

    def render_message(self, msg: Dict[str, Any]) -> str:
        """Render a single message."""
        msg_type = msg.get('type')
        message = msg.get('message', {})
        role = message.get('role', '')
        content_items = message.get('content', [])

        if msg_type == 'user':
            html_parts = []

            # Handle case where content_items might be a string instead of a list
            if isinstance(content_items, str):
                html_parts.append(f'<div class="message-text">{self.render_markdown(content_items)}</div>')
            else:
                for item in content_items:
                    if isinstance(item, str):
                        html_parts.append(f'<div class="message-text">{self.render_markdown(item)}</div>')
                    elif isinstance(item, dict):
                        if item.get('type') == 'text':
                            text = item.get('text', '')
                            html_parts.append(f'<div class="message-text">{self.render_markdown(text)}</div>')
                        elif item.get('type') == 'tool_result':
                            # Tool results are usually shown inline with the tool call
                            pass

            if html_parts:
                return f'<div class="message user-message">{"".join(html_parts)}</div>'
            return ''

        elif msg_type == 'assistant':
            html_parts = []

            for item in content_items:
                if isinstance(item, str):
                    if item.strip():
                        html_parts.append(f'<div class="message-text">{self.render_markdown(item)}</div>')
                    continue

                if not isinstance(item, dict):
                    continue

                item_type = item.get('type')

                if item_type == 'text':
                    text = item.get('text', '')
                    if text.strip():
                        html_parts.append(f'<div class="message-text">{self.render_markdown(text)}</div>')

                elif item_type == 'thinking':
                    # Skip thinking blocks for now (can be shown in a collapsed section)
                    pass

                elif item_type == 'tool_use':
                    html_parts.append(self.render_tool_use(item))

                    # Look for corresponding tool result in next messages
                    tool_id = item.get('id')
                    tool_name = item.get('name', '')
                    tool_input = item.get('input', {})
                    result_html = self.find_and_render_tool_result(tool_id, tool_name, tool_input)
                    if result_html:
                        html_parts.append(result_html)

            if html_parts:
                return f'<div class="message assistant-message">{"".join(html_parts)}</div>'
            return ''

        return ''

    def find_and_render_tool_result(self, tool_id: str, tool_name: str, tool_input: Dict[str, Any] = None) -> str:
        """Find and render the tool result for a given tool use ID."""
        for msg in self.messages:
            if msg.get('type') == 'user':
                content = msg.get('message', {}).get('content', [])
                # Handle case where content might be a string instead of a list
                if isinstance(content, str):
                    continue
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'tool_result' and item.get('tool_use_id') == tool_id:
                            return self.render_tool_result(item, tool_name, tool_input)
        return ''

    def get_css(self) -> str:
        """Get the CSS styles."""
        return '''
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
            background-color: #f9f9f9;
            color: #1a1a1a;
            line-height: 1.6;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .header {
            border-bottom: 2px solid #e5e5e5;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 24px;
            color: #2c2c2c;
            margin-bottom: 5px;
        }

        .header .session-info {
            color: #666;
            font-size: 14px;
            margin-bottom: 12px;
        }

        .session-timing {
            display: flex;
            gap: 24px;
            margin-top: 12px;
            padding: 12px;
            background-color: #f9fafb;
            border-radius: 6px;
            border: 1px solid #e5e7eb;
        }

        .timing-item {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .timing-label {
            font-size: 12px;
            color: #6b7280;
            font-weight: 500;
        }

        .timing-value {
            font-size: 16px;
            color: #1f2937;
            font-weight: 600;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
        }

        .message {
            margin-bottom: 24px;
            padding: 16px;
            border-radius: 6px;
        }

        .user-message {
            background-color: #f0f4f8;
            border-left: 3px solid #3b82f6;
        }

        .assistant-message {
            background-color: #ffffff;
            border-left: 3px solid #10b981;
        }

        .message-text {
            margin-bottom: 12px;
        }

        .message-text:last-child {
            margin-bottom: 0;
        }

        .tool-use {
            margin: 12px 0;
            padding: 8px 12px;
            background-color: #f9fafb;
            border-radius: 4px;
            border: 1px solid #e5e7eb;
        }

        .tool-header {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }

        .tool-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .tool-name {
            font-weight: 600;
            color: #374151;
        }

        .tool-params {
            color: #6b7280;
            font-size: 13px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .tool-result {
            margin: 8px 0;
            background-color: #f9fafb;
            border-radius: 4px;
            border: 1px solid #e5e7eb;
            overflow: hidden;
        }

        .tool-result.collapsible .tool-result-full {
            display: none;
        }

        .tool-result.collapsible.expanded .tool-result-preview {
            display: none;
        }

        .tool-result.collapsible.expanded .tool-result-full {
            display: block;
        }

        .tool-result-preview {
            cursor: pointer;
            position: relative;
        }

        .expand-hint {
            text-align: center;
            padding: 8px;
            background-color: #e5e7eb;
            color: #6b7280;
            font-size: 13px;
            border-top: 1px solid #d1d5db;
            cursor: pointer;
        }

        .expand-hint:hover {
            background-color: #d1d5db;
        }

        pre {
            margin: 0;
            padding: 12px;
            background-color: #ffffff;
            color: #1f2937;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.5;
        }

        code {
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 13px;
            color: #1f2937;
        }

        .message-text code {
            background-color: #f3f4f6;
            color: #1f2937;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 12px;
        }

        .message-text pre {
            background-color: #f3f4f6;
            color: #1f2937;
            margin: 8px 0;
        }

        .message-text pre code {
            background-color: transparent;
            color: #1f2937;
            padding: 0;
        }

        .diff-block {
            margin: 8px 0;
        }

        .diff-block.collapsible .diff-full {
            display: none;
        }

        .diff-block.collapsible.expanded .diff-preview {
            display: none;
        }

        .diff-block.collapsible.expanded .diff-full {
            display: block;
        }

        .diff-block.collapsible.expanded .expand-link {
            display: none;
        }

        .expand-link {
            text-align: center;
            padding: 8px;
            background-color: #f3f4f6;
            color: #3b82f6;
            cursor: pointer;
            border-radius: 4px;
            margin-top: 4px;
            font-size: 13px;
        }

        .expand-link:hover {
            background-color: #e5e7eb;
        }

        h1, h2, h3 {
            margin: 16px 0 8px 0;
            color: #1f2937;
        }

        h1 { font-size: 24px; }
        h2 { font-size: 20px; }
        h3 { font-size: 16px; }

        strong {
            font-weight: 600;
            color: #1f2937;
        }

        em {
            font-style: italic;
        }

        /* Edit diff styling */
        .edit-diff {
            margin: 8px 0;
            border: 1px solid #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            background-color: #ffffff;
        }

        .diff-file-header {
            padding: 8px 12px;
            background-color: #f9fafb;
            border-bottom: 1px solid #e5e7eb;
            font-size: 13px;
            font-weight: 600;
            color: #374151;
        }

        .diff-lines {
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 12px;
            line-height: 1.5;
        }

        .diff-line {
            display: flex;
            align-items: stretch;
            border-bottom: 1px solid #f3f4f6;
        }

        .diff-line:last-child {
            border-bottom: none;
        }

        .diff-line-num {
            padding: 2px 8px;
            text-align: right;
            color: #9ca3af;
            background-color: #f9fafb;
            border-right: 1px solid #e5e7eb;
            min-width: 40px;
            flex-shrink: 0;
            user-select: none;
        }

        .diff-line-num.old {
            border-right: none;
        }

        .diff-line-num.new {
            border-right: 1px solid #e5e7eb;
        }

        .diff-prefix {
            padding: 2px 4px;
            width: 20px;
            flex-shrink: 0;
            text-align: center;
            font-weight: bold;
        }

        .diff-content {
            padding: 2px 8px;
            flex-grow: 1;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .diff-del {
            background-color: #fef2f2;
        }

        .diff-del .diff-prefix {
            color: #dc2626;
        }

        .diff-del .diff-content {
            background-color: rgba(239, 68, 68, 0.1);
        }

        .diff-add {
            background-color: #f0fdf4;
        }

        .diff-add .diff-prefix {
            color: #16a34a;
        }

        .diff-add .diff-content {
            background-color: rgba(34, 197, 94, 0.15);
        }

        .diff-context {
            background-color: #ffffff;
        }

        .diff-expand-link {
            text-align: center;
            padding: 8px;
            background-color: #f9fafb;
            color: #3b82f6;
            cursor: pointer;
            border-top: 1px solid #e5e7eb;
            font-size: 13px;
        }

        .diff-expand-link:hover {
            background-color: #f3f4f6;
        }

        .edit-diff.collapsible .diff-full {
            display: none;
        }

        .edit-diff.collapsible.expanded .diff-preview {
            display: none;
        }

        .edit-diff.collapsible.expanded .diff-full {
            display: block;
        }
        '''

    def get_javascript(self) -> str:
        """Get the JavaScript for interactivity."""
        return '''
        // Simple toggle functionality for collapsible sections
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Claude Code session viewer loaded');
        });
        '''

    def render_html(self) -> str:
        """Render the complete HTML document."""
        session_id = os.path.basename(self.jsonl_path).replace('.jsonl', '')

        # Calculate session timing
        timing = self.calculate_session_timing()
        timing_html = f'''
            <div class="session-timing">
                <div class="timing-item">
                    <span class="timing-label">Total Duration:</span>
                    <span class="timing-value">{self.format_timedelta(timing['total_duration'])}</span>
                </div>
                <div class="timing-item">
                    <span class="timing-label">Claude Working Time:</span>
                    <span class="timing-value">{self.format_timedelta(timing['claude_working_time'])}</span>
                </div>
                <div class="timing-item">
                    <span class="timing-label">Waiting for User:</span>
                    <span class="timing-value">{self.format_timedelta(timing['waiting_for_user_time'])}</span>
                </div>
            </div>'''

        messages_html = []
        for msg in self.messages:
            rendered = self.render_message(msg)
            if rendered:
                messages_html.append(rendered)

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code Session - {escape(session_id)}</title>
    <style>
{self.get_css()}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Claude Code Session</h1>
            <div class="session-info">Session ID: {escape(session_id)}</div>
            {timing_html}
        </div>
        <div class="messages">
{"".join(messages_html)}
        </div>
    </div>
    <script>
{self.get_javascript()}
    </script>
</body>
</html>'''

    def save(self, output_path: str):
        """Save the rendered HTML to a file."""
        html = self.render_html()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Saved HTML to {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python claudecode_to_html.py input.jsonl [output.html]")
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found")
        sys.exit(1)

    # Determine output path
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        output_path = input_path.replace('.jsonl', '.html')

    # Render and save
    renderer = SessionRenderer(input_path)
    renderer.save(output_path)


if __name__ == '__main__':
    main()
