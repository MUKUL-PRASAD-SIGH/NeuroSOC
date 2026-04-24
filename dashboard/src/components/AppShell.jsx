import { Outlet } from "react-router-dom";
import { useEffect } from "react";
import { useDashboardStore } from "../store/dashboardStore";

export default function AppShell() {
  const fetchStats = useDashboardStore((state) => state.fetchStats);
  const fetchModelStatus = useDashboardStore((state) => state.fetchModelStatus);
  const hydrateAlerts = useDashboardStore((state) => state.hydrateAlerts);
  const startAlertStream = useDashboardStore((state) => state.startAlertStream);
  const stopAlertStream = useDashboardStore((state) => state.stopAlertStream);

  useEffect(() => {
    fetchStats();
    const statsInterval = window.setInterval(fetchStats, 30000);

    return () => {
      window.clearInterval(statsInterval);
    };
  }, [fetchStats]);

  useEffect(() => {
    fetchModelStatus();
    const modelInterval = window.setInterval(fetchModelStatus, 60000);

    return () => {
      window.clearInterval(modelInterval);
    };
  }, [fetchModelStatus]);

  useEffect(() => {
    hydrateAlerts();
    startAlertStream();

    return () => {
      stopAlertStream();
    };
  }, [hydrateAlerts, startAlertStream, stopAlertStream]);

  return (
    <main className="soc-shell">
      <Outlet />
    </main>
  );
}
