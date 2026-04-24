const DIMENSION_LABELS = [
  "Velocity",
  "Session Drift",
  "Bot Pressure",
  "Credential Risk",
  "Geo Variance",
  "Device Novelty",
  "Typing Rhythm",
  "Mouse Entropy",
  "Route Depth",
  "Auth Friction",
  "Token Churn",
  "Transfer Heat",
  "Time Deviation",
  "Privilege Lift",
  "IP Reputation",
  "Cashout Risk",
  "Login Burst",
  "Browser Trust",
  "Peer Similarity",
  "Recovery Abuse",
];

const USER_FIXTURES = [
  {
    userId: "usr-4012",
    userName: "Ava Morales",
    sourceIp: "8.8.8.8",
    locationLabel: "Mountain View, US",
  },
  {
    userId: "usr-4018",
    userName: "Leo Bennett",
    sourceIp: "1.1.1.1",
    locationLabel: "Sydney, AU",
  },
  {
    userId: "usr-4023",
    userName: "Mia Chen",
    sourceIp: "208.67.222.222",
    locationLabel: "San Francisco, US",
  },
  {
    userId: "usr-4040",
    userName: "Noah Carter",
    sourceIp: "9.9.9.9",
    locationLabel: "New York, US",
  },
];

const ALERT_TEMPLATES = [
  {
    verdict: "HACKER",
    severity: "high",
    score: 0.97,
    message: "Credential stuffing burst tripped cross-tenant anomaly guardrails.",
  },
  {
    verdict: "FORGETFUL_USER",
    severity: "medium",
    score: 0.64,
    message: "Repeat MFA failures match known forgetful-user recovery pattern.",
  },
  {
    verdict: "LEGITIMATE",
    severity: "low",
    score: 0.18,
    message: "Verified payment spike aligns with seasonal payroll behavior.",
  },
  {
    verdict: "HACKER",
    severity: "high",
    score: 0.91,
    message: "Impossible-travel login paired with high-risk device fingerprint.",
  },
];

function buildDimensions(seed) {
  return DIMENSION_LABELS.map((subject, index) => ({
    subject,
    value: 22 + ((seed * 11 + index * 7) % 72),
  }));
}

function buildRecentVerdicts(primaryVerdict, seed) {
  return Array.from({ length: 10 }).map((_, index) => {
    const cycle = ["LEGITIMATE", "FORGETFUL_USER", "HACKER"];
    const verdict = index === 0 ? primaryVerdict : cycle[(seed + index) % cycle.length];
    return {
      id: `verdict-${seed}-${index}`,
      verdict,
      score: Number((0.2 + ((seed + index) % 7) * 0.1).toFixed(2)),
      timestamp: new Date(Date.now() - (index + 1) * 36 * 60 * 1000).toISOString(),
    };
  });
}

function buildAlert(index, offsetMinutes, override = {}) {
  const template = ALERT_TEMPLATES[index % ALERT_TEMPLATES.length];
  const user = USER_FIXTURES[index % USER_FIXTURES.length];
  const verdict = override.verdict || template.verdict;

  return {
    id: `alert-${index + 1}`,
    severity: override.severity || template.severity,
    verdict,
    score: override.score ?? template.score,
    message: override.message || template.message,
    timestamp: new Date(Date.now() - offsetMinutes * 60 * 1000).toISOString(),
    sourceIp: override.sourceIp || user.sourceIp,
    userId: user.userId,
    userName: user.userName,
    locationLabel: user.locationLabel,
    dimensions: buildDimensions(index + 1),
    recentVerdicts: buildRecentVerdicts(verdict, index + 1),
    modelVersion: "neuroshield-xgb-2026.04.20",
  };
}

export const mockAlerts = [
  buildAlert(0, 4),
  buildAlert(1, 12),
  buildAlert(2, 25),
  buildAlert(3, 37),
  buildAlert(4, 54, {
    verdict: "HACKER",
    severity: "high",
    sourceIp: "208.80.152.201",
    locationLabel: "Ashburn, US",
  }),
  buildAlert(5, 83, {
    verdict: "FORGETFUL_USER",
    severity: "medium",
    sourceIp: "4.2.2.2",
    locationLabel: "Chicago, US",
  }),
  buildAlert(6, 180, {
    verdict: "LEGITIMATE",
    severity: "low",
    sourceIp: "64.6.64.6",
    locationLabel: "Los Angeles, US",
  }),
  buildAlert(7, 410, {
    verdict: "HACKER",
    severity: "high",
    sourceIp: "208.67.220.220",
    locationLabel: "Toronto, CA",
  }),
];

export const mockStats = {
  totalTransactions: 14520,
  hackerDetections: 318,
  avgRiskScore: 47.21,
  liveAlerts: mockAlerts.length,
};

export const mockModelStatus = {
  versions: [
    { label: "Primary", value: "neuroshield-xgb-2026.04.20" },
    { label: "Shadow", value: "neuroshield-transformer-2026.04.18" },
  ],
  validationF1: [
    { label: "HACKER", value: 0.97 },
    { label: "FORGETFUL_USER", value: 0.91 },
    { label: "LEGITIMATE", value: 0.95 },
  ],
  lastRetrainedAt: "2026-04-20T04:30:00.000Z",
};

export function buildTimelineData(alerts) {
  const buckets = new Map();

  alerts.forEach((alert) => {
    const date = new Date(alert.timestamp);
    const key = new Date(date.getFullYear(), date.getMonth(), date.getDate(), date.getHours()).toISOString();
    if (!buckets.has(key)) {
      buckets.set(key, {
        time: key,
        HACKER: 0,
        FORGETFUL_USER: 0,
        LEGITIMATE: 0,
      });
    }
    buckets.get(key)[alert.verdict] += 1;
  });

  return [...buckets.values()].sort((a, b) => new Date(a.time) - new Date(b.time));
}

let mockCounter = mockAlerts.length;

export function createMockAlert() {
  mockCounter += 1;
  const template = ALERT_TEMPLATES[mockCounter % ALERT_TEMPLATES.length];
  const verdict = template.verdict;

  return buildAlert(mockCounter, 0, {
    verdict,
    severity: template.severity,
    score: Number((template.score - (mockCounter % 3) * 0.03).toFixed(2)),
  });
}
