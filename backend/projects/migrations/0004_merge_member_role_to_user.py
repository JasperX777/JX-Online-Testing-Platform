from django.db import migrations


def merge_member_roles(apps, schema_editor):
    ProjectMember = apps.get_model('projects', 'ProjectMember')
    ProjectMember.objects.filter(role_in_project='tester').update(role_in_project='user')


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0003_alter_projectmember_role_in_project'),
    ]

    operations = [
        migrations.RunPython(merge_member_roles, migrations.RunPython.noop),
    ]
