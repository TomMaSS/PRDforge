import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;
  const body = await req.json();
  const { name, email, password, role } = body;

  if (!name || !email || !password) {
    return NextResponse.json(
      { error: "name, email, and password are required" },
      { status: 400 }
    );
  }

  try {
    // Create user via Better Auth API (Next.js only — Python never writes auth)
    const ctx = await auth.api.signUpEmail({
      body: { name, email, password },
    });

    return NextResponse.json({
      user: { id: ctx.user.id, email: ctx.user.email, name: ctx.user.name },
      org: slug,
      role: role || "member",
    });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Failed to create user" },
      { status: 500 }
    );
  }
}
