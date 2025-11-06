# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0006_ordercomment_ordercommentreaction_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='received_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Thời gian nhận hàng'),
        ),
        migrations.AddField(
            model_name='order',
            name='kitchen_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Thời gian vào bếp'),
        ),
    ]
