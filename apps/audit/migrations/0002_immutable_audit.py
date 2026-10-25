from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION reject_audit_mutation() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                    RAISE EXCEPTION 'audit_log is append-only';
                END;
                $$;
                CREATE TRIGGER audit_guard_change
                BEFORE UPDATE OR DELETE ON audit_log
                FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
                CREATE TRIGGER audit_guard_truncate
                BEFORE TRUNCATE ON audit_log
                FOR EACH STATEMENT EXECUTE FUNCTION reject_audit_mutation();
            """,
            reverse_sql="""
                DROP TRIGGER audit_guard_truncate ON audit_log;
                DROP TRIGGER audit_guard_change ON audit_log;
                DROP FUNCTION reject_audit_mutation();
            """,
        )
    ]
