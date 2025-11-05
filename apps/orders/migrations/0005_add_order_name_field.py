# Generated migration for adding order_name field and updating order_number logic

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_orderitem_note'),
    ]

    operations = [
        # Add order_name field
        migrations.AddField(
            model_name='order',
            name='order_name',
            field=models.CharField(
                default='Đơn 1',
                max_length=255,
                verbose_name='Tên đơn hàng',
                help_text='Tên đơn hàng tự đặt (có thể trùng)'
            ),
            preserve_default=False,
        ),

        # Update order_number field (remove unique constraint)
        migrations.AlterField(
            model_name='order',
            name='order_number',
            field=models.CharField(
                max_length=50,
                verbose_name='Số đơn hàng (tự động theo ngày)',
                help_text='VD: Đơn 1, Đơn 2, Đơn 3 (reset mỗi ngày)'
            ),
        ),

        # Add indexes for searching
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['order_name'], name='orders_order_name_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['delivery_time'], name='orders_delivery_time_idx'),
        ),
    ]
