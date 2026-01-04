type SchemaJsonArrayParseResult<T> = {
  value: T[] | null;
  error: string | null;
  errorDetails: SchemaJsonErrorDetails | null;
};

type SchemaJsonErrorDetails = {
  offset: number;
  line: number;
  column: number;
  message: string;
};

function lineAndColumnFromOffset(text: string, offset: number): { line: number; column: number } {
  const boundedOffset = Math.max(0, Math.min(offset, text.length));

  let line = 1;
  let column = 1;

  for (let index = 0; index < boundedOffset; index += 1) {
    const char = text[index];
    if (char === "\n") {
      line += 1;
      column = 1;
      continue;
    }
    column += 1;
  }

  return { line, column };
}

function describeJsonParseError(
  error: unknown,
  text: string,
): { message: string; details: SchemaJsonErrorDetails | null } {
  if (!(error instanceof Error)) {
    return { message: "Okänt JSON-fel.", details: null };
  }

  const message = error.message.trim();
  if (!message) {
    return { message: "Okänt JSON-fel.", details: null };
  }

  const match = message.match(/position\s+(?<position>\d+)/);
  if (!match?.groups?.position) {
    return {
      message,
      details: {
        offset: 0,
        line: 1,
        column: 1,
        message,
      },
    };
  }

  const offset = Number.parseInt(match.groups.position, 10);
  if (Number.isNaN(offset)) {
    return {
      message,
      details: {
        offset: 0,
        line: 1,
        column: 1,
        message,
      },
    };
  }

  const { line, column } = lineAndColumnFromOffset(text, offset);
  return {
    message: `Rad ${line}, kolumn ${column}: ${message}`,
    details: {
      offset,
      line,
      column,
      message,
    },
  };
}

export function parseSchemaJsonArrayText<T>(
  text: string,
  label: string,
  emptyValue: T[] | null,
): SchemaJsonArrayParseResult<T> {
  const trimmed = text.trim();
  if (!trimmed) {
    return { value: emptyValue, error: null, errorDetails: null };
  }

  try {
    const parsed = JSON.parse(text);
    if (!Array.isArray(parsed)) {
      const error = `${label} måste vara en JSON-array.`;
      return {
        value: null,
        error,
        errorDetails: {
          offset: 0,
          line: 1,
          column: 1,
          message: error,
        },
      };
    }
    return { value: parsed as T[], error: null, errorDetails: null };
  } catch (error: unknown) {
    const details = describeJsonParseError(error, text);
    return {
      value: null,
      error: `${label} måste vara giltig JSON. ${details.message}`,
      errorDetails: details.details,
    };
  }
}
