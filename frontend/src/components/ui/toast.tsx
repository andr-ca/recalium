import * as React from "react";
import { cn } from "@/lib/utils";

interface ToastProps {
  message: string;
  type?: "success" | "error" | "info";
  onDismiss: () => void;
}

export function Toast({ message, type = "info", onDismiss }: ToastProps) {
  React.useEffect(() => {
    const timer = setTimeout(onDismiss, 4000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "fixed bottom-4 right-4 z-50 rounded-lg px-4 py-3 text-sm font-medium shadow-lg",
        type === "success" && "bg-green-600 text-white",
        type === "error" && "bg-red-600 text-white",
        type === "info" && "bg-gray-800 text-white"
      )}
    >
      {message}
    </div>
  );
}
