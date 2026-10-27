from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("finance", "0001_initial")]
    operations = [
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION guard_sent_collection() RETURNS trigger AS $$
                BEGIN
                    IF OLD.transfer_id IS NOT NULL AND
                        (NEW.amount, NEW.collection_date, NEW.method, NEW.branch_id)
                        IS DISTINCT FROM
                        (OLD.amount, OLD.collection_date, OLD.method, OLD.branch_id)
                    THEN RAISE EXCEPTION 'Sent collections are immutable';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                CREATE TRIGGER collection_sent_guard BEFORE UPDATE ON collections
                FOR EACH ROW EXECUTE FUNCTION guard_sent_collection();
                CREATE FUNCTION guard_transfer() RETURNS trigger AS $$
                BEGIN
                    RAISE EXCEPTION 'Transfers are immutable';
                END;
                $$ LANGUAGE plpgsql;
                CREATE TRIGGER transfer_immutable BEFORE UPDATE OR DELETE ON transfers
                FOR EACH ROW EXECUTE FUNCTION guard_transfer();
            """,
            reverse_sql="""
                DROP TRIGGER transfer_immutable ON transfers;
                DROP FUNCTION guard_transfer();
                DROP TRIGGER collection_sent_guard ON collections;
                DROP FUNCTION guard_sent_collection();
            """,
        )
    ]
