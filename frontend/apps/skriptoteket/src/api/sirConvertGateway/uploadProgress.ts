/**
 * Sir Convert Gateway upload progress contracts.
 *
 * Domain purpose:
 *   Describe browser-visible multipart upload progress before Sir Convert has
 *   accepted a conversion job and returned a job id.
 *
 * Relationships:
 *   - Used by the transcript Gateway client for audio intake.
 *   - Rendered by the Conversion Hub transcript runtime before polling starts.
 */

export type SirConvertUploadProgress = {
  loadedBytes: number;
  totalBytes: number | null;
  percentComplete: number | null;
};

export type SirConvertUploadProgressHandler = (progress: SirConvertUploadProgress) => void;
