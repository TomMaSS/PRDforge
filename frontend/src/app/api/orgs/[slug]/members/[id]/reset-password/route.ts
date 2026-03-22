import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { requireOrgAdmin } from "@/lib/require-org-admin";
import crypto from "crypto";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string; id: string }> }
) {
  const { slug, id: userId } = await params;

  const check = await requireOrgAdmin(slug);
  if ("error" in check) return check.error;

  // Generate a secure reset token
  const token = crypto.randomBytes(32).toString("hex");
  const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24h

  try {
    await prisma.$executeRawUnsafe(
      `INSERT INTO password_reset_tokens (user_id, token, expires_at)
       VALUES ($1::uuid, $2, $3)`,
      userId,
      token,
      expiresAt
    );

    // Return the reset URL — admin shares it manually (no email)
    const resetUrl = `/reset?token=${token}`;

    return NextResponse.json({
      reset_url: resetUrl,
      expires_at: expiresAt.toISOString(),
    });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Failed to create reset token" },
      { status: 500 }
    );
  }
}
