import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import AlertFeed from "../components/AlertFeed";
import IngestionWorkbench from "../components/IngestionWorkbench";
import ModelStatusCard from "../components/ModelStatusCard";
import StatsBar from "../components/StatsBar";
import ThreatMap from "../components/ThreatMap";
import UserProfileModal from "../components/UserProfileModal";
import VerdictTimeline from "../components/Charts/VerdictTimeline";
import { buildTimelineData } from "../mocks/data";
import { useDashboardStore } from "../store/dashboardStore";

export default function DashboardPage() {
  const alerts = useDashboardStore((state) => state.alerts.items);
  const statsError = useDashboardStore((state) => state.stats.error);
  const modelError = useDashboardStore((state) => state.modelStatus.error);
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get("view") === "threat-map" ? "threat-map" : "overview";

  const timelineData = useMemo(() => buildTimelineData(alerts), [alerts]);

  function setActiveTab(view) {
    const next = new URLSearchParams(searchParams);
    if (view === "overview") {
      next.delete("view");
    } else {
      next.set("view", view);
    }

    setSearchParams(next);
  }

  return (
    <>
      <section className="mb-4 rounded-[5px] border border-soc-border/0 bg-soc-panel/75 p-4 shadow-[0_24px_70px_rgba(3,10,24,0.48)] backdrop-blur-xl md:p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3">
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-soc-electric/40 bg-soc-electric/10 text-xl font-semibold text-soc-electric">
                N
              </span>
              <div>
                <p className="soc-kicker">NeuroSOC Analyst Surface</p>
                <h1 className="mt-1 text-2xl font-semibold text-soc-text md:text-3xl">
                  Live classifier oversight for human analysts
                </h1>
              </div>
            </div>
            <div className="mt-4">
              <StatsBar />
            </div>
          </div>

          <div className="xl:w-[420px]">
            <ModelStatusCard />
          </div>
        </div>

        {statsError || modelError ? (
          <div className="mt-4 rounded-2xl border border-soc-red/45 bg-soc-red/10 px-4 py-3 text-sm text-soc-red">
            {statsError || modelError}
          </div>
        ) : null}
      </section>

      <section className="soc-glass mb-4 p-2 md:p-3">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setActiveTab("overview")}
            className={`rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition-colors ${
              activeTab === "overview"
                ? "border-soc-electric/45 bg-soc-electric/15 text-soc-electric"
                : "border-soc-border bg-soc-panelSoft/45 text-soc-muted hover:border-soc-electric/35"
            }`}
          >
            Overview
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("threat-map")}
            className={`rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition-colors ${
              activeTab === "threat-map"
                ? "border-soc-electric/45 bg-soc-electric/15 text-soc-electric"
                : "border-soc-border bg-soc-panelSoft/45 text-soc-muted hover:border-soc-electric/35"
            }`}
          >
            Threat Map
          </button>
        </div>
      </section>

      <IngestionWorkbench />

      {activeTab === "overview" ? (
        <section className="relative">
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(320px,3fr)]">
            <VerdictTimeline data={timelineData} />
            <AlertFeed />
          </div>
        </section>
      ) : (
        <section className="relative">
          <ThreatMap compact={false} />
        </section>
      )}

      <UserProfileModal />
    </>
  );
}
