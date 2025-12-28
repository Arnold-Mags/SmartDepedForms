from django.db import migrations, models
import django.db.models.deletion


def migrate_sections_sql(apps, schema_editor):
    from django.db import connection

    cursor = connection.cursor()

    # 1. Ensure we have sections and link them
    cursor.execute(
        "SELECT DISTINCT grade_level, section FROM depedsfportal_academicrecord"
    )
    rows = cursor.fetchall()

    for grade_level, section_name in rows:
        section_name_str = str(section_name) if section_name else ""
        if not section_name_str or len(section_name_str) > 20:
            section_name_str = "Section A"

        # Ensure grade_level is an int for insertion
        try:
            gl = int(grade_level)
        except:
            gl = 7

        cursor.execute(
            "INSERT INTO depedsfportal_section (grade_level, name, max_students) "
            "SELECT %s, %s, 45 WHERE NOT EXISTS (SELECT 1 FROM depedsfportal_section WHERE grade_level=%s AND name=%s) "
            "RETURNING id",
            [gl, section_name_str, gl, section_name_str],
        )
        res = cursor.fetchone()
        if res:
            section_id = res[0]
        else:
            cursor.execute(
                "SELECT id FROM depedsfportal_section WHERE grade_level=%s AND name=%s",
                [gl, section_name_str],
            )
            section_id = cursor.fetchone()[0]

        cursor.execute(
            "UPDATE depedsfportal_academicrecord SET section_link_id = %s WHERE grade_level = %s AND (section = %s OR (%s = 'Section A' AND (section IS NULL OR LENGTH(section) > 20)))",
            [section_id, grade_level, section_name, section_name_str],
        )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("depedsfportal", "0007_section_alter_student_status_teacherprofile_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_sections_sql),
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
            ),
            preserve_default=False,
        ),
    ]
