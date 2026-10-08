from django.conf import settings
from django.db import migrations

OWNERS_GROUP = 'owners'


def create_owners(apps, schema_editor):
    # Accounts made before roles existed could do everything; they stay owners.
    # Accounts made from now on are sellers until someone adds them to the group.
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    owners, _created = Group.objects.get_or_create(name=OWNERS_GROUP)
    owners.user_set.add(*User.objects.all())


def remove_owners(apps, schema_editor):
    apps.get_model('auth', 'Group').objects.filter(name=OWNERS_GROUP).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0004_sale_payment'),
    ]

    operations = [
        migrations.RunPython(create_owners, remove_owners),
    ]
