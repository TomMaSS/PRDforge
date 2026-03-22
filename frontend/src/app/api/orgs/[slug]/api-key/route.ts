import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { requireOrgAdmin } from "@/lib/require-org-admin";
import crypto from "crypto";

const ENCRYPTION_SECRET = process.env.API_KEY_ENCRYPTION_SECRET || "dev-encryption-key-change-in-prod";

function encrypt(text: string): string {
  const key = crypto.scryptSync(ENCRYPTION_SECRET, "salt", 32);
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipheriv("aes-256-cbc", key, iv);
  let encrypted = cipher.update(text, "utf8", "hex");
  encrypted += cipher.final("hex");
  return iv.toString("hex") + ":" + encrypted;
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;

  const check = await requireOrgAdmin(slug);
  if ("error" in check) return check.error;

  const body = await req.json();
  const apiKey = body.api_key?.trim();

  if (!apiKey) {
    return NextResponse.json({ error: "api_key required" }, { status: 400 });
  }

  if (!apiKey.startsWith("sk-ant-")) {
    return NextResponse.json(
      { error: "Invalid API key format (expected sk-ant-...)" },
      { status: 400 }
    );
  }

  const encrypted = encrypt(apiKey);

  try {
    await prisma.$executeRawUnsafe(
      `UPDATE organization SET anthropic_api_key_encrypted = $1, "updatedAt" = now() WHERE slug = $2`,
      encrypted,
      slug
    );

    return NextResponse.json({
      ok: true,
      key_hint: `...${apiKey.slice(-4)}`,
    });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Failed to save key" },
      { status: 500 }
    );
  }
}
