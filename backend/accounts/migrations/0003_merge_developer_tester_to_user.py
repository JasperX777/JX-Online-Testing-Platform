from django.db import migrations


def merge_roles(apps, schema_editor):
    Profile = apps.get_model('accounts', 'Profile')
    Profile.objects.filter(role__in=['developer', 'tester']).update(role='user')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_profile_role'),
    ]

    operations = [
        migrations.RunPython(merge_roles, migrations.RunPython.noop),
    ]
