import { useToast } from "./useToast";

export type AppAvailability = "available" | "unavailable";

const CURRENTLY_UNAVAILABLE_LABEL = "Inte tillgänglig för närvarande";

export function useAppAvailability() {
  const toast = useToast();

  function isUnavailable(availability: AppAvailability | undefined): boolean {
    return availability === "unavailable";
  }

  function availabilityLabel(availability: AppAvailability | undefined): string | null {
    return isUnavailable(availability) ? CURRENTLY_UNAVAILABLE_LABEL : null;
  }

  function unavailableMessage(appTitle: string): string {
    return `${appTitle} är inte tillgänglig för närvarande.`;
  }

  function notifyUnavailable(appTitle: string): void {
    toast.info(unavailableMessage(appTitle));
  }

  return {
    availabilityLabel,
    isUnavailable,
    notifyUnavailable,
    unavailableMessage,
  };
}
