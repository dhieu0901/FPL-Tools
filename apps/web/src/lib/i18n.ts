export const LOCALES = ["vi", "en"] as const;

export type Locale = (typeof LOCALES)[number];

/** Vietnamese is the default: the 40 managers of the league are Vietnamese. */
export const DEFAULT_LOCALE: Locale = "vi";

export const LOCALE_COOKIE = "vmf_locale";

/** One year, so a manager picks a language once per season. */
export const LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && LOCALES.includes(value as Locale);
}

const messages = {
  "locale.switch": { vi: "Ngôn ngữ", en: "Language" },
  "locale.vi": { vi: "Tiếng Việt", en: "Vietnamese" },
  "locale.en": { vi: "Tiếng Anh", en: "English" },

  "common.viewAll": { vi: "Xem tất cả", en: "View all" },
  "common.details": { vi: "Chi tiết", en: "Details" },
  "common.retry": { vi: "Thử lại", en: "Try again" },
  "common.season": { vi: "Mùa giải", en: "Season" },
  "common.all": { vi: "Tất cả", en: "All" },
  "common.rank": { vi: "Hạng", en: "Rank" },
  "common.team": { vi: "Đội bóng", en: "Team" },
  "common.form": { vi: "Phong độ", en: "Form" },
  "common.total": { vi: "Tổng", en: "Total" },
  "common.points": { vi: "Điểm", en: "Points" },
  "common.profileCount": { vi: "{count} hồ sơ", en: "{count} profiles" },
  "common.formAria": { vi: "Phong độ: {form}", en: "Form: {form}" },
  "common.contentOptions": { vi: "Lựa chọn nội dung", en: "Content options" },

  "skip.toContent": { vi: "Đi tới nội dung chính", en: "Skip to main content" },
  "brand.tagline": { vi: "Văn Minh Fantasy", en: "Văn Minh Fantasy" },
  "footer.season": { vi: "Mùa giải 2026/27", en: "Season 2026/27" },
  "footer.note": {
    vi: "Dữ liệu điểm số được đồng bộ và kiểm toán theo luật giải.",
    en: "Scoring data is synchronized and audited against the league rulebook."
  },
  "footer.status": { vi: "Minh bạch nguồn dữ liệu", en: "Transparent data provenance" },

  "nav.main": { vi: "Điều hướng chính", en: "Main navigation" },
  "nav.mobile": { vi: "Điều hướng di động", en: "Mobile navigation" },
  "nav.admin": { vi: "Điều hướng quản trị", en: "Admin navigation" },
  "nav.overview": { vi: "Tổng quan", en: "Overview" },
  "nav.classic": { vi: "Classic", en: "Classic" },
  "nav.h2h": { vi: "H2H", en: "H2H" },
  "nav.cup": { vi: "Cup", en: "Cup" },
  "nav.highlights": { vi: "Highlights", en: "Highlights" },
  "nav.managers": { vi: "Managers", en: "Managers" },
  "nav.control": { vi: "Điều hành", en: "Admin" },
  "nav.violations": { vi: "Vi phạm", en: "Violations" },

  "data.mock": { vi: "Dữ liệu minh hoạ", en: "Illustrative data" },
  "data.unavailable": { vi: "Chưa có nguồn dữ liệu", en: "No data source yet" },
  "data.live": { vi: "Đã kết nối API", en: "API connected" },
  "data.respondedAt": { vi: "· phản hồi {time}", en: "· responded {time}" },

  "state.preseason": { vi: "Chưa bắt đầu", en: "Not started" },
  "state.open": { vi: "Đang mở", en: "Open" },
  "state.live": { vi: "Đang diễn ra", en: "In progress" },
  "state.provisional": { vi: "Tạm tính", en: "Provisional" },
  "state.final": { vi: "Đã chốt", en: "Final" },
  "match.scheduled": { vi: "Sắp diễn ra", en: "Scheduled" },
  "match.live": { vi: "Trực tiếp", en: "Live" },
  "match.provisional": { vi: "Tạm tính", en: "Provisional" },
  "match.final": { vi: "Đã chốt", en: "Final" },
  "match.walkover": { vi: "Xử thắng", en: "Walkover" },

  "zone.title": { vi: "Đua vô địch", en: "Title race" },
  "zone.championship": { vi: "Championship", en: "Championship" },
  "zone.cup": { vi: "Suất Cup", en: "Cup place" },
  "zone.playoff": { vi: "Play-off", en: "Play-off" },
  "zone.safe": { vi: "An toàn", en: "Safe" },
  "zone.relegation": { vi: "Xuống hạng", en: "Relegation" },

  "dashboard.title": { vi: "Tổng quan", en: "Overview" },
  "dashboard.eyebrow": { vi: "Văn Minh Fantasy League", en: "Văn Minh Fantasy League" },
  "dashboard.headline1": { vi: "Mỗi điểm số.", en: "Every point." },
  "dashboard.headline2": { vi: "Đều có câu chuyện.", en: "Tells a story." },
  "dashboard.lede": {
    vi: "Theo dõi Classic, đối đầu H2H và hành trình Cup trên một bảng điều hành minh bạch, cập nhật xuyên suốt mùa giải.",
    en: "Follow the Classic race, head-to-head duels and the Cup run on one transparent dashboard, updated all season."
  },
  "dashboard.viewStandings": { vi: "Xem bảng xếp hạng", en: "View standings" },
  "dashboard.fixtures": { vi: "Lịch đối đầu", en: "Fixtures" },
  "dashboard.gameweekProgress": { vi: "Tiến độ Gameweek", en: "Gameweek progress" },
  "dashboard.completed": { vi: "Hoàn thành", en: "Completed" },
  "dashboard.matchesShort": { vi: "trận", en: "matches" },
  "dashboard.deadline": { vi: "Deadline", en: "Deadline" },
  "dashboard.deadlineUnknown": { vi: "Chưa công bố", en: "Not published" },
  "dashboard.quickMetrics": { vi: "Chỉ số nhanh", en: "Key metrics" },
  // Position and bench labels stay in English in both locales: these are the
  // terms FPL itself uses, so a manager reads them faster than a translation.
  "squad.gk": { vi: "GK", en: "GK" },
  "squad.def": { vi: "DEF", en: "DEF" },
  "squad.mid": { vi: "MID", en: "MID" },
  "squad.fwd": { vi: "FWD", en: "FWD" },
  "squad.gkSub": { vi: "GK Sub", en: "GK Sub" },
  "squad.bench": { vi: "Bench {order}", en: "Bench {order}" },
  "squad.benchHeading": { vi: "Bench", en: "Bench" },
  "squad.doubleGameweek": {
    vi: "Đá hai trận trong vòng này",
    en: "Plays twice this Gameweek"
  },
  "squad.unavailable": {
    vi: "Đội hình chưa công bố. FPL chỉ mở sau deadline.",
    en: "Squad not published yet. FPL opens it after the deadline."
  },
  "match.squadOf": { vi: "Đội hình · {team}", en: "Squad · {team}" },
  "match.remainingPlayers": { vi: "Cầu thủ chưa đá", en: "Players still to play" },
  "match.remainingDetail": {
    vi: "{players} người · {fixtures} trận · hệ số {effective}",
    en: "{players} players · {fixtures} fixtures · {effective} effective"
  },
  "match.sharedPlayers": { vi: "Cầu thủ trùng nhau", en: "Shared players" },
  "match.sharedNote": {
    vi: "Hai bên dùng giống hệt nhau nên không làm thay đổi cách biệt.",
    en: "Fielded identically by both sides, so they cannot change the margin."
  },
  "match.differentials": { vi: "Điểm khác biệt", en: "Differentials" },
  "match.differentialsNote": {
    vi: "Dấu cộng nghiêng về đội nhà, dấu trừ nghiêng về đội khách.",
    en: "A positive swing favours the home side, a negative one the away side."
  },
  "match.noDifferentials": {
    vi: "Chưa có cầu thủ khác biệt nào.",
    en: "No differentials yet."
  },
  "highlight.team_of_the_week.eyebrow": { vi: "Đội hình tuần", en: "Team of the Week" },
  "highlight.team_of_the_week.title": {
    vi: "{team} dẫn đầu vòng này",
    en: "{team} tops the Gameweek"
  },
  "highlight.team_of_the_week.body": {
    vi: "{manager} đạt {value} điểm thuần, cao nhất trong 40 HLV ở GW{gameweek}.",
    en: "{manager} scored {value} net points, the highest of the forty in GW{gameweek}."
  },
  "highlight.season_high.eyebrow": { vi: "Kỷ lục mùa giải", en: "Season record" },
  "highlight.season_high.title": {
    vi: "Điểm cao nhất mùa: {value}",
    en: "Season high: {value}"
  },
  "highlight.season_high.body": {
    vi: "{manager} lập mốc {value} điểm ở GW{gameweek}, chưa ai vượt qua.",
    en: "{manager} set {value} points in GW{gameweek}, still unbeaten."
  },
  "highlight.captain_haul.eyebrow": { vi: "Băng đội trưởng", en: "The armband" },
  "highlight.captain_haul.title": {
    vi: "Đội trưởng của {team} bùng nổ",
    en: "A captain haul for {team}"
  },
  "highlight.captain_haul.body": {
    vi: "Riêng băng đội trưởng mang về {value} điểm ở GW{gameweek}.",
    en: "The armband alone returned {value} points in GW{gameweek}."
  },
  "highlight.totw_leader.eyebrow": { vi: "Dẫn đầu TotW", en: "TotW leader" },
  "highlight.totw_leader.title": {
    vi: "{team} có {value} lần đội hình tuần",
    en: "{team} leads with {value} TotW awards"
  },
  "highlight.totw_leader.body": {
    vi: "{manager} đang giữ nhiều danh hiệu đội hình tuần nhất mùa này.",
    en: "{manager} holds more Team of the Week awards than anyone this season."
  },
  "highlight.bench_regret.eyebrow": { vi: "Tiếc nuối", en: "Bench regret" },
  "highlight.bench_regret.title": {
    vi: "{team} bỏ phí {value} điểm trên băng ghế",
    en: "{team} left {value} points on the bench"
  },
  "highlight.bench_regret.body": {
    vi: "Số điểm này thuộc về những cầu thủ không được xếp đá chính ở GW{gameweek}.",
    en: "Those points belong to players who were not in the eleven in GW{gameweek}."
  },
  "highlight.provisional": { vi: "Tạm tính", en: "Provisional" },
  "match.chip": { vi: "Chip", en: "Chip" },
  "match.benchPoints": { vi: "Điểm băng ghế", en: "Bench points" },
  "metric.managers": { vi: "Quản lý", en: "Managers" },
  "metric.managersDetail": { vi: "Hồ sơ đã đăng ký", en: "Registered profiles" },
  "metric.divisionHigh": { vi: "Division HIGH", en: "Division HIGH" },
  "metric.divisionLow": { vi: "Division LOW", en: "Division LOW" },
  "metric.divisionDetail": { vi: "Quản lý", en: "Managers" },
  "metric.h2hMatches": { vi: "Trận H2H", en: "H2H matches" },
  "metric.h2hScheduled": {
    vi: "Đã xếp cho GW{gameweek}",
    en: "Scheduled for GW{gameweek}"
  },
  "metric.h2hBeforeStart": { vi: "Chưa đến GW1", en: "Before GW1" },
  "dashboard.spotlightEyebrow": { vi: "Tâm điểm vòng đấu", en: "Round spotlight" },
  "dashboard.spotlightTitle": { vi: "Đối đầu nổi bật", en: "Featured matchup" },
  "dashboard.allMatches": { vi: "Mọi trận đấu", en: "All matches" },
  "dashboard.noFixtureTitle": { vi: "Chưa có lịch H2H", en: "No H2H schedule yet" },
  "dashboard.noFixtureBody": {
    vi: "Lịch thi đấu sẽ xuất hiện sau khi admin tạo schedule.",
    en: "Fixtures appear once an administrator generates the schedule."
  },
  "dashboard.organiser": { vi: "Ban tổ chức", en: "Organisers" },
  "dashboard.notices": { vi: "Thông báo", en: "Announcements" },
  "dashboard.noNoticeTitle": { vi: "Chưa có thông báo", en: "No announcements" },
  "dashboard.noNoticeBody": {
    vi: "Admin chưa đăng thông báo mới.",
    en: "No administrator announcement has been published yet."
  },
  "dashboard.classicEyebrow": { vi: "Division HIGH", en: "HIGH division" },
  "dashboard.classicTitle": { vi: "Cuộc đua Classic", en: "The Classic race" },
  "dashboard.classicBody": {
    vi: "Bảng điểm tạm tính sau các trận đã hoàn tất.",
    en: "Provisional standings after the fixtures played so far."
  },
  "dashboard.momentsEyebrow": { vi: "Khoảnh khắc VMF", en: "VMF moments" },
  "dashboard.momentsTitle": { vi: "Highlights mới nhất", en: "Latest highlights" },
  "dashboard.noHighlightTitle": {
    vi: "Highlights đang được hoàn thiện",
    en: "Highlights are still being built"
  },
  "dashboard.noHighlightBody": {
    vi: "Backend hiện chưa cung cấp nguồn highlights.",
    en: "The backend does not expose a highlights source yet."
  },

  "classic.title": { vi: "Bảng Classic", en: "Classic table" },
  "classic.heading": { vi: "Bảng xếp hạng", en: "Standings" },
  "classic.description": {
    vi: "Xếp hạng theo tổng điểm FPL net của đúng giai đoạn và division đã chọn.",
    en: "Ranked by net FPL points within the selected period and division only."
  },
  "classic.divisionHigh": { vi: "Division HIGH", en: "HIGH division" },
  "classic.divisionLow": { vi: "Division LOW", en: "LOW division" },
  "classic.teamsShown": { vi: "{count} đội đang hiển thị", en: "{count} teams shown" },
  "classic.season1": { vi: "Season 1 · GW1–19", en: "Season 1 · GW1–19" },
  "classic.season2": { vi: "Season 2 · GW20–38", en: "Season 2 · GW20–38" },
  "classic.fullSeason": { vi: "Cả mùa", en: "Full season" },
  "classic.tieBreakTitle": { vi: "Nguyên tắc xếp hạng", en: "Ranking rules" },
  "classic.tieBreakBody": {
    vi: "Khi bằng tổng điểm: số lần TotW → điểm GW cao nhất → quyết định có audit log của ban tổ chức.",
    en: "On equal points: cumulative TotW → highest single Gameweek score → an audited organiser decision."
  },

  "h2h.title": { vi: "H2H League", en: "H2H league" },
  "h2h.heading": { vi: "Bảng đấu H2H", en: "Head-to-head table" },
  "h2h.description": {
    vi: "Mỗi gameweek là một cuộc đối đầu. Thắng 3 điểm, hoà 1 điểm; vi phạm được khấu trừ riêng theo luật giải.",
    en: "Every Gameweek is a duel. A win is 3 points, a draw 1; violations are deducted separately under the rulebook."
  },
  "h2h.standings": { vi: "Bảng xếp hạng", en: "Standings" },
  "h2h.fixtures": { vi: "Lịch & kết quả", en: "Fixtures & results" },
  "h2h.groupStage": { vi: "Vòng bảng · GW1–GW35", en: "Group stage · GW1–GW35" },
  "h2h.playoffSlot": { vi: "Suất play-off", en: "Play-off places" },
  "h2h.top8": { vi: "Top 8", en: "Top 8" },
  "h2h.afterGw35": { vi: "Sau GW35", en: "After GW35" },
  "h2h.quarterFinal": { vi: "Tứ kết", en: "Quarter-finals" },
  "h2h.quarterFinalGw": { vi: "GW36", en: "GW36" },
  "h2h.semiFinal": { vi: "Bán kết", en: "Semi-finals" },
  "h2h.semiFinalGw": { vi: "GW37", en: "GW37" },
  "h2h.final": { vi: "Chung kết", en: "Final" },
  "h2h.finalGw": { vi: "GW38", en: "GW38" },
  "h2h.noThirdPlace": { vi: "Không tranh hạng ba", en: "No third-place match" },
  "h2h.sharedThird": {
    vi: "Hai đội thua bán kết đồng hạng ba",
    en: "Both losing semi-finalists share third"
  },
  "h2h.immutableTitle": { vi: "Kết quả đã chốt là bất biến", en: "A final result is immutable" },
  "h2h.immutableBody": {
    vi: "Chỉ admin có thể mở lại gameweek đã finalize; mọi thay đổi bắt buộc có lý do và nhật ký kiểm toán.",
    en: "Only an administrator may reopen a finalized Gameweek, and every change requires a reason and an audit entry."
  },
  "h2h.played": { vi: "Trận", en: "P" },
  "h2h.won": { vi: "Thắng", en: "W" },
  "h2h.drawn": { vi: "Hoà", en: "D" },
  "h2h.lost": { vi: "Thua", en: "L" },
  "h2h.pointsFor": { vi: "Điểm ghi", en: "Points for" },
  "h2h.groupLabel": { vi: "Vòng bảng", en: "Group stage" },

  "fixtures.title": { vi: "Lịch H2H", en: "H2H fixtures" },
  "fixtures.heading": { vi: "Lịch & kết quả", en: "Fixtures & results" },
  "fixtures.description": {
    vi: "Điểm live có thể thay đổi cho tới khi gameweek được finalize.",
    en: "Live scores can still change until the Gameweek is finalized."
  },
  "fixtures.gameweek": { vi: "Vòng đấu", en: "Gameweek" },
  "fixtures.apply": { vi: "Xem", en: "Show" },
  "fixtures.empty": {
    vi: "Chưa có trận H2H nào được xếp cho GW{gameweek}.",
    en: "No H2H match is scheduled for GW{gameweek} yet."
  },
  "fixtures.kickoffUnknown": { vi: "Chưa có giờ thi đấu", en: "Kick-off time to be confirmed" },

  "match.title": { vi: "Chi tiết trận H2H", en: "H2H match detail" },
  "match.back": { vi: "Quay lại lịch thi đấu", en: "Back to fixtures" },
  "match.captain": { vi: "Captain", en: "Captain" },
  "match.playersLeft": { vi: "Cầu thủ còn lại", en: "Players remaining" },
  "match.breakdown": { vi: "Chi tiết điểm", en: "Score breakdown" },
  "match.timeline": { vi: "Diễn biến", en: "Timeline" },
  "match.resultStatus": { vi: "Trạng thái kết quả", en: "Result status" },
  "match.squadPoints": { vi: "Điểm đội hình", en: "Squad points" },
  "match.transferCost": { vi: "Điểm trừ chuyển nhượng", en: "Transfer cost" },
  "match.adminAdjustment": { vi: "Điều chỉnh admin", en: "Admin adjustment" },
  "match.netPoints": { vi: "Điểm net", en: "Net points" },
  "match.walkoverNote": { vi: "Kết quả walkover: {reason}", en: "Walkover result: {reason}" },
  "match.settledNote": { vi: "Kết quả đã được chốt.", en: "This result is final." },
  "match.provisionalNote": {
    vi: "Kết quả có thể thay đổi cho tới khi gameweek được finalize.",
    en: "The result can change until the Gameweek is finalized."
  },
  "match.notFound": { vi: "Không tìm thấy trận H2H #{id}.", en: "H2H match #{id} was not found." },

  "cup.title": { vi: "VMF Cup", en: "VMF Cup" },
  "cup.description": {
    vi: "{window}. Mọi GW vi phạm đóng góp 0 điểm vào bảng xét suất Cup.",
    en: "{window}. Every Gameweek with a confirmed violation contributes 0 to the Cup qualification table."
  },
  "cup.eyebrow": { vi: "Knock-out", en: "Knock-out" },
  "cup.season1": { vi: "Season 1", en: "Season 1" },
  "cup.season2": { vi: "Season 2", en: "Season 2" },
  "cup.netNote": { vi: "Cập nhật theo điểm net", en: "Updated from net points" },
  "cup.window1": { vi: "Xét điểm hợp lệ từ GW1–GW14", en: "Qualification window GW1–GW14" },
  "cup.window2": { vi: "Xét điểm hợp lệ từ GW20–GW33", en: "Qualification window GW20–GW33" },
  "cup.honours": { vi: "Vị trí danh dự", en: "Honours" },
  "cup.thirdPlace": { vi: "Trận tranh hạng ba", en: "Third-place match" },
  "cup.thirdPlaceBody": {
    vi: "Cup có trận tranh hạng ba riêng ở vòng đấu cuối.",
    en: "The Cup does play a separate third-place match in its final round."
  },

  "highlights.eyebrow": { vi: "Season stories", en: "Season stories" },
  "highlights.description": {
    vi: "Những đội hình xuất sắc, cuộc lội ngược dòng và cột mốc đáng nhớ của cộng đồng VMF.",
    en: "Standout squads, comebacks and milestones from the VMF community."
  },
  "highlights.emptyTitle": { vi: "Chưa có highlights", en: "No highlights yet" },
  "highlights.emptyBody": {
    vi: "Backend hiện chưa có endpoint highlights; trang sẽ tự hiển thị khi nguồn dữ liệu được bổ sung.",
    en: "The backend has no highlights endpoint yet; this page fills in once the source exists."
  },

  "managers.eyebrow": { vi: "Cộng đồng", en: "Community" },
  "managers.heading": {
    vi: "{count} managers. Một mùa giải.",
    en: "{count} managers. One season."
  },
  "managers.description": {
    vi: "Hồ sơ thi đấu công khai chỉ hiển thị dữ liệu giải; thông tin cá nhân được giới hạn cho ban tổ chức.",
    en: "Public profiles show competition data only; personal contact details stay with the organisers."
  },
  "managers.division": { vi: "Division {division}", en: "{division} division" },
  "managers.totalPoints": { vi: "Tổng điểm", en: "Total points" },
  "managers.lastGameweek": { vi: "GW gần nhất", en: "Latest GW" },
  "managers.violations": { vi: "Violation", en: "Violations" },
  "managers.status.active": { vi: "Active", en: "Active" },
  "managers.status.locked": { vi: "Locked", en: "Locked" },
  "managers.status.suspended": { vi: "Suspended", en: "Suspended" },
  "managers.status.pending_review": { vi: "Pending", en: "Pending" },
  "managers.status.removed": { vi: "Removed", en: "Removed" },
  "managers.status.deleted": { vi: "Deleted", en: "Deleted" },

  "admin.title": { vi: "Điều hành", en: "Administration" },
  "admin.eyebrow": { vi: "Khu vực điều hành", en: "Admin area" },
  "admin.heading": { vi: "Trung tâm vận hành", en: "Operations centre" },
  "admin.description": {
    vi: "Theo dõi đồng bộ, trạng thái tính điểm và các ngoại lệ cần xử lý.",
    en: "Monitor synchronization, scoring state and the exceptions waiting for a decision."
  },
  "admin.syncState": { vi: "Tình trạng đồng bộ", en: "Synchronization state" },
  "admin.syncHealthy": {
    vi: "Hệ thống hoạt động bình thường",
    en: "The system is operating normally"
  },
  "admin.syncUnknown": { vi: "Chưa có telemetry worker", en: "No worker telemetry yet" },
  "admin.syncDetail": {
    vi: "Thành công lúc {time} · Độ trễ {latency} giây",
    en: "Last success {time} · latency {latency}s"
  },
  "admin.syncMissing": {
    vi: "Backend hiện chưa cung cấp endpoint trạng thái đồng bộ.",
    en: "The backend does not expose a synchronization status endpoint yet."
  },
  "admin.healthy": { vi: "Healthy", en: "Healthy" },
  "admin.unknown": { vi: "Unknown", en: "Unknown" },
  "admin.managersConfirmed": { vi: "Đã xác nhận tham gia", en: "Confirmed entries" },
  "admin.provisionalScores": { vi: "Điểm tạm tính", en: "Provisional scores" },
  "admin.noEndpoint": { vi: "Chưa có endpoint", en: "No endpoint yet" },
  "admin.awaitingFinalize": { vi: "Chờ finalize", en: "Awaiting finalization" },
  "admin.pendingViolations": { vi: "Violation chờ xử lý", en: "Violations pending" },
  "admin.needsDecision": { vi: "Cần quyết định admin", en: "Needs an admin decision" },
  "admin.lockedTeams": { vi: "Team bị khóa", en: "Locked teams" },
  "admin.lockedTeamsNote": {
    vi: "Dùng điểm trung bình division",
    en: "Using the division average"
  },
  "admin.byGameweek": { vi: "Theo gameweek", en: "By Gameweek" },
  "admin.divisionAverage": { vi: "Điểm trung bình division", en: "Division average score" },
  "admin.eligibleManagers": { vi: "{count} managers hợp lệ", en: "{count} eligible managers" },
  "admin.noAverageTitle": { vi: "Chưa có dữ liệu trung bình", en: "No average data yet" },
  "admin.noAverageBody": {
    vi: "Backend chưa cung cấp endpoint division average.",
    en: "The backend does not expose a division-average endpoint yet."
  },
  "admin.averageNote": {
    vi: "Team locked/removed và điểm replacement không được đưa vào mẫu tính.",
    en: "Locked or removed teams and replacement scores are excluded from the sample."
  },
  "admin.workerLog": { vi: "Worker log", en: "Worker log" },
  "admin.recentJobs": { vi: "Tác vụ gần đây", en: "Recent jobs" },
  "admin.syncCadence": { vi: "Đồng bộ 5 phút", en: "Sync every 5 minutes" },
  "admin.noJobTitle": { vi: "Chưa có worker log", en: "No worker log yet" },
  "admin.noJobBody": {
    vi: "Backend chưa cung cấp endpoint lịch sử tác vụ.",
    en: "The backend does not expose a job-history endpoint yet."
  },

  "violations.title": { vi: "Quản lý vi phạm", en: "Violation management" },
  "violations.heading": { vi: "Violation review", en: "Violation review" },
  "violations.description": {
    vi: "Xác minh vi phạm, phạm vi ảnh hưởng và lịch sử quyết định theo từng gameweek.",
    en: "Verify each violation, its scope of impact and the decision history per Gameweek."
  },
  "violations.pending": { vi: "Chờ xử lý", en: "Pending" },
  "violations.confirmed": { vi: "Đã xác nhận", en: "Confirmed" },
  "violations.waived": { vi: "Được miễn", en: "Waived" },
  "violations.viewAudit": { vi: "Xem audit log", en: "View audit log" },
  "violations.auditUnavailable": {
    vi: "Audit-log detail chưa có endpoint cho giao diện.",
    en: "The audit-log detail has no endpoint for the UI yet."
  },
  "violations.requestChipReview": { vi: "Yêu cầu kiểm tra chip", en: "Request chip review" },
  "violations.confirmViolation": { vi: "Xác nhận vi phạm", en: "Confirm violation" },
  "violations.approveException": { vi: "Duyệt ngoại lệ", en: "Approve exception" },
  "violations.rejectException": { vi: "Bác ngoại lệ", en: "Reject exception" },
  "violations.mockNotice": {
    vi: "Dữ liệu minh hoạ · không thể review",
    en: "Illustrative data · review disabled"
  },
  "violations.notePlaceholder": { vi: "Ghi chú bắt buộc", en: "Reason (required)" },
  "violations.noteAria": {
    vi: "Ghi chú review violation {id}",
    en: "Review note for violation {id}"
  },
  "violations.noneConfirmed": { vi: "Không xác nhận", en: "None confirmed" },
  "violations.occurrences": {
    vi: "{count} lần trong bản ghi",
    en: "{count} recorded occurrences"
  },
  "violations.noTransferCost": {
    vi: "Backend chưa trả transfer cost",
    en: "The backend did not return a transfer cost"
  },
  "violations.transferCost": {
    vi: "Transfer cost ghi nhận: −{cost}",
    en: "Recorded transfer cost: −{cost}"
  },
  "violations.notReviewed": { vi: "Chưa review", en: "Not reviewed" },
  "violations.impact.threshold": {
    vi: "Áp dụng theo ngưỡng vi phạm tích lũy",
    en: "Applied at the cumulative violation threshold"
  },
  "violations.impact.cupZero": {
    vi: "Điểm GW không tính xét suất Cup",
    en: "Gameweek excluded from Cup qualification"
  },
  "violations.impact.waived": { vi: "Không cộng violation", en: "No violation counted" },
  "violations.impact.h2hDeduction": {
    vi: "Trừ 6 điểm bảng H2H",
    en: "6 points deducted from the H2H table"
  },
  "violations.impact.level2Warning": { vi: "Cảnh cáo cấp 2", en: "Level 2 sanction" },
  "violations.impact.keepTransferHit": {
    vi: "Giữ nguyên transfer hit FPL",
    en: "The official FPL transfer hit still stands"
  },

  "error.title": { vi: "Không thể tải nội dung", en: "This content could not load" },
  "error.body": {
    vi: "Dữ liệu đang tạm thời gián đoạn. Bạn có thể thử tải lại mà không làm mất trạng thái.",
    en: "The data source is temporarily unavailable. You can retry without losing your place."
  },
  "loading.label": { vi: "Đang tải dữ liệu…", en: "Loading data…" },
  "notFound.title": { vi: "Không tìm thấy trang", en: "Page not found" },
  "notFound.body": {
    vi: "Đường dẫn này không tồn tại hoặc nội dung đã được di chuyển.",
    en: "This address does not exist, or the content has moved."
  },
  "notFound.action": { vi: "Về tổng quan", en: "Back to overview" },

  "api.missingUrl": {
    vi: "Thiếu VMF_API_URL (hoặc NEXT_PUBLIC_API_URL). Không thể tải dữ liệu thật.",
    en: "VMF_API_URL (or NEXT_PUBLIC_API_URL) is missing, so live data cannot be loaded."
  },
  "api.mockWriteBlocked": {
    vi: "Không thể ghi quyết định khi đang dùng dữ liệu minh hoạ.",
    en: "Decisions cannot be recorded while illustrative data is enabled."
  }
} as const;

export type MessageKey = keyof typeof messages;

type Variables = Record<string, string | number>;

export function translate(locale: Locale, key: MessageKey, variables?: Variables): string {
  const entry = messages[key];
  const template = entry[locale] ?? entry[DEFAULT_LOCALE];
  if (!variables) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in variables ? String(variables[name]) : match
  );
}

export type Translator = (key: MessageKey, variables?: Variables) => string;

export function createTranslator(locale: Locale): Translator {
  return (key, variables) => translate(locale, key, variables);
}
