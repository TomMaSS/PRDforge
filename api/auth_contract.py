"""Contract test: verify Better Auth table names and columns exist.

Better Auth uses Prisma model names which may differ from DB table names.
This contract verifies the ACTUAL tables created by `prisma migrate deploy`.
Pin: better-auth@1.4.7
"""

# Expected tables and their required columns (from Prisma schema @@map)
EXPECTED_TABLES = {
    "user": ["id", "name", "email", "emailVerified", "createdAt", "updatedAt"],
    "session": ["id", "token", "userId", "expiresAt", "createdAt"],
    "account": ["id", "accountId", "providerId", "userId", "createdAt"],
    "verification": ["id", "identifier", "value", "expiresAt"],
    "organization": ["id", "name", "slug", "createdAt", "updatedAt"],
    "member": ["id", "organizationId", "userId", "role", "createdAt"],
    "invitation": ["id", "organizationId", "email", "role", "status", "expiresAt"],
}


async def verify_auth_contract(pool) -> list[str]:
    """Verify Better Auth tables exist with expected columns.

    Returns list of errors (empty = all good).
    """
    errors = []

    for table, expected_cols in EXPECTED_TABLES.items():
        # Check table exists
        exists = await pool.fetchval(
            "SELECT to_regclass($1)", table
        )
        if not exists:
            errors.append(f"Table '{table}' does not exist")
            continue

        # Check columns
        actual_cols = await pool.fetch(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = $1 AND table_schema = 'public'
            """,
            table,
        )
        actual_col_names = {r["column_name"] for r in actual_cols}

        for col in expected_cols:
            if col not in actual_col_names:
                errors.append(f"Table '{table}' missing column '{col}'")

    return errors
