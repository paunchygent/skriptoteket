export type UiNotifier = {
  info: (message: string) => void;
  success: (message: string) => void;
  warning: (message: string) => void;
  failure: (message: string) => void;
};
