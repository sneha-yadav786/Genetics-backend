
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS records_appointmentslot (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    date DATE NOT NULL,
                    start_time TIME(6) NOT NULL,
                    end_time TIME(6) NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    is_booked BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at DATETIME(6) NOT NULL,
                    UNIQUE (date, start_time)
                );
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
