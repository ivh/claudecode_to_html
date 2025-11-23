# Claude Code to HTML Converter

Convert Claude Code session logs (`.jsonl` format) to standalone HTML files.

## Features

- ✅ Single self-contained HTML output (all CSS and JavaScript inlined)
- ✅ Compact, clean rendering similar to Claude Code web interface
- ✅ Collapsible sections for long file reads (>20 lines)
- ✅ Expandable diffs for long changes
- ✅ Tool calls displayed with colored dots
- ✅ Markdown rendering for text content
- ✅ Syntax highlighting for code blocks

## Usage

```bash
python3 claudecode_to_html.py input.jsonl [output.html]
```

### Examples

Convert a session log to HTML (auto-names output):
```bash
python3 claudecode_to_html.py a06171f9-5f33-4258-84e1-4dc70e84c6dd.jsonl
# Creates: a06171f9-5f33-4258-84e1-4dc70e84c6dd.html
```

Specify custom output filename:
```bash
python3 claudecode_to_html.py session.jsonl my-session.html
```

## Output

The generated HTML file includes:

- **User messages**: Blue-bordered blocks with user input
- **Assistant messages**: Green-bordered blocks with assistant responses
- **Tool calls**: Compact display with colored dots (Read=blue, Edit=orange, Bash=green, etc.)
- **Tool results**: Automatically collapsed for long file reads, expandable on click
- **Code blocks**: Dark-themed syntax highlighting
- **Diffs**: Shortened with expand/collapse for changes >20 lines

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

## Implementation Notes

- The script parses the JSONL format used by Claude Code session logs
- All CSS and JavaScript is inlined in the HTML output
- File reads with >20 lines are automatically collapsed
- Thinking blocks are currently hidden (can be made visible if needed)
- The HTML is fully self-contained and can be shared or archived

## Example Output

See `a06171f9-5f33-4258-84e1-4dc70e84c6dd.html` for an example of the rendered output.
