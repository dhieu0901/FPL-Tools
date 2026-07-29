import type {
  AdminOverview,
  CupData,
  DashboardData,
  H2HFixture,
  H2HStanding,
  Highlight,
  Manager,
  MatchDetail,
  StandingEntry,
  Violation
} from "./types";

export const standings: StandingEntry[] = [
  {
    rank: 1,
    previousRank: 2,
    managerId: "m01",
    managerName: "Trần Minh Đức",
    teamName: "Hanoi Phoenix",
    division: "HIGH",
    gameweekPoints: 78,
    totalPoints: 1248,
    totw: 3,
    violations: 0,
    form: ["W", "W", "D", "W", "W"],
    qualification: "title"
  },
  {
    rank: 2,
    previousRank: 1,
    managerId: "m02",
    managerName: "Nguyễn Hoàng Nam",
    teamName: "Red River XI",
    division: "HIGH",
    gameweekPoints: 62,
    totalPoints: 1236,
    totw: 2,
    violations: 0,
    form: ["W", "L", "W", "W", "D"],
    qualification: "title"
  },
  {
    rank: 3,
    previousRank: 3,
    managerId: "m03",
    managerName: "Lê Tuấn Anh",
    teamName: "Pressing Machine",
    division: "HIGH",
    gameweekPoints: 71,
    totalPoints: 1211,
    totw: 1,
    violations: 0,
    form: ["D", "W", "W", "L", "W"],
    qualification: "championship"
  },
  {
    rank: 4,
    previousRank: 5,
    managerId: "m04",
    managerName: "Phạm Gia Huy",
    teamName: "Saigon Saints",
    division: "HIGH",
    gameweekPoints: 69,
    totalPoints: 1198,
    totw: 2,
    violations: 1,
    form: ["L", "W", "W", "W", "L"],
    qualification: "championship"
  },
  {
    rank: 5,
    previousRank: 4,
    managerId: "m05",
    managerName: "Vũ Khánh Linh",
    teamName: "Blue Lanterns",
    division: "HIGH",
    gameweekPoints: 58,
    totalPoints: 1183,
    totw: 1,
    violations: 0,
    form: ["W", "D", "L", "D", "W"],
    qualification: "cup"
  },
  {
    rank: 6,
    previousRank: 7,
    managerId: "m06",
    managerName: "Đỗ Thành Công",
    teamName: "Cầu Giấy Athletic",
    division: "HIGH",
    gameweekPoints: 75,
    totalPoints: 1176,
    totw: 1,
    violations: 0,
    form: ["W", "W", "L", "W", "W"],
    qualification: "cup"
  },
  {
    rank: 7,
    previousRank: 6,
    managerId: "m07",
    managerName: "Bùi Quang Vinh",
    teamName: "North End FC",
    division: "HIGH",
    gameweekPoints: 55,
    totalPoints: 1154,
    totw: 0,
    violations: 1,
    form: ["L", "L", "W", "D", "L"],
    qualification: "safe"
  },
  {
    rank: 8,
    previousRank: 8,
    managerId: "m08",
    managerName: "Hoàng Hải Yến",
    teamName: "Golden Boots",
    division: "HIGH",
    gameweekPoints: 64,
    totalPoints: 1142,
    totw: 1,
    violations: 0,
    form: ["D", "W", "L", "W", "D"],
    qualification: "relegation"
  },
  {
    rank: 1,
    previousRank: 1,
    managerId: "m09",
    managerName: "Mai Quốc Bảo",
    teamName: "Mekong United",
    division: "LOW",
    gameweekPoints: 73,
    totalPoints: 1168,
    totw: 2,
    violations: 0,
    form: ["W", "W", "W", "D", "W"],
    qualification: "playoff"
  },
  {
    rank: 2,
    previousRank: 3,
    managerId: "m10",
    managerName: "Ngô Minh Khang",
    teamName: "The Underdogs",
    division: "LOW",
    gameweekPoints: 77,
    totalPoints: 1152,
    totw: 3,
    violations: 0,
    form: ["W", "D", "W", "W", "W"],
    qualification: "playoff"
  },
  {
    rank: 3,
    previousRank: 2,
    managerId: "m11",
    managerName: "Trịnh Đức Long",
    teamName: "Capital Wanderers",
    division: "LOW",
    gameweekPoints: 54,
    totalPoints: 1136,
    totw: 1,
    violations: 1,
    form: ["L", "W", "D", "W", "L"],
    qualification: "playoff"
  },
  {
    rank: 4,
    previousRank: 4,
    managerId: "m12",
    managerName: "Tạ Ngọc Hà",
    teamName: "Green Tigers",
    division: "LOW",
    gameweekPoints: 67,
    totalPoints: 1120,
    totw: 0,
    violations: 0,
    form: ["D", "W", "L", "W", "D"],
    qualification: "safe"
  }
];

