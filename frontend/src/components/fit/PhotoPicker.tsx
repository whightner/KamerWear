"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Camera, ImageUp, Trash2 } from "lucide-react";

const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];
const MAX_BYTES = 8 * 1024 * 1024;

interface PhotoPickerProps {
  /** "front" or "side": used in labels such as "Take front photo". */
  view: "front" | "side";
  file: File | null;
  onChange: (file: File | null) => void;
  /** Error from the server about this photo (e.g. feet not visible). */
  error?: string;
}

/**
 * Choose or take one photo. The photo stays in the browser (object URL
 * preview) until the customer asks for an estimate.
 */
export function PhotoPicker({ view, file, onChange, error }: PhotoPickerProps) {
  const fileId = useId();
  const cameraId = useId();
  const errorId = useId();
  const fileInput = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    if (!file) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- preview follows the chosen file
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function choose(candidate: File | undefined) {
    if (!candidate) return;
    if (!ACCEPTED.includes(candidate.type)) {
      setLocalError("Please choose a JPEG, PNG or WebP photo. HEIC photos aren't supported yet.");
      return;
    }
    if (candidate.size > MAX_BYTES) {
      setLocalError("This photo is too large. Please use one under 8 MB.");
      return;
    }
    setLocalError("");
    onChange(candidate);
  }

  const message = localError || error;
  const button =
    "inline-flex h-11 cursor-pointer items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold";

  return (
    <div>
      {/* Hidden inputs with real labels; the visible buttons open them. */}
      <label htmlFor={fileId} className="sr-only">
        Choose {view} photo from your device
      </label>
      <input
        ref={fileInput}
        id={fileId}
        tabIndex={-1}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        onChange={(event) => {
          choose(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
      <label htmlFor={cameraId} className="sr-only">
        Take {view} photo with your camera
      </label>
      <input
        ref={cameraInput}
        id={cameraId}
        tabIndex={-1}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        onChange={(event) => {
          choose(event.target.files?.[0]);
          event.target.value = "";
        }}
      />

      {preview && file ? (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-line bg-cream p-3 sm:flex-row sm:items-start">
          {/* eslint-disable-next-line @next/next/no-img-element -- local object URL preview */}
          <img
            src={preview}
            alt={`Your ${view} photo`}
            className="h-56 w-auto max-w-full rounded-lg bg-white object-contain"
          />
          <div className="flex w-full min-w-0 flex-col gap-2 sm:w-auto">
            <p className="truncate text-xs text-muted">{file.name}</p>
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              className={`${button} border border-line bg-white text-ink hover:border-ink`}
            >
              <ImageUp className="size-4" aria-hidden="true" />
              Replace {view} photo
            </button>
            <button
              type="button"
              onClick={() => {
                setLocalError("");
                onChange(null);
              }}
              className={`${button} text-muted hover:text-ink`}
            >
              <Trash2 className="size-4" aria-hidden="true" />
              Remove {view} photo
            </button>
          </div>
        </div>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => cameraInput.current?.click()}
            aria-describedby={message ? errorId : undefined}
            className={`${button} bg-ink text-white hover:bg-black`}
          >
            <Camera className="size-4" aria-hidden="true" />
            Take {view} photo
          </button>
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            aria-describedby={message ? errorId : undefined}
            className={`${button} border border-line bg-white text-ink hover:border-ink`}
          >
            <ImageUp className="size-4" aria-hidden="true" />
            Choose {view} photo
          </button>
        </div>
      )}
      {message && (
        <p id={errorId} role="alert" className="mt-3 rounded-lg border border-deal/30 bg-deal-soft px-3 py-2 text-sm font-medium text-deal-dark">
          {message}
        </p>
      )}
    </div>
  );
}
