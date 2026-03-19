-- Better Auth tables (matches Prisma schema with @@map names)
-- These are normally created by `prisma db push` but we create via SQL
-- for Docker init compatibility. All statements idempotent.

CREATE TABLE IF NOT EXISTS "user" (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    "emailVerified" BOOLEAN NOT NULL DEFAULT false,
    image           TEXT,
    "createdAt"     TIMESTAMPTZ NOT NULL DEFAULT now(),
    "updatedAt"     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS session (
    id              TEXT PRIMARY KEY,
    "expiresAt"     TIMESTAMPTZ NOT NULL,
    token           TEXT NOT NULL UNIQUE,
    "createdAt"     TIMESTAMPTZ NOT NULL DEFAULT now(),
    "updatedAt"     TIMESTAMPTZ NOT NULL DEFAULT now(),
    "ipAddress"     TEXT,
    "userAgent"     TEXT,
    "userId"        TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS account (
    id                      TEXT PRIMARY KEY,
    "accountId"             TEXT NOT NULL,
    "providerId"            TEXT NOT NULL,
    "userId"                TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    "accessToken"           TEXT,
    "refreshToken"          TEXT,
    "idToken"               TEXT,
    "accessTokenExpiresAt"  TIMESTAMPTZ,
    "refreshTokenExpiresAt" TIMESTAMPTZ,
    scope                   TEXT,
    password                TEXT,
    "createdAt"             TIMESTAMPTZ NOT NULL DEFAULT now(),
    "updatedAt"             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS verification (
    id              TEXT PRIMARY KEY,
    identifier      TEXT NOT NULL,
    value           TEXT NOT NULL,
    "expiresAt"     TIMESTAMPTZ NOT NULL,
    "createdAt"     TIMESTAMPTZ DEFAULT now(),
    "updatedAt"     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS organization (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE,
    logo            TEXT,
    "createdAt"     TIMESTAMPTZ NOT NULL DEFAULT now(),
    "updatedAt"     TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata        TEXT,
    anthropic_api_key_encrypted TEXT
);

CREATE TABLE IF NOT EXISTS member (
    id                  TEXT PRIMARY KEY,
    "organizationId"    TEXT NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    "userId"            TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    role                TEXT NOT NULL,
    "createdAt"         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS invitation (
    id                  TEXT PRIMARY KEY,
    "organizationId"    TEXT NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    email               TEXT NOT NULL,
    role                TEXT,
    status              TEXT NOT NULL,
    "expiresAt"         TIMESTAMPTZ NOT NULL,
    "inviterId"         TEXT NOT NULL
);
