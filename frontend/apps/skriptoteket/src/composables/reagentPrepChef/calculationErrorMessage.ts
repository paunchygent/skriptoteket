import { isApiError } from "../../api/client";

const fieldMessages: Record<string, string> = {
  chemical_formula: "Ange en giltig kemisk formel.",
  target_molarity: "Ange en målmolaritet större än 0.",
  vol_per_group_ml: "Ange en volym per grupp större än 0 ml.",
  student_count: "Ange ett helt antal elever större än 0.",
  students_per_group: "Ange ett helt antal elever per grupp större än 0.",
  safety_factor: "Ange en marginal mellan 0 och 0,5.",
  solute_purity: "Ange en renhet större än 0 och högst 1.",
  stock_molarity: "Ange en stockmolaritet som är större än målmolariteten.",
  source_type: "Välj källa: fast ämne eller spädning från stocklösning.",
};

const appMessages: Record<string, string> = {
  ERR_INVALID_FORMULA: fieldMessages.chemical_formula,
  ERR_STOCK_MISSING: "Ange stockmolariteten.",
  ERR_IMPOSSIBLE_DILUTION: fieldMessages.stock_molarity,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Translate structured validation identities, never infer meaning from server prose. */
export function calculationErrorMessage(error: unknown): string {
  const fallback = "Det gick inte att beräkna just nu. Kontrollera uppgifterna och försök igen.";
  if (!isApiError(error)) return fallback;

  const details = error.details;
  if (isRecord(details)) {
    if (typeof details.app_error_code === "string" && Object.hasOwn(appMessages, details.app_error_code)) {
      return appMessages[details.app_error_code];
    }
    if (typeof details.field === "string" && Object.hasOwn(fieldMessages, details.field)) {
      return fieldMessages[details.field];
    }
  }

  if (Array.isArray(details)) {
    const messages = details.map((issue: unknown) => {
      if (!isRecord(issue) || !Array.isArray(issue.loc)) return null;
      const [location, field] = issue.loc;
      return location === "body" && typeof field === "string" && Object.hasOwn(fieldMessages, field)
        ? fieldMessages[field]
        : null;
    });
    const uniqueMessages = [...new Set(messages.filter((message): message is string => message !== null))];
    if (uniqueMessages.length > 0) return uniqueMessages.join(" ");
  }

  return fallback;
}
