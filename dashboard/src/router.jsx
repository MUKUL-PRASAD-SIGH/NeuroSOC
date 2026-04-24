import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router-dom";
import AppShell from "./components/AppShell";

const DashboardPage = lazy(() => import("./pages/Dashboard"));
const IntelFeedPage = lazy(() => import("./pages/IntelFeed"));
const ResponseOpsPage = lazy(() => import("./pages/ResponseOps"));
const NotFoundPage = lazy(() => import("./pages/NotFound"));

function LazyPage({ children }) {
  return <Suspense fallback={<section className="soc-glass p-4 text-sm text-soc-muted">Loading view...</section>}>{children}</Suspense>;
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: (
          <LazyPage>
            <DashboardPage />
          </LazyPage>
        ),
      },
      {
        path: "intel-feed",
        element: (
          <LazyPage>
            <IntelFeedPage />
          </LazyPage>
        ),
      },
      {
        path: "response-ops",
        element: (
          <LazyPage>
            <ResponseOpsPage />
          </LazyPage>
        ),
      },
      {
        path: "*",
        element: (
          <LazyPage>
            <NotFoundPage />
          </LazyPage>
        ),
      },
    ],
  },
]);

export default router;
