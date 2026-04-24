import { useEffect } from "react";

export default function usePolling(callback, intervalMs) {
  useEffect(() => {
    callback();
    const id = setInterval(callback, intervalMs);
    return () => clearInterval(id);
  }, [callback, intervalMs]);
}
