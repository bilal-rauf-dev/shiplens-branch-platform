from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("finance", "0003_weekly_reports")]
    operations = [
        migrations.RunSQL(
            sql="""
            CREATE FUNCTION guard_locked_report() RETURNS trigger AS $$
            BEGIN
                IF OLD.status = 'LOCKED' THEN
                    RAISE EXCEPTION 'Weekly report is locked';
                END IF;
                IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            CREATE TRIGGER weekly_reports_lock_guard
            BEFORE UPDATE OR DELETE ON weekly_reports
            FOR EACH ROW EXECUTE FUNCTION guard_locked_report();

            CREATE FUNCTION guard_locked_report_line() RETURNS trigger AS $$
            DECLARE parent_status varchar(12);
            BEGIN
                IF TG_OP <> 'INSERT' THEN
                    SELECT status INTO parent_status FROM weekly_reports
                    WHERE id = OLD.report_id FOR SHARE;
                    IF parent_status = 'LOCKED' THEN
                        RAISE EXCEPTION 'Weekly report line is locked';
                    END IF;
                END IF;
                IF TG_OP <> 'DELETE' THEN
                    SELECT status INTO parent_status FROM weekly_reports
                    WHERE id = NEW.report_id FOR SHARE;
                    IF parent_status = 'LOCKED' THEN
                        RAISE EXCEPTION 'Weekly report line is locked';
                    END IF;
                END IF;
                IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            CREATE TRIGGER weekly_report_lines_lock_guard
            BEFORE INSERT OR UPDATE OR DELETE ON weekly_report_lines
            FOR EACH ROW EXECUTE FUNCTION guard_locked_report_line();
        """,
            reverse_sql="""
            DROP TRIGGER weekly_report_lines_lock_guard ON weekly_report_lines;
            DROP FUNCTION guard_locked_report_line();
            DROP TRIGGER weekly_reports_lock_guard ON weekly_reports;
            DROP FUNCTION guard_locked_report();
        """,
        )
    ]
