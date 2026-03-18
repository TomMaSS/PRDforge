import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/db";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { name, email, password } = body;

  if (!name || !email || !password) {
    return NextResponse.json(
      { error: "name, email, and password are required" },
      { status: 400 }
    );
  }

  // Race-safe bootstrap check via INSERT ON CONFLICT
  try {
    const result = await prisma.$queryRawUnsafe<{ id: string }[]>(
      `INSERT INTO prdforge_bootstrap (setup_type, completed)
       VALUES ('first_user', true)
       ON CONFLICT (setup_type) DO NOTHING
       RETURNING id`
    );

    if (!result || result.length === 0) {
      return NextResponse.json(
        { error: "Setup already completed" },
        { status: 409 }
      );
    }

    const bootstrapId = result[0].id;

    // Create first user via Better Auth API
    try {
      const ctx = await auth.api.signUpEmail({
        body: { name, email, password },
      });

      // Create default organization
      // Note: org creation via Better Auth API requires auth context
      // For bootstrap, we create directly
      const orgId = crypto.randomUUID();
      await prisma.$executeRawUnsafe(
        `INSERT INTO organization (id, name, slug, "createdAt", "updatedAt")
         VALUES ($1, 'Default', 'default', now(), now())`,
        orgId
      );

      await prisma.$executeRawUnsafe(
        `INSERT INTO member (id, "organizationId", "userId", role, "createdAt")
         VALUES ($1, $2, $3, 'owner', now())`,
        crypto.randomUUID(),
        orgId,
        ctx.user.id
      );

      return NextResponse.json({
        success: true,
        user: { id: ctx.user.id, email: ctx.user.email, name: ctx.user.name },
      });
    } catch (err) {
      // Compensation: remove bootstrap flag on failure
      await prisma.$executeRawUnsafe(
        `DELETE FROM prdforge_bootstrap WHERE id = $1`,
        bootstrapId
      );
      throw err;
    }
  } catch (err) {
    if (err instanceof Error && err.message === "Setup already completed") {
      throw err;
    }
    console.error("Setup failed:", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Setup failed" },
      { status: 500 }
    );
  }
}
