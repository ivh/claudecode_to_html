# Notes for Future Claude Sessions

## Critical Lessons Learned

### 1. Markdown Processing Order Matters
**Problem**: Headers (# ## ###) were being rendered inside code blocks.

**Solution**: Extract code blocks FIRST using placeholders, process markdown on remaining text, then restore code blocks. Never process markdown syntax inside code blocks.

```python
# 1. Save code blocks with placeholders
# 2. Process markdown headers/bold/italic on text WITHOUT code blocks
# 3. Escape HTML
# 4. Restore code blocks
```

### 2. Light Theme for Tool Outputs
Tool result backgrounds must be `#ffffff` (white), not dark. Users expect light theme matching Claude Code web UI.

### 3. Diff Rendering
- Use Python's `difflib.unified_diff()` for proper diff generation
- Show line numbers for both old and new positions
- Collapse diffs >10 lines, showing preview
- Color coding: deletions (red background), additions (green background)

### 4. Collapsible Sections
- File reads >20 lines: auto-collapse, show first 10 + last 5
- Bash/Grep output >3 lines: auto-collapse, show first 3
- Diffs >10 lines: show first 5, expand on click

### 5. HTML Escaping
Always `escape()` user content AFTER markdown processing but BEFORE inserting into HTML templates. Headers need special placeholder handling.

## Project Architecture

- `SessionRenderer` class handles all rendering
- `render_markdown()`: Converts markdown to HTML (code blocks handled specially)
- `render_edit_diff()`: Generates proper diffs with line numbers
- `render_tool_result()`: Handles collapsing logic per tool type
- All CSS/JS inlined in output for portability

## Testing Approach

Keep example HTML outputs in repo (add to .gitignore after initial examples) to visually compare rendering changes.