export const h2hStandings: H2HStanding[] = standings
  .filter((entry) => entry.division === "HIGH")
  .map((entry, index) => ({
    rank: index + 1,
    managerId: entry.managerId,
    managerName: entry.managerName,
    teamName: entry.teamName,
    played: 12,
    won: Math.max(3, 9 - index),
    drawn: index % 3,
    lost: Math.min(7, 3 + index - (index % 3)),
    pointsFor: 856 - index * 13,
    points: Math.max(8, 27 - index * 3) - (entry.violations ? 6 : 0),
    deduction: entry.violations ? 6 : 0,
    form: entry.form
  }));

export const fixtures: H2HFixture[] = [
  {
    id: "h2h-gw13-01",
    gameweek: 13,
    bracketLabel: null,
    kickoff: "2026-11-28T12:30:00+07:00",
    status: "live",
    home: {
      managerId: "m01",
      managerName: "Trần Minh Đức",
      teamName: "Hanoi Phoenix",
      score: 64,
      liveScore: 64,
      captain: "Haaland",
      activePlayers: 2
    },
    away: {
      managerId: "m04",
      managerName: "Phạm Gia Huy",
      teamName: "Saigon Saints",
      score: 59,
      liveScore: 59,
      captain: "Salah",
      activePlayers: 3
    }
  },
  {
    id: "h2h-gw13-02",
    gameweek: 13,
    bracketLabel: null,
    kickoff: "2026-11-28T12:30:00+07:00",
    status: "provisional",
    home: {
      managerId: "m02",
      managerName: "Nguyễn Hoàng Nam",
      teamName: "Red River XI",
      score: 71,
      captain: "Palmer",
      activePlayers: 0,
      isWinner: true
    },
    away: {
      managerId: "m07",
      managerName: "Bùi Quang Vinh",
      teamName: "North End FC",
      score: 55,
      captain: "Saka",
      activePlayers: 0
    }
  },
  {
    id: "h2h-gw13-03",
    gameweek: 13,
    bracketLabel: null,
    kickoff: "2026-11-29T15:00:00+07:00",
    status: "scheduled",
    home: {
      managerId: "m03",
      managerName: "Lê Tuấn Anh",
      teamName: "Pressing Machine",
      score: null
    },
    away: {
      managerId: "m06",
      managerName: "Đỗ Thành Công",
      teamName: "Cầu Giấy Athletic",
      score: null
    }
  },
  {
    id: "h2h-gw13-04",
    gameweek: 13,
    bracketLabel: null,
    kickoff: "2026-11-29T15:00:00+07:00",
    status: "scheduled",
    home: {
      managerId: "m05",
      managerName: "Vũ Khánh Linh",
      teamName: "Blue Lanterns",
      score: null
    },
    away: {
      managerId: "m08",
      managerName: "Hoàng Hải Yến",
      teamName: "Golden Boots",
      score: null
    }
  }
];

export const matchDetail: MatchDetail = {
  ...fixtures[0],
  scoreBreakdown: [
    { labelKey: "match.squadPoints", home: 71, away: 67 },
    { labelKey: "match.transferCost", home: -4, away: -8 },
    { labelKey: "match.adminAdjustment", home: -3, away: 0 },
    { labelKey: "match.netPoints", home: 64, away: 59 }
  ],
  events: [
    {
      time: "21:42",
      title: "Captain ghi điểm",
      description: "Haaland mang về 18 điểm cho Hanoi Phoenix.",
      tone: "positive"
    },
    {
      time: "20:15",
      title: "Điểm điều chỉnh",
      description: "Áp dụng -3 điểm theo quyết định VMF-2026-014.",
      tone: "negative"
    },
    {
      time: "18:30",
      title: "Đội hình được công bố",
      description: "Dữ liệu hai đội đã được đồng bộ sau deadline.",
      tone: "neutral"
    }
  ],
  ruleNote: { kind: "provisional" }
};

