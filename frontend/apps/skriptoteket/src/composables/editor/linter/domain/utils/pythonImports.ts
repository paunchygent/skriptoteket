function endOfLine(text: string, start: number): number {
  const newline = text.indexOf("\n", start);
  return newline === -1 ? text.length : newline + 1;
}

function lineTextAt(text: string, start: number): string {
  return text.slice(start, endOfLine(text, start));
}

function isCommentOrBlankLine(lineText: string): boolean {
  const trimmed = lineText.trim();
  return trimmed === "" || trimmed.startsWith("#");
}

function isEncodingCookieLine(lineText: string): boolean {
  return /^[ \t\f]*#.*coding[:=][ \t]*[-_.a-zA-Z0-9]+/.test(lineText);
}

function isImportLine(lineText: string): boolean {
  return /^[ \t]*(import|from)\b/.test(lineText);
}

function isFutureImportLine(lineText: string): boolean {
  return /^[ \t]*from[ \t]+__future__[ \t]+import\b/.test(lineText);
}

type StringQuote = "'" | '"' | "'''" | '"""';

function quoteAt(text: string, pos: number): StringQuote | null {
  if (text.startsWith("'''", pos)) return "'''";
  if (text.startsWith('"""', pos)) return '"""';
  const ch = text[pos] ?? "";
  if (ch === "'" || ch === '"') return ch;
  return null;
}

function quoteStartAt(text: string, pos: number): { quote: StringQuote; from: number } | null {
  let cursor = pos;
  while (cursor < text.length) {
    const ch = text[cursor] ?? "";
    if (ch === "r" || ch === "R" || ch === "u" || ch === "U" || ch === "b" || ch === "B" || ch === "f" || ch === "F") {
      cursor += 1;
      continue;
    }
    break;
  }

  const quote = quoteAt(text, cursor);
  if (!quote) return null;
  return { quote, from: cursor };
}

function findStringLiteralEnd(text: string, start: number, quote: StringQuote): number | null {
  const quoteLen = quote.length;
  const end = text.indexOf(quote, start + quoteLen);
  if (end === -1) return null;
  return end + quoteLen;
}

function skipModuleDocstring(text: string, start: number): number {
  let pos = start;
  while (pos < text.length && isCommentOrBlankLine(lineTextAt(text, pos))) {
    pos = endOfLine(text, pos);
  }

  const line = lineTextAt(text, pos);
  const firstNonWhitespace = line.search(/\S/);
  if (firstNonWhitespace === -1) return start;

  const docStart = pos + firstNonWhitespace;
  const startQuote = quoteStartAt(text, docStart);
  if (!startQuote) return start;

  const docEnd = findStringLiteralEnd(text, startQuote.from, startQuote.quote);
  if (docEnd === null) return start;

  return endOfLine(text, docEnd);
}

function skipFutureImports(text: string, start: number): number {
  let pos = start;
  while (pos < text.length) {
    const line = lineTextAt(text, pos);
    if (isCommentOrBlankLine(line)) {
      pos = endOfLine(text, pos);
      continue;
    }

    if (!isFutureImportLine(line)) break;
    pos = endOfLine(text, pos);
  }
  return pos;
}

function findImportBlockInsertion(text: string, start: number): number {
  let pos = start;
  let lastImportLineEnd: number | null = null;

  while (pos < text.length) {
    const line = lineTextAt(text, pos);
    const lineEnd = endOfLine(text, pos);

    if (isCommentOrBlankLine(line)) {
      pos = lineEnd;
      continue;
    }

    if (isImportLine(line)) {
      lastImportLineEnd = lineEnd;
      pos = lineEnd;
      continue;
    }

    break;
  }

  if (lastImportLineEnd !== null) return lastImportLineEnd;

  return start;
}

export function findImportInsertPosition(text: string): number {
  let pos = 0;

  if (text.startsWith("\uFEFF")) {
    pos = 1;
  }

  if (text.startsWith("#!", pos)) {
    pos = endOfLine(text, pos);
  }

  const firstLineStart = pos;
  const firstLine = lineTextAt(text, firstLineStart);
  const secondLineStart = endOfLine(text, firstLineStart);
  const secondLine = lineTextAt(text, secondLineStart);

  if (isEncodingCookieLine(firstLine)) pos = endOfLine(text, firstLineStart);
  if (isEncodingCookieLine(secondLine) && pos <= secondLineStart) pos = endOfLine(text, secondLineStart);

  const afterDocstring = skipModuleDocstring(text, pos);
  if (afterDocstring !== pos) pos = afterDocstring;

  pos = skipFutureImports(text, pos);

  const importInsert = findImportBlockInsertion(text, pos);
  if (importInsert !== pos) return importInsert;

  let scan = pos;
  while (scan < text.length) {
    const lineStart = scan;
    const line = lineTextAt(text, scan);
    if (isCommentOrBlankLine(line)) {
      scan = endOfLine(text, scan);
      continue;
    }
    return lineStart;
  }

  return text.length;
}
