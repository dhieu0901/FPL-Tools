import type { Metadata } from "next";
import { H2HTable } from "@/components/h2h-table";
import { Callout, DataBadge, PageHeader, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";

export const metadata: Metadata = { title: "H2H League" };

export default async function H2HPage() {
  const result = await vmfApi.h2hStandings();
  return (
    <>
      <PageHeader
        eyebrow="Head to Head"
        title="Bảng đấu H2H"
        description="Mỗi gameweek là một cuộc đối đầu. Thắng 3 điểm, hoà 1 điểm; vi phạm được khấu trừ riêng theo luật giải."
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <div className="toolbar-row">
        <SegmentedLinks
          items={[
            { href: "/h2h", label: "Bảng xếp hạng", active: true },
            { href: "/h2h/fixtures", label: "Lịch & kết quả" }
          ]}
        />
        <span className="toolbar-note">Vòng bảng · GW1–GW35</span>
      </div>
      <H2HTable entries={result.data} />
      <div className="h2h-summary-grid">
        <article>
          <span>Suất bán kết</span>
          <strong>Top 4</strong>
          <small>Sau GW35</small>
        </article>
        <article>
          <span>Bán kết</span>
          <strong>GW36–37</strong>
          <small>Hai lượt trận</small>
        </article>
        <article>
          <span>Chung kết</span>
          <strong>GW38</strong>
          <small>Không tranh hạng ba</small>
        </article>
      </div>
      <Callout title="Kết quả đã chốt là bất biến" icon="shield" tone="lime">
        <p>
          Chỉ admin có thể mở lại gameweek đã finalize; mọi thay đổi bắt buộc có lý do và nhật ký
          kiểm toán.
        </p>
      </Callout>
    </>
  );
}
