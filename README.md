# Claude Code to HTML Converter

Convert Claude Code session logs (`.jsonl`) to standalone HTML files.

## Usage

```bash
python3 claudecode_to_html.py input.jsonl [output.html]
```

If no output file is specified, creates `input.html` from `input.jsonl`.

## Features

- Self-contained HTML (all CSS/JS inlined)
- Collapsible long file reads (>20 lines)
- Expandable diffs with line numbers
- Tool calls with colored indicators
- Markdown rendering with syntax highlighting
- Light theme matching Claude Code web UI

## Requirements

Python 3.7+ (standard library only)

## Example

```bash
python3 claudecode_to_html.py session.jsonl
# Creates: session.html
```
