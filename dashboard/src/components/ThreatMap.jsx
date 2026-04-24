import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useDashboardStore } from "../store/dashboardStore";

function buildMarkerIcon(score) {
  const size = 12 + Math.round(score * 18);

  return L.divIcon({
    className: "",
    html: `
      <div class="soc-threat-dot" style="width:${size}px;height:${size}px;">
        <span></span>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function getRiskBand(score) {
  const value = Number(score) || 0;
  if (value >= 0.8) return "Critical";
  if (value >= 0.5) return "Elevated";
  return "Watch";
}

function formatPercent(score) {
  const value = Number(score);
  if (!Number.isFinite(value)) {
    return "0%";
  }

  return `${Math.round(value * 100)}%`;
}

async function geocodeIp(sourceIp) {
  const response = await fetch(
    `http://ip-api.com/json/${sourceIp}?fields=status,message,query,country,city,lat,lon`
  );
  const data = await response.json();

  if (data.status !== "success") {
    throw new Error(data.message || "Geocoding failed");
  }

  return {
    lat: data.lat,
    lng: data.lon,
    label: [data.city, data.country].filter(Boolean).join(", ") || sourceIp,
  };
}

export default function ThreatMap({ compact = true }) {
  const threatEvents = useDashboardStore((state) => state.threatMap.items);
  const mapRef = useRef(null);
  const mapNodeRef = useRef(null);
  const markerLayerRef = useRef(null);
  const mapInitializedRef = useRef(false);
  const geoCacheRef = useRef(new Map());
  const [resolvedEvents, setResolvedEvents] = useState([]);
  const [isResolving, setIsResolving] = useState(false);

  const threatSummary = useMemo(() => {
    if (!threatEvents.length) {
      return "No HACKER verdicts in the last 24 hours.";
    }

    return `${threatEvents.length} HACKER verdicts geocoded from live alerts.`;
  }, [threatEvents]);

  const mapSettings = useMemo(
    () => [
      { label: "Basemap", value: "CARTO Dark" },
      { label: "Zoom", value: "Scroll wheel off" },
      { label: "Projection", value: "World copy jump" },
      { label: "Geocoder", value: "ip-api.com" },
    ],
    []
  );

  const legend = useMemo(
    () => [
      { label: "Watch", detail: "Score below 50%", score: 0.3 },
      { label: "Elevated", detail: "Score 50% to 79%", score: 0.65 },
      { label: "Critical", detail: "Score 80% and above", score: 0.92 },
    ],
    []
  );

  useEffect(() => {
    if (!mapNodeRef.current || mapInitializedRef.current) {
      return;
    }

    const map = L.map(mapNodeRef.current, {
      zoomControl: false,
      attributionControl: true,
      scrollWheelZoom: false,
      worldCopyJump: true,
      preferCanvas: true,
    }).setView([20, 10], 2);

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 19,
    }).addTo(map);

    markerLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    mapInitializedRef.current = true;

    const timeoutId = window.setTimeout(() => {
      map.invalidateSize();
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
      map.remove();
      mapRef.current = null;
      markerLayerRef.current = null;
      mapInitializedRef.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function resolveThreats() {
      if (!threatEvents.length) {
        setResolvedEvents([]);
        setIsResolving(false);
        return;
      }

      setIsResolving(true);

      const nextEvents = await Promise.all(
        threatEvents.map(async (event) => {
          if (!event.sourceIp) {
            return null;
          }

          if (!geoCacheRef.current.has(event.sourceIp)) {
            try {
              geoCacheRef.current.set(event.sourceIp, await geocodeIp(event.sourceIp));
            } catch {
              geoCacheRef.current.set(event.sourceIp, null);
            }
          }

          const geo = geoCacheRef.current.get(event.sourceIp);
          if (!geo) {
            return null;
          }

          return {
            ...event,
            ...geo,
          };
        })
      );

      if (!cancelled) {
        setResolvedEvents(nextEvents.filter(Boolean));
        setIsResolving(false);
      }
    }

    resolveThreats();

    return () => {
      cancelled = true;
    };
  }, [threatEvents]);

  useEffect(() => {
    if (!mapRef.current || !markerLayerRef.current) {
      return;
    }

    markerLayerRef.current.clearLayers();

    resolvedEvents.forEach((event) => {
      L.marker([event.lat, event.lng], {
        icon: buildMarkerIcon(event.score),
        keyboard: false,
      })
        .bindTooltip(`${event.userName} · ${event.label}`, {
          direction: "top",
          sticky: true,
          opacity: 0.95,
          className: "soc-tooltip",
        })
        .addTo(markerLayerRef.current);
    });
  }, [resolvedEvents]);

  return (
    <section
      className={`soc-glass pointer-events-auto overflow-hidden p-4 md:p-5 ${
        compact ? "h-[300px] w-full max-w-[360px] md:h-[320px]" : "min-h-[720px]"
      }`}
    >
      {compact ? (
        <>
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <p className="soc-kicker">Threat Map</p>
              <p className="mt-2 text-xs text-soc-muted">{threatSummary}</p>
            </div>
            {isResolving ? <span className="text-xs text-soc-muted">Geocoding...</span> : null}
          </div>

          <div className="relative h-[228px] overflow-hidden rounded-[22px] border border-soc-border/80">
            <div ref={mapNodeRef} className="h-full w-full" />
            {isResolving && resolvedEvents.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center bg-soc-panel/60 text-sm text-soc-muted">
                Resolving threat origins...
              </div>
            ) : null}
          </div>
        </>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.9fr)]">
          <div className="space-y-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="soc-kicker">Threat Map</p>
                <h2 className="mt-2 text-2xl font-semibold text-soc-text">Geolocated HACKER activity</h2>
                <p className="mt-2 max-w-2xl text-sm text-soc-muted">{threatSummary}</p>
              </div>
              <div className="rounded-2xl border border-soc-border/80 bg-soc-panelSoft/55 px-4 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-soc-muted">Live markers</p>
                <p className="mt-1 text-lg font-semibold text-soc-text">{resolvedEvents.length}</p>
                <p className="mt-1 text-xs text-soc-muted">{isResolving ? "Updating geocodes..." : "Ready"}</p>
              </div>
            </div>

            <div className="relative h-[560px] overflow-hidden rounded-[24px] border border-soc-border/80">
              <div ref={mapNodeRef} className="h-full w-full" />
              {isResolving && resolvedEvents.length === 0 ? (
                <div className="absolute inset-0 flex items-center justify-center bg-soc-panel/60 text-sm text-soc-muted">
                  Resolving threat origins...
                </div>
              ) : null}
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[24px] border border-soc-border/80 bg-soc-panelSoft/45 p-4">
              <p className="soc-kicker">Legend</p>
              <div className="mt-4 space-y-3">
                {legend.map((item) => (
                  <div key={item.label} className="flex items-center gap-3">
                    <div className="soc-threat-dot shrink-0" style={{ width: `${12 + Math.round(item.score * 18)}px`, height: `${12 + Math.round(item.score * 18)}px`, transform: "none" }}>
                      <span />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-soc-text">{item.label}</p>
                      <p className="text-xs text-soc-muted">{item.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[24px] border border-soc-border/80 bg-soc-panelSoft/45 p-4">
              <p className="soc-kicker">Map Settings</p>
              <div className="mt-4 space-y-3">
                {mapSettings.map((item) => (
                  <div key={item.label} className="flex items-center justify-between gap-3 border-b border-soc-border/40 pb-2 last:border-none last:pb-0">
                    <span className="text-sm text-soc-muted">{item.label}</span>
                    <span className="text-sm font-semibold text-soc-text">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[24px] border border-soc-border/80 bg-soc-panelSoft/45 p-4">
              <p className="soc-kicker">Recent Signals</p>
              <div className="mt-4 space-y-3">
                {resolvedEvents.length === 0 ? (
                  <p className="text-sm text-soc-muted">No geolocated markers yet.</p>
                ) : (
                  resolvedEvents.slice(0, 5).map((event) => (
                    <div key={`${event.id}-${event.timestamp}`} className="rounded-2xl border border-soc-border/70 bg-soc-panel/55 p-3">
                      <div className="flex items-center justify-between gap-3 text-xs text-soc-muted">
                        <span>{event.userName}</span>
                        <span>{formatPercent(event.score)}</span>
                      </div>
                      <p className="mt-2 text-sm text-soc-text">{event.label}</p>
                      <p className="mt-1 text-xs text-soc-muted">{getRiskBand(event.score)} risk band</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
