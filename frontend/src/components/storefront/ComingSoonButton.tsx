"use client";

import { useState, type ReactNode } from "react";

interface ComingSoonButtonProps {
  children: ReactNode;
  message: string;
  className: string;
  messageClassName?: string;
}

// For calls to action whose feature is not built yet: clicking explains that
// instead of pretending something happened.
export function ComingSoonButton({
  children,
  message,
  className,
  messageClassName = "",
}: ComingSoonButtonProps) {
  const [showMessage, setShowMessage] = useState(false);

  return (
    <div className="flex flex-col items-start gap-2">
      <button
        type="button"
        className={className}
        onClick={() => setShowMessage(true)}
      >
        {children}
      </button>
      <p role="status" className={`min-h-5 text-sm ${messageClassName}`}>
        {showMessage ? message : ""}
      </p>
    </div>
  );
}
