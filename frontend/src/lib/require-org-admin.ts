import { auth } from "@/lib/auth";
import { prisma } from "@/lib/db";
import { headers } from "next/headers";
import { NextResponse } from "next/server";

export async function requireOrgAdmin(orgSlug: string) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return { error: NextResponse.json({ error: "unauthorized" }, { status: 401 }) };
  }

  const rows = await prisma.$queryRaw<{ role: string }[]>`
    SELECT role FROM member
    WHERE "userId" = ${session.user.id}
      AND "organizationId" = (SELECT id FROM organization WHERE slug = ${orgSlug})
  `;

  if (!rows.length || !["owner", "admin"].includes(rows[0].role)) {
    return { error: NextResponse.json({ error: "forbidden" }, { status: 403 }) };
  }

  return { session, role: rows[0].role };
}
