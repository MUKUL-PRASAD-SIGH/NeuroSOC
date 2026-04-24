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
  {
    userId: "usr-4051",
    userName: "Priya Nair",
    sourceIp: "185.199.108.153",
    locationLabel: "Singapore, SG",
  },
  {
    userId: "usr-4058",
    userName: "Omar Haddad",
    sourceIp: "77.88.8.8",
    locationLabel: "Dubai, AE",
  },
  {
    userId: "usr-4064",
    userName: "Sofia Alvarez",
    sourceIp: "52.95.110.1",
    locationLabel: "Madrid, ES",
  },
  {
    userId: "usr-4072",
    userName: "Ethan Brooks",
    sourceIp: "13.107.42.14",
    locationLabel: "Seattle, US",
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
  {
    verdict: "HACKER",
    severity: "high",
    score: 0.94,
    message: "Synthetic account takeover chain reached transfer staging controls.",
  },
  {
    verdict: "FORGETFUL_USER",
    severity: "medium",
    score: 0.58,
    message: "Password reset loop matched low-confidence recovery friction pattern.",
  },
  {
    verdict: "LEGITIMATE",
    severity: "low",
    score: 0.12,
    message: "Known device resumed normal transaction cadence after MFA success.",
  },
  {
    verdict: "HACKER",
    severity: "high",
    score: 0.89,
    message: "Botnet-origin login spray exceeded adaptive rate-limit thresholds.",
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
  buildAlert(0, 3),
  buildAlert(1, 7),
  buildAlert(2, 14),
  buildAlert(3, 21),
  buildAlert(4, 28, {
    verdict: "HACKER",
    severity: "high",
    sourceIp: "208.80.152.201",
    locationLabel: "Ashburn, US",
  }),
  buildAlert(5, 34, {
    verdict: "FORGETFUL_USER",
    severity: "medium",
    sourceIp: "4.2.2.2",
    locationLabel: "Chicago, US",
  }),
  buildAlert(6, 42, {
    verdict: "LEGITIMATE",
    severity: "low",
    sourceIp: "64.6.64.6",
    locationLabel: "Los Angeles, US",
  }),
  buildAlert(7, 55, {
    verdict: "HACKER",
    severity: "high",
    sourceIp: "208.67.220.220",
    locationLabel: "Toronto, CA",
  }),
  buildAlert(8, 66, {
    sourceIp: "151.101.1.69",
    locationLabel: "Frankfurt, DE",
  }),
  buildAlert(9, 79, {
    verdict: "FORGETFUL_USER",
    severity: "medium",
    sourceIp: "23.205.89.14",
    locationLabel: "Atlanta, US",
  }),
  buildAlert(10, 93, {
    verdict: "HACKER",
    severity: "high",
    score: 0.96,
    sourceIp: "45.83.64.1",
    locationLabel: "Bucharest, RO",
  }),
  buildAlert(11, 109, {
    verdict: "LEGITIMATE",
    severity: "low",
    score: 0.16,
    sourceIp: "34.149.120.5",
    locationLabel: "Dallas, US",
  }),
  buildAlert(12, 126, {
    verdict: "HACKER",
    severity: "high",
    sourceIp: "103.21.244.0",
    locationLabel: "Mumbai, IN",
  }),
  buildAlert(13, 144, {
    verdict: "FORGETFUL_USER",
    severity: "medium",
    sourceIp: "203.0.113.44",
    locationLabel: "Melbourne, AU",
  }),
  buildAlert(14, 168, {
    verdict: "LEGITIMATE",
    severity: "low",
    sourceIp: "198.51.100.18",
    locationLabel: "Denver, US",
  }),
  buildAlert(15, 191, {
    verdict: "HACKER",
    severity: "high",
    score: 0.92,
    sourceIp: "91.198.174.192",
    locationLabel: "London, GB",
  }),
  buildAlert(16, 228, {
    verdict: "HACKER",
    severity: "high",
    sourceIp: "104.244.42.1",
    locationLabel: "Phoenix, US",
  }),
  buildAlert(17, 264, {
    verdict: "FORGETFUL_USER",
    severity: "medium",
    sourceIp: "31.13.71.36",
    locationLabel: "Dublin, IE",
  }),
  buildAlert(18, 305, {
    verdict: "LEGITIMATE",
    severity: "low",
    sourceIp: "172.217.14.206",
    locationLabel: "Austin, US",
  }),
  buildAlert(19, 349, {
    verdict: "HACKER",
    severity: "high",
    sourceIp: "203.0.113.99",
    locationLabel: "Warsaw, PL",
  }),
  buildAlert(20, 408, {
    verdict: "FORGETFUL_USER",
    severity: "medium",
    sourceIp: "198.51.100.77",
    locationLabel: "Boston, US",
  }),
  buildAlert(21, 482, {
    verdict: "LEGITIMATE",
    severity: "low",
    sourceIp: "20.99.132.1",
    locationLabel: "Amsterdam, NL",
  }),
  buildAlert(22, 577, {
    verdict: "HACKER",
    severity: "high",
    score: 0.9,
    sourceIp: "185.220.101.4",
    locationLabel: "Prague, CZ",
  }),
  buildAlert(23, 691, {
    verdict: "HACKER",
    severity: "high",
    score: 0.88,
    sourceIp: "198.18.0.45",
    locationLabel: "Sao Paulo, BR",
  }),
];

export const mockStats = {
  totalTransactions: 286451,
  hackerDetections: 18234,
  avgRiskScore: 52.84,
  liveAlerts: mockAlerts.length,
};

export const mockModelStatus = {
  versions: [
    { label: "Primary", value: "neuroshield-xgb-2026.04.24" },
    { label: "Shadow", value: "neuroshield-transformer-2026.04.22" },
    { label: "Ruleset", value: "velocity-guard-v3.9.1" },
  ],
  validationF1: [
    { label: "HACKER", value: 0.98 },
    { label: "FORGETFUL_USER", value: 0.93 },
    { label: "LEGITIMATE", value: 0.96 },
  ],
  lastRetrainedAt: "2026-04-24T04:30:00.000Z",
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
