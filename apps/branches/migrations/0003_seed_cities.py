from django.db import migrations

CITIES = (
    ("KHI", "Karachi", "کراچی"),
    ("LHE", "Lahore", "لاہور"),
    ("ISB", "Islamabad", "اسلام آباد"),
    ("RWP", "Rawalpindi", "راولپنڈی"),
    ("PEW", "Peshawar", "پشاور"),
    ("QTA", "Quetta", "کوئٹہ"),
    ("MUX", "Multan", "ملتان"),
    ("FSD", "Faisalabad", "فیصل آباد"),
    ("HYD", "Hyderabad", "حیدرآباد"),
    ("SKT", "Sialkot", "سیالکوٹ"),
)


def seed_cities(apps, schema_editor):
    city_model = apps.get_model("branches", "City")
    for code, name_en, name_ur in CITIES:
        city_model.objects.using(schema_editor.connection.alias).get_or_create(
            code=code, defaults={"name_en": name_en, "name_ur": name_ur}
        )


class Migration(migrations.Migration):
    dependencies = [
        (
            "branches",
            "0002_branch_address_en_branch_address_ur_branch_closed_on_and_more",
        ),
    ]
    operations = [migrations.RunPython(seed_cities, migrations.RunPython.noop)]
