"""
Management command to delete order images older than specified days.
Usage:
    python manage.py cleanup_old_images --days 30
    python manage.py cleanup_old_images --days 30 --dry-run
"""
import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from apps.orders.models import OrderImage


class Command(BaseCommand):
    help = 'Delete order images older than specified days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete images older than this many days (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)

        # Get old images
        old_images = OrderImage.objects.filter(created_at__lt=cutoff_date)
        total_count = old_images.count()

        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'No images older than {days} days found.')
            )
            return

        # Calculate total size
        total_size = 0
        deleted_count = 0
        failed_count = 0

        self.stdout.write(
            self.style.WARNING(f'\nFound {total_count} images older than {days} days.')
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE('\n=== DRY RUN MODE - Nothing will be deleted ===\n')
            )

        for image in old_images:
            try:
                # Get file size
                if image.image and os.path.exists(image.image.path):
                    file_size = os.path.getsize(image.image.path)
                    total_size += file_size

                    self.stdout.write(
                        f'  - {image.image.name} ({file_size / 1024:.2f} KB) '
                        f'from Order #{image.order.order_number} '
                        f'created on {image.created_at.strftime("%Y-%m-%d")}'
                    )

                    if not dry_run:
                        # Delete physical file
                        image.image.delete(save=False)
                        # Delete database record
                        image.delete()
                        deleted_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  - File not found: {image.image.name} (deleting DB record only)'
                        )
                    )
                    if not dry_run:
                        image.delete()
                        deleted_count += 1

            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  - Failed to delete {image.image.name}: {str(e)}')
                )

        # Summary
        total_size_mb = total_size / (1024 * 1024)

        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f'\nDRY RUN Summary:'
                    f'\n  - Images found: {total_count}'
                    f'\n  - Total size: {total_size_mb:.2f} MB'
                    f'\n  - Would be deleted: {total_count - failed_count}'
                    f'\n\nRun without --dry-run to actually delete these images.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nCleanup Summary:'
                    f'\n  - Total images: {total_count}'
                    f'\n  - Successfully deleted: {deleted_count}'
                    f'\n  - Failed: {failed_count}'
                    f'\n  - Space freed: {total_size_mb:.2f} MB'
                )
            )

        self.stdout.write('=' * 60 + '\n')
