import { NextResponse } from "next/server";
import { ApiRequestError, vmfApi } from "@/lib/api";

/**
 * One match, for the squad panel a reader opens under a fixture.
 *
 * The fixture list would be far heavier if it carried both squads for all
 * twenty-three ties of a Gameweek, and almost none of them get opened. This
 * route lets the card fetch its own detail on the first expand, and keeps the
 * API URL and admin key on the server where they belong.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  const { id } = await params;
  if (!/^\d+$/.test(id)) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  try {
    const { data, updatedAt } = await vmfApi.h2hMatch(id);
    return NextResponse.json(
      { data, updatedAt },
      // Live scores move; a short cache still absorbs a burst of readers
      // opening the same tie at once.
      { headers: { "Cache-Control": "private, max-age=20" } }
    );
  } catch (error) {
    const status = error instanceof ApiRequestError ? (error.status ?? 502) : 502;
    return NextResponse.json({ error: "unavailable" }, { status });
  }
}