export const cupData: CupData = {
  season: 1,
  title: "VMF Cup · Season 1",
  qualificationWindow: "Xét điểm hợp lệ từ GW1–GW14",
  rounds: [
    {
      id: "preliminary",
      name: "Sơ loại",
      gameweek: "GW15",
      matches: [
        {
          id: "cup-pre-1",
          label: "Trận 01",
          status: "final",
          home: { ...fixtures[0].home, score: 72, isWinner: true },
          away: { ...fixtures[1].away, score: 61 },
          decidedBy: "Điểm net"
        },
        {
          id: "cup-pre-2",
          label: "Trận 02",
          status: "final",
          home: { ...fixtures[2].home, score: 58 },
          away: { ...fixtures[2].away, score: 66, isWinner: true },
          decidedBy: "Điểm net"
        },
        {
          id: "cup-pre-3",
          label: "Trận 03",
          status: "final",
          home: { ...fixtures[3].home, score: 63, isWinner: true },
          away: { ...fixtures[3].away, score: 60 },
          decidedBy: "Điểm net"
        },
        {
          id: "cup-pre-4",
          label: "Trận 04",
          status: "final",
          home: { ...fixtures[1].home, score: 69, isWinner: true },
          away: {
            managerId: "m12",
            managerName: "Tạ Ngọc Hà",
            teamName: "Green Tigers",
            score: 65
          },
          decidedBy: "Điểm net"
        }
      ]
    },
    {
      id: "quarterfinal",
      name: "Tứ kết",
      gameweek: "GW16",
      matches: [
        {
          id: "cup-qf-1",
          label: "TK 01",
          status: "final",
          home: { ...fixtures[0].home, score: 70, isWinner: true },
          away: { ...fixtures[2].away, score: 64 },
          decidedBy: "Điểm net"
        },
        {
          id: "cup-qf-2",
          label: "TK 02",
          status: "final",
          home: { ...fixtures[3].home, score: 62 },
          away: { ...fixtures[1].home, score: 68, isWinner: true },
          decidedBy: "Điểm net"
        }
      ]
    },
    {
      id: "semifinal",
      name: "Bán kết",
      gameweek: "GW17",
      matches: [
        {
          id: "cup-sf-1",
          label: "BK 01",
          status: "provisional",
          home: { ...fixtures[0].home, score: 64 },
          away: { ...fixtures[1].home, score: 67, isWinner: true }
        }
      ]
    },
    {
      id: "final",
      name: "Chung kết",
      gameweek: "GW18",
      matches: [
        {
          id: "cup-final",
          label: "Chung kết",
          status: "scheduled",
          home: {
            managerId: "tbd-1",
            managerName: "Chờ xác định",
            teamName: "Thắng BK 01",
            score: null
          },
          away: {
            managerId: "tbd-2",
            managerName: "Chờ xác định",
            teamName: "Thắng BK 02",
            score: null
          }
        }
      ]
    }
  ],
  thirdPlace: {
    id: "cup-third",
    label: "Tranh hạng ba",
    status: "scheduled",
    home: {
      managerId: "tbd-3",
      managerName: "Chờ xác định",
      teamName: "Thua BK 01",
      score: null
    },
    away: {
      managerId: "tbd-4",
      managerName: "Chờ xác định",
      teamName: "Thua BK 02",
      score: null
    }
  }
};

