from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("depedsfportal", "0007_section_alter_student_status_teacherprofile_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="academicrecord",
            name="section",
        ),
        migrations.RenameField(
            model_name="academicrecord",
            old_name="section_link",
            new_name="section",
        ),
        migrations.AlterField(
            model_name="academicrecord",
            name="section",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="academic_records",
                to="depedsfportal.section",
                default=1,  # Temporary default if needed, but we already have data
            ),
            preserve_default=False,
        ),
    ]
