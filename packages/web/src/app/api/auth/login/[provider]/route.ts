import { NextRequest, NextResponse } from "next/server";
import { getApiBaseUrl } from "@/lib/api-base";

const ALLOWED_PROVIDERS = new Set(["github", "google"]);

export async function GET(
  request: NextRequest,
  context: { params: { provider: string } }
) {
  const provider = context.params.provider;

  if (!ALLOWED_PROVIDERS.has(provider)) {
    return NextResponse.json(
      { detail: "Unsupported OAuth provider" },
      { status: 400 }
    );
  }

  const host =
    request.headers.get("x-forwarded-host") ||
    request.headers.get("host") ||
    request.nextUrl.host;
  const protocol =
    request.headers.get("x-forwarded-proto") || request.nextUrl.protocol;
  const apiUrl = getApiBaseUrl({
    hostname: host ?? undefined,
    protocol: protocol ?? undefined,
  });

  try {
    const response = await fetch(
      `${apiUrl}/api/v1/auth/login/${provider}`,
      { method: "GET", cache: "no-store" }
    );

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      return NextResponse.json(
        { detail: payload.detail || "Failed to initiate login" },
        { status: response.status }
      );
    }

    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    console.error("OAuth login proxy error:", error);
    return NextResponse.json(
      { detail: "Authentication service unavailable" },
      { status: 503 }
    );
  }
}