export const highlights: Highlight[] = [
  {
    id: "hl-01",
    category: "totw",
    eyebrow: "Đội hình tuần · GW12",
    title: "Đỗ Thành Công bứt phá",
    description: "Ba cầu thủ hai chữ số giúp Cầu Giấy Athletic vượt trung bình division 22 điểm.",
    value: "94 điểm",
    managerName: "Đỗ Thành Công",
    gameweek: 12
  },
  {
    id: "hl-02",
    category: "comeback",
    eyebrow: "Cuộc lội ngược dòng",
    title: "Từ 18% lên 72%",
    description: "Red River XI đảo chiều cặp H2H sau cú đúp của captain trong trận đấu muộn.",
    value: "+19 điểm",
    managerName: "Nguyễn Hoàng Nam",
    gameweek: 11
  },
  {
    id: "hl-03",
    category: "record",
    eyebrow: "Kỷ lục mùa giải",
    title: "Khoảng cách sít sao nhất",
    description: "Blue Lanterns thắng Golden Boots đúng một điểm sau khi autosub hoàn tất.",
    value: "68–67",
    managerName: "Vũ Khánh Linh",
    gameweek: 9
  },
  {
    id: "hl-04",
    category: "notice",
    eyebrow: "Thông báo điều hành",
    title: "Chốt điểm GW12",
    description: "Toàn bộ kết quả đã được finalize. Một điều chỉnh có audit log được áp dụng.",
    gameweek: 12
  }
];

const seededManagers: Manager[] = standings.map((entry, index) => ({
  id: entry.managerId,
  name: entry.managerName,
  teamName: entry.teamName,
  division: entry.division,
  rank: entry.rank,
  gameweekPoints: entry.gameweekPoints,
  totalPoints: entry.totalPoints,
  totw: entry.totw,
  h2hPoints: entry.division === "HIGH" ? (h2hStandings[index]?.points ?? 0) : 0,
  violations: entry.violations,
  status: index === 7 ? "locked" : "active",
  joinedAt: `2026-07-${String(2 + index).padStart(2, "0")}T10:00:00+07:00`
}));

const additionalManagerSeeds = [
  ["Nguyễn Anh Tú", "Old Quarter FC"],
  ["Lương Mạnh Hùng", "Tactical Owls"],
  ["Đặng Việt Dũng", "West Lake City"],
  ["Dương Thanh Tâm", "Sunday Strikers"],
  ["Chu Hoàng Sơn", "Black Star XI"],
  ["Trần Khánh An", "Long Biên Rovers"],
  ["Lê Nhật Minh", "Violet Storm"],
  ["Phan Đình Quân", "Haiphong Waves"],
  ["Nguyễn Phương Thảo", "Lotus Athletic"],
  ["Đỗ Minh Trí", "Rising Dragons"],
  ["Bùi Anh Khoa", "No Hit United"],
  ["Võ Quốc Việt", "Da Nang Breeze"],
  ["Trương Ngọc Hân", "Emerald Eleven"],
  ["Hồ Gia Bảo", "Bench Boosters"],
  ["Lâm Đức Anh", "Maverick FC"],
  ["Phạm Quỳnh Mai", "The Captains"],
  ["Ngô Thành Đạt", "East Gate City"],
  ["Vũ Hải Đăng", "Deadline Crew"],
  ["Tô Minh Châu", "Northern Lights"],
  ["Cao Tuấn Kiệt", "Last Minute FC"]
] as const;

export const managers: Manager[] = [
  ...seededManagers,
  ...additionalManagerSeeds.map(([name, teamName], index): Manager => {
    const division = index < 8 ? "HIGH" : "LOW";
    const rank = index < 8 ? index + 9 : index - 3;
    return {
      id: `m${String(index + 13).padStart(2, "0")}`,
      name,
      teamName,
      division,
      rank,
      gameweekPoints: 61 - (index % 9),
      totalPoints: division === "HIGH" ? 1130 - index * 9 : 1102 - (index - 8) * 11,
      totw: index % 5 === 0 ? 1 : 0,
      h2hPoints: Math.max(4, 18 - (index % 8) * 2),
      violations: 0,
      status: "active",
      joinedAt: `2026-08-${String(index + 1).padStart(2, "0")}T10:00:00+07:00`
    };
  })
];

