"""
Management command to seed initial permissions and role mappings.

Usage:
    python manage.py seed_permissions
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.users.models import Permission, RolePermission
from core.enums import UserRole


class Command(BaseCommand):
    help = 'Seed initial permissions and role-permission mappings'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🌱 Seeding permissions...'))

        with transaction.atomic():
            # Clear existing permissions
            self.stdout.write('Clearing existing permissions...')
            RolePermission.objects.all().delete()
            Permission.objects.all().delete()

            # Define permissions
            permissions_data = [
                # Order permissions
                {'resource': 'order', 'action': 'create', 'description': 'Create new orders'},
                {'resource': 'order', 'action': 'read', 'description': 'View orders'},
                {'resource': 'order', 'action': 'update', 'description': 'Update order information'},
                {'resource': 'order', 'action': 'delete', 'description': 'Delete orders'},
                {'resource': 'order', 'action': 'change_status', 'description': 'Change order status'},
                {'resource': 'order', 'action': 'assign_users', 'description': 'Assign users to orders'},
                {'resource': 'order', 'action': 'upload_image', 'description': 'Upload order images'},
                {'resource': 'order', 'action': 'delete_image', 'description': 'Delete order images'},
                {'resource': 'order', 'action': 'view_all', 'description': 'View all orders (not just assigned)'},

                # Comment permissions
                {'resource': 'comment', 'action': 'create', 'description': 'Create comments on orders'},
                {'resource': 'comment', 'action': 'read', 'description': 'Read comments'},
                {'resource': 'comment', 'action': 'update', 'description': 'Update own comments'},
                {'resource': 'comment', 'action': 'delete', 'description': 'Delete own comments'},
                {'resource': 'comment', 'action': 'delete_any', 'description': 'Delete any comment'},

                # User permissions
                {'resource': 'user', 'action': 'create', 'description': 'Create new users'},
                {'resource': 'user', 'action': 'read', 'description': 'View users'},
                {'resource': 'user', 'action': 'update', 'description': 'Update users'},
                {'resource': 'user', 'action': 'delete', 'description': 'Delete users'},
                {'resource': 'user', 'action': 'manage_permissions', 'description': 'Manage user permissions'},

                # Product permissions
                {'resource': 'product', 'action': 'create', 'description': 'Create products'},
                {'resource': 'product', 'action': 'read', 'description': 'View products'},
                {'resource': 'product', 'action': 'update', 'description': 'Update products'},
                {'resource': 'product', 'action': 'delete', 'description': 'Delete products'},

                # Report permissions
                {'resource': 'report', 'action': 'view', 'description': 'View reports'},
                {'resource': 'report', 'action': 'export', 'description': 'Export reports'},
            ]

            # Create permissions
            self.stdout.write('Creating permissions...')
            permissions = {}
            for perm_data in permissions_data:
                perm = Permission.objects.create(**perm_data)
                permissions[perm.name] = perm
                self.stdout.write(f'  ✓ {perm.name}')

            # Define role-permission mappings
            role_permissions = {
                UserRole.ADMIN.value: [
                    # Admin has ALL permissions
                    *permissions.keys()
                ],

                UserRole.MANAGER.value: [
                    # Manager has most permissions except user management
                    'order:create', 'order:read', 'order:update', 'order:delete',
                    'order:change_status', 'order:assign_users', 'order:upload_image',
                    'order:delete_image', 'order:view_all',
                    'comment:create', 'comment:read', 'comment:update', 'comment:delete',
                    'comment:delete_any',
                    'product:create', 'product:read', 'product:update', 'product:delete',
                    'report:view', 'report:export',
                    'user:read',  # Can view users but not manage
                ],

                UserRole.SALE.value: [
                    # Sale can create and manage early-stage orders
                    'order:create', 'order:read', 'order:update',
                    'order:change_status',  # Limited by status transition rules
                    'order:assign_users', 'order:upload_image',
                    'comment:create', 'comment:read', 'comment:update', 'comment:delete',
                    'product:read',
                    'user:read',
                ],

                UserRole.WEIGHING.value: [
                    # Weighing can handle weighing stage
                    'order:read', 'order:change_status',
                    'order:upload_image',  # For weighing photos
                    'comment:create', 'comment:read',
                    'product:read',
                ],

                UserRole.KITCHEN.value: [
                    # Kitchen can handle kitchen stage
                    'order:read', 'order:change_status',
                    'order:upload_image',  # For cooking photos
                    'comment:create', 'comment:read',
                    'product:read',
                ],
            }

            # Create role-permission mappings
            self.stdout.write('\nCreating role-permission mappings...')
            for role, perm_names in role_permissions.items():
                self.stdout.write(f'\n{role.upper()}:')
                for perm_name in perm_names:
                    if perm_name in permissions:
                        RolePermission.objects.create(
                            role=role,
                            permission=permissions[perm_name]
                        )
                        self.stdout.write(f'  ✓ {perm_name}')

            self.stdout.write(self.style.SUCCESS('\n✅ Permissions seeded successfully!'))
            self.stdout.write(self.style.SUCCESS(f'   Created {len(permissions)} permissions'))
            self.stdout.write(self.style.SUCCESS(f'   Created {RolePermission.objects.count()} role mappings'))
