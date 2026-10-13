-- Utente applicativo a privilegi minimi. Esegui come amministratore sul database dell'app:
--   psql -d aidb -v app_password="'$(openssl rand -hex 24)'" -f scripts/ops_create_app_user.sql
-- La password va nei secrets di Coolify (DATABASE_URL), mai nel repository.
-- Le migrazioni Alembic richiedono DDL: usale con un utente "migrator" separato (o l'amministratore) al deploy.
\set ON_ERROR_STOP on

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aidb_app') THEN
    CREATE ROLE aidb_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END
$$;
ALTER ROLE aidb_app PASSWORD :app_password;

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE :"DBNAME" TO aidb_app;
GRANT USAGE ON SCHEMA public TO aidb_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO aidb_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO aidb_app;

-- Tabelle future create dall'amministratore/migratore
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO aidb_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO aidb_app;
