import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { auth } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { token, password } = body;

  if (!token || !password) {
    return NextResponse.json(
      { error: "token and password are required" },
      { status: 400 }
    );
  }

  if (password.length < 8) {
    return NextResponse.json(
      { error: "Password must be at least 8 characters" },
      { status: 400 }
    );
  }

  try {
    // Find valid, unused token
    const rows = await prisma.$queryRawUnsafe<
      { id: string; user_id: string; expires_at: Date }[]
    >(
      `SELECT id, user_id, expires_at FROM password_reset_tokens
       WHERE token = $1 AND NOT used AND expires_at > now()
       LIMIT 1`,
      token
    );

    if (!rows || rows.length === 0) {
      return NextResponse.json(
        { error: "Invalid or expired reset token" },
        { status: 400 }
      );
    }

    const resetToken = rows[0];

    // Mark token as used
    await prisma.$executeRawUnsafe(
      `UPDATE password_reset_tokens SET used = true WHERE id = $1::uuid`,
      resetToken.id
    );

    // Update password via Better Auth API
    // Better Auth doesn't expose a direct password update API publicly,
    // so we update the account table directly
    const bcrypt = await import("bcryptjs");
    const hashedPassword = await bcrypt.hash(password, 10);

    await prisma.$executeRawUnsafe(
      `UPDATE account SET password = $1, "updatedAt" = now()
       WHERE "userId" = $2 AND "providerId" = 'credential'`,
      hashedPassword,
      resetToken.user_id
    );

    // Revoke all sessions for this user
    await prisma.$executeRawUnsafe(
      `DELETE FROM session WHERE "userId" = $1`,
      resetToken.user_id
    );

    return NextResponse.json({ success: true });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Password reset failed" },
      { status: 500 }
    );
  }
}
