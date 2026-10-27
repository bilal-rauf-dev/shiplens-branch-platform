from django.db import migrations


def seed_roles(apps, schema_editor):
    role_model = apps.get_model("volunteers", "VolunteerRole")
    roles = (
        ("VOLUNTEER", "Volunteer", "رضاکار"),
        ("TEAM_LEAD", "Team Lead", "ٹیم سربراہ"),
        ("COORDINATOR", "Coordinator", "رابطہ کار"),
        ("TREASURER", "Treasurer", "خزانچی"),
    )
    for order, (code, name_en, name_ur) in enumerate(roles):
        role_model.objects.using(schema_editor.connection.alias).get_or_create(
            code=code,
            defaults={"name_en": name_en, "name_ur": name_ur, "sort_order": order},
        )


class Migration(migrations.Migration):
    dependencies = [("volunteers", "0001_initial")]
    operations = [migrations.RunPython(seed_roles, migrations.RunPython.noop)]
