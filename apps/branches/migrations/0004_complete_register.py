import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("branches", "0003_seed_cities"),
        ("core", "0002_idsequence"),
    ]
    # branches is empty at this point in every environment: no branch could be
    # created before P3.
    operations = [
        migrations.AlterField(
            model_name="branch",
            name="city",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="branches",
                to="branches.city",
                verbose_name="city",
            ),
        ),
        migrations.AlterField(
            model_name="branch",
            name="name_ur",
            field=models.CharField(max_length=100, verbose_name="Urdu name"),
        ),
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION reject_branch_code_change() RETURNS trigger AS $$
                BEGIN
                    IF NEW.code IS DISTINCT FROM OLD.code THEN
                        RAISE EXCEPTION 'Branch codes are immutable';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                CREATE TRIGGER branches_code_immutable BEFORE UPDATE ON branches
                FOR EACH ROW EXECUTE FUNCTION reject_branch_code_change();
            """,
            reverse_sql="""
                DROP TRIGGER branches_code_immutable ON branches;
                DROP FUNCTION reject_branch_code_change();
            """,
        ),
    ]
