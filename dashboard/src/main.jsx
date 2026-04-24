import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import router from "./router";
import "./index.css";

async function bootstrap() {
  const mockEnabled =
    import.meta.env.DEV &&
    String(import.meta.env.VITE_ENABLE_MSW || "false").toLowerCase() === "true";

  if (mockEnabled) {
    try {
      const { worker } = await import("./mocks/browser");
      await worker.start({ onUnhandledRequest: "bypass" });
    } catch (error) {
      console.warn("MSW failed to start, continuing without request mocking.", error);
    }
  }

  ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
      <RouterProvider router={router} />
    </React.StrictMode>
  );
}

bootstrap();
