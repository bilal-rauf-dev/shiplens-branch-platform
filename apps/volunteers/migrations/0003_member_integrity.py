from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("volunteers", "0002_seed_volunteer_roles")]
    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE members ADD CONSTRAINT members_team_branch_fk
                FOREIGN KEY (team_id, branch_id) REFERENCES teams (id, branch_id);

                CREATE FUNCTION reject_member_id_change() RETURNS trigger AS $$
                BEGIN
                    IF NEW.member_id IS DISTINCT FROM OLD.member_id THEN
                        RAISE EXCEPTION 'Member IDs are immutable';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                CREATE TRIGGER members_id_immutable BEFORE UPDATE ON members
                FOR EACH ROW EXECUTE FUNCTION reject_member_id_change();
            """,
            reverse_sql="""
                DROP TRIGGER members_id_immutable ON members;
                DROP FUNCTION reject_member_id_change();
                ALTER TABLE members DROP CONSTRAINT members_team_branch_fk;
            """,
        )
    ]
