import { type NextRequest, NextResponse } from "next/server";

function constantTimeEqual(left: string, right: string): boolean {
  const maximumLength = Math.max(left.length, right.length);
  let difference = left.length ^ right.length;
  for (let index = 0; index < maximumLength; index += 1) {
    difference |= (left.charCodeAt(index) || 0) ^ (right.charCodeAt(index) || 0);
  }
  return difference === 0;
}

export function hasValidAdminCredentials(
  authorization: string | null,
  expectedUsername: string,
  expectedPassword: string
): boolean {
  if (!authorization?.startsWith("Basic ")) return false;
  try {
    const decoded = atob(authorization.slice("Basic ".length));
    return constantTimeEqual(decoded, `${expectedUsername}:${expectedPassword}`);
  } catch {
    return false;
  }
}

export function proxy(request: NextRequest): NextResponse {
  const username = process.env.VMF_ADMIN_UI_USER?.trim();
  const password = process.env.VMF_ADMIN_UI_PASSWORD;

  // Length is the operator's decision, not this file's. Note that guessing it
  // grants the whole admin surface: finalizing a Gameweek, confirming a
  // violation and the removals that follow from it.
  if (!username || !password) {
    return new NextResponse("Admin UI is not configured.", {
      status: 503,
      headers: { "Cache-Control": "no-store" }
    });
  }

  if (!hasValidAdminCredentials(request.headers.get("authorization"), username, password)) {
    // Only a navigation may raise the browser's sign-in dialog. A background
    // request that answered with WWW-Authenticate would pop it over whatever
    // public page the visitor is actually reading.
    const isBackgroundRequest =
      request.headers.get("next-router-prefetch") !== null ||
      request.headers.get("rsc") !== null ||
      request.headers.get("sec-fetch-mode") === "cors";

    return new NextResponse("Authentication required.", {
      status: 401,
      headers: {
        "Cache-Control": "no-store",
        ...(isBackgroundRequest
          ? {}
          : { "WWW-Authenticate": 'Basic realm="VMF Admin", charset="UTF-8"' })
      }
    });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*"]
};
