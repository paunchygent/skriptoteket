
import re

file_path = 'docs/reference/reports/ref-frontend-expert-review-epic-05.md'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove blank line before closing code fence
# Matches: newline, newline, ```, optional whitespace, end of line
# Replaces with: newline, ```, ...
fixed_content = re.sub(r'\n\n(```\s*)$', r'\n\1', content, flags=re.MULTILINE)

# Also check for triple newlines one last time just in case
fixed_content = re.sub(r'\n{3,}', '\n\n', fixed_content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print(f"Fixed internal code block spacing in {file_path}")
