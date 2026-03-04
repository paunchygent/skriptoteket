/**
 * Build UI-facing risk export gate text from backend `export_gate` payloads.
 *
 * The backend remains the source of truth for required fields and returns
 * `missing_context_fields`. This module maps those field keys to Swedish labels
 * and creates concise copy for the risk step UI.
 */

const RISK_CONTEXT_FIELD_LABELS: Record<string, string> = {
  scope: "omfattning",
  participants: "deltagare",
  approver: "ansvarig",
  assessment_date: "datum",
  next_review_date: "nästa översyn",
};

function toLabel(field: string): string {
  return RISK_CONTEXT_FIELD_LABELS[field] ?? field;
}

export function mapMissingRiskContextFieldLabels(fields: string[] | null | undefined): string[] {
  if (!fields || fields.length === 0) return [];
  return fields.map(toLabel);
}

export function buildMissingRiskContextMessage(fields: string[] | null | undefined): string | null {
  const labels = mapMissingRiskContextFieldLabels(fields);
  if (labels.length === 0) return null;
  return `Fyll i ${labels.join(", ")} innan export.`;
}
