## Database

This folder contains the database schema and seed data for the NMTC backend.

### Files
- `schema.sql`: Logical schema for tables, constraints, and relationships (context-first; not ordered for execution).
- `seed_data.sql.sql`: Example seed data to help bootstrap a development environment.
- `relationships.md`: Human-readable summary of key foreign-key relationships.

### Usage notes
- The `schema.sql` file may not be in dependency-safe order. When applying to a new database, you may need to:
  - Create referenced schemas first (e.g., `auth` on Supabase).
  - Disable/skip FKs temporarily or reorder statements.
- Supabase environments provide `auth.users` and other extensions; ensure your target matches these expectations.

### Applying schema on Supabase
1. In the Supabase Dashboard, go to SQL Editor.
2. Paste the relevant sections of `schema.sql` in an order that respects dependencies, or split into multiple runs.
3. Verify constraints and indexes.
4. Load `seed_data.sql.sql` as needed for local testing.

### Conventions
- All application tables are under the `public` schema unless noted.
- UUID primary keys use `gen_random_uuid()`.
- Timestamps default to `now()`.

### See also
- `relationships.md` for a compact overview of entity relationships.

