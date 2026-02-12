"""
Markdown parser and filter module.
Removes code blocks and tables from markdown content.
"""

import re
from dataclasses import dataclass, field


@dataclass
class ParseResult:
    """Holds the result of parsing a markdown file."""
    cleaned_text: str
    removed_code_blocks: list[str] = field(default_factory=list)
    removed_tables: list[str] = field(default_factory=list)

    @property
    def code_block_count(self) -> int:
        return len(self.removed_code_blocks)

    @property
    def table_count(self) -> int:
        return len(self.removed_tables)


def remove_fenced_code_blocks(text: str) -> tuple[str, list[str]]:
    """
    Remove fenced code blocks (backtick or tilde fences) from markdown.

    Handles:
      - Backtick fences with or without language identifier
      - Tilde fences with or without language identifier
      - Nested content of any kind inside the block

    Returns:
        Tuple of (cleaned_text, list_of_removed_blocks)
    """
    # Pattern: line starting with backtick or tilde fence (with optional lang),
    # everything until closing fence
    pattern = re.compile(
        r'^(?P<fence>`{3,}|~{3,})(?P<lang>[^\n]*)$'  # opening fence
        r'(?P<body>.*?)'                                # body (non-greedy)
        r'^(?P=fence)[ \t]*$',                          # closing fence (same marker)
        re.MULTILINE | re.DOTALL,
    )

    removed: list[str] = []

    def _collect_and_remove(match: re.Match) -> str:
        removed.append(match.group(0))
        return ""

    cleaned = pattern.sub(_collect_and_remove, text)
    return cleaned, removed


def remove_indented_code_blocks(text: str) -> tuple[str, list[str]]:
    """
    Remove indented code blocks (4 spaces or 1 tab) from markdown.

    An indented code block is a consecutive group of lines each indented
    by at least 4 spaces or 1 tab, preceded and followed by a blank line
    (or start/end of document).

    Returns:
        Tuple of (cleaned_text, list_of_removed_blocks)
    """
    lines = text.split('\n')
    removed: list[str] = []
    result_lines: list[str] = []
    buffer: list[str] = []
    in_code = False

    for line in lines:
        is_code_line = line.startswith('    ') or line.startswith('\t')
        is_blank = line.strip() == ''

        if in_code:
            if is_code_line or is_blank:
                buffer.append(line)
            else:
                # End of indented block
                # Strip trailing blank lines from buffer
                while buffer and buffer[-1].strip() == '':
                    result_lines.append(buffer.pop())
                if buffer:
                    removed.append('\n'.join(buffer))
                buffer = []
                in_code = False
                result_lines.append(line)
        else:
            if is_code_line and (not result_lines or result_lines[-1].strip() == ''):
                in_code = True
                buffer.append(line)
            else:
                result_lines.append(line)

    # Handle remaining buffer
    if buffer:
        while buffer and buffer[-1].strip() == '':
            result_lines.append(buffer.pop())
        if buffer:
            removed.append('\n'.join(buffer))

    return '\n'.join(result_lines), removed


def remove_tables(text: str) -> tuple[str, list[str]]:
    """
    Remove markdown tables from text.

    A markdown table is detected as:
      - A header row with pipes
      - A separator row with pipes and dashes
      - Zero or more data rows with pipes

    Returns:
        Tuple of (cleaned_text, list_of_removed_tables)
    """
    pattern = re.compile(
        r'^'
        r'(?P<header>\|[^\n]*\|[ \t]*)\n'                     # header row
        r'(?P<sep>\|[ \t:]*-[-| \t:]*\|[ \t]*)\n'             # separator row
        r'(?P<body>(?:\|[^\n]*\|[ \t]*\n)*)',                  # body rows
        re.MULTILINE,
    )

    removed: list[str] = []

    def _collect_and_remove(match: re.Match) -> str:
        removed.append(match.group(0).rstrip('\n'))
        return ""

    cleaned = pattern.sub(_collect_and_remove, text)
    return cleaned, removed


def remove_tables_loose(text: str) -> tuple[str, list[str]]:
    """
    Remove markdown tables that may not have leading/trailing pipes.

    Handles tables like:
        Header 1 | Header 2
        ---------|--------
        Cell 1   | Cell 2

    Returns:
        Tuple of (cleaned_text, list_of_removed_tables)
    """
    pattern = re.compile(
        r'^'
        r'(?P<header>[^\n]*\|[^\n]*)\n'                          # header with pipe
        r'(?P<sep>[ \t:]*-[-| \t:]*-[ \t:]*)\n'                  # separator
        r'(?P<body>(?:[^\n]*\|[^\n]*\n)*)',                       # body rows
        re.MULTILINE,
    )

    removed: list[str] = []

    def _collect_and_remove(match: re.Match) -> str:
        removed.append(match.group(0).rstrip('\n'))
        return ""

    cleaned = pattern.sub(_collect_and_remove, text)
    return cleaned, removed


def collapse_excessive_blank_lines(text: str, max_consecutive: int = 2) -> str:
    """
    Collapse runs of blank lines so that at most max_consecutive
    consecutive blank lines remain.
    """
    pattern = re.compile(r'\n{' + str(max_consecutive + 2) + r',}')
    replacement = '\n' * (max_consecutive + 1)
    return pattern.sub(replacement, text)


def parse_and_clean(markdown_text: str) -> ParseResult:
    """
    Main function: remove all code blocks and tables from markdown.

    Processing order:
      1. Fenced code blocks (backtick and tilde fences)
      2. Indented code blocks (4 spaces / tab)
      3. Pipe tables (strict format with leading/trailing pipes)
      4. Pipe tables (loose format without leading/trailing pipes)
      5. Collapse excessive blank lines

    Returns:
        ParseResult with cleaned text and lists of removed elements.
    """
    all_code_blocks: list[str] = []
    all_tables: list[str] = []

    # Step 1: fenced code blocks
    text, removed = remove_fenced_code_blocks(markdown_text)
    all_code_blocks.extend(removed)

    # Step 2: indented code blocks
    text, removed = remove_indented_code_blocks(text)
    all_code_blocks.extend(removed)

    # Step 3: strict tables
    text, removed = remove_tables(text)
    all_tables.extend(removed)

    # Step 4: loose tables
    text, removed = remove_tables_loose(text)
    all_tables.extend(removed)

    # Step 5: clean up blank lines
    text = collapse_excessive_blank_lines(text)

    # Strip trailing whitespace on each line but preserve structure
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # Ensure file ends with single newline
    text = text.strip('\n') + '\n'

    return ParseResult(
        cleaned_text=text,
        removed_code_blocks=all_code_blocks,
        removed_tables=all_tables,
    )
