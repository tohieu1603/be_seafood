# Generated manually for Shield RBAC

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('resource', models.CharField(help_text='Resource name (e.g., order, user, product)', max_length=50, verbose_name='Resource')),
                ('action', models.CharField(help_text='Action name (e.g., create, read, update, delete)', max_length=50, verbose_name='Action')),
                ('name', models.CharField(help_text='Unique permission name in format resource:action', max_length=100, unique=True, verbose_name='Permission Name')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
            ],
            options={
                'verbose_name': 'Permission',
                'verbose_name_plural': 'Permissions',
                'db_table': 'permissions',
                'ordering': ['resource', 'action'],
                'unique_together': {('resource', 'action')},
            },
        ),
        migrations.CreateModel(
            name='UserPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('granted', models.BooleanField(default=True, help_text='True = grant permission, False = revoke permission', verbose_name='Granted')),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_permissions', to='users.permission', verbose_name='Permission')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_permissions', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'User Permission',
                'verbose_name_plural': 'User Permissions',
                'db_table': 'user_permissions',
                'ordering': ['user', 'permission'],
                'unique_together': {('user', 'permission')},
            },
        ),
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('role', models.CharField(help_text='Role name from UserRole enum (admin, manager, sale, etc.)', max_length=20, verbose_name='Role')),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_permissions', to='users.permission', verbose_name='Permission')),
            ],
            options={
                'verbose_name': 'Role Permission',
                'verbose_name_plural': 'Role Permissions',
                'db_table': 'role_permissions',
                'ordering': ['role', 'permission'],
                'unique_together': {('role', 'permission')},
            },
        ),
    ]