export const violations: Violation[] = [
  {
    id: "vio-014",
    managerId: "m04",
    managerName: "Phạm Gia Huy",
    teamName: "Saigon Saints",
    division: "HIGH",
    gameweek: 13,
    reason: "Chi phí chuyển nhượng vượt ngưỡng -12",
    transferCost: 16,
    severity: 1,
    status: "pending",
    impact: ["h2hDeduction", "cupZero"],
    createdAt: "2026-11-28T18:05:00+07:00"
  },
  {
    id: "vio-013",
    managerId: "m11",
    managerName: "Trịnh Đức Long",
    teamName: "Capital Wanderers",
    division: "LOW",
    gameweek: 12,
    reason: "Chi phí chuyển nhượng -20",
    transferCost: 20,
    severity: 2,
    status: "confirmed",
    impact: ["h2hDeduction", "level2Warning", "cupZero"],
    createdAt: "2026-11-21T17:56:00+07:00"
  },
  {
    id: "vio-012",
    managerId: "m07",
    managerName: "Bùi Quang Vinh",
    teamName: "North End FC",
    division: "HIGH",
    gameweek: 11,
    reason: "Yêu cầu exception chip đã được duyệt",
    transferCost: 12,
    severity: 1,
    status: "waived",
    impact: ["keepTransferHit", "waived"],
    createdAt: "2026-11-14T16:42:00+07:00"
  }
];

export const dashboardData: DashboardData = {
  season: "2026/27",
  gameweek: {
    number: 13,
    name: "Gameweek 13",
    state: "live",
    deadline: "2026-11-27T18:30:00+07:00",
    progress: 70,
    fixturesComplete: 7,
    fixturesTotal: 10
  },
  metrics: [
    {
      labelKey: "metric.managers",
      value: "32",
      detailKey: "metric.managersDetail",
      tone: "blue"
    },
    {
      labelKey: "metric.divisionHigh",
      value: "16",
      detailKey: "metric.divisionDetail",
      tone: "lime"
    },
    {
      labelKey: "metric.divisionLow",
      value: "16",
      detailKey: "metric.divisionDetail",
      tone: "coral"
    },
    {
      labelKey: "metric.h2hMatches",
      value: "16",
      detailKey: "metric.h2hScheduled",
      detailVars: { gameweek: 12 },
      tone: "neutral"
    }
  ],
  featuredFixture: fixtures[0],
  standings: standings.slice(0, 6),
  recentHighlights: highlights.slice(0, 3),
  notices: [
    {
      id: "notice-01",
      title: "Kết quả GW13 đang tạm tính",
      body: "Điểm bonus và autosub có thể tiếp tục thay đổi tới khi FPL chốt dữ liệu.",
      publishedAt: "2026-11-28T09:00:00+07:00",
      priority: "important"
    },
    {
      id: "notice-02",
      title: "Cửa sổ xác nhận Cup Season 1",
      body: "Danh sách suất dự Cup sẽ khóa ngay sau khi GW14 được finalize.",
      publishedAt: "2026-11-25T20:00:00+07:00",
      priority: "normal"
    }
  ]
};

export const adminOverview: AdminOverview = {
  sync: {
    state: "healthy",
    lastSuccessfulAt: "2026-11-28T22:41:00+07:00",
    nextRunAt: "2026-11-28T22:42:00+07:00",
    latencySeconds: 18
  },
  counts: {
    managers: 32,
    provisionalScores: 8,
    pendingViolations: 1,
    lockedTeams: 1
  },
  divisionAverages: [
    { division: "HIGH", gameweek: 13, average: 67, eligibleManagers: 14 },
    { division: "LOW", gameweek: 13, average: 63, eligibleManagers: 16 }
  ],
  recentJobs: [
    {
      id: "job-1028",
      name: "Đồng bộ live points",
      status: "success",
      startedAt: "2026-11-28T22:41:00+07:00",
      duration: "4,2 giây"
    },
    {
      id: "job-1027",
      name: "Phát hiện violation",
      status: "success",
      startedAt: "2026-11-28T22:40:00+07:00",
      duration: "1,1 giây"
    },
    {
      id: "job-1026",
      name: "Tính bảng H2H",
      status: "success",
      startedAt: "2026-11-28T22:39:00+07:00",
      duration: "0,8 giây"
    }
  ]
};
