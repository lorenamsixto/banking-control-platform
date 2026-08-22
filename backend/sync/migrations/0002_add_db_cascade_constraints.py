from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("sync", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE logs_errores
                DROP CONSTRAINT logs_errores_correlation_id_41b1af10_fk_sincroniz;

                ALTER TABLE logs_errores
                ADD CONSTRAINT logs_errores_correlation_id_fk
                FOREIGN KEY (correlation_id)
                REFERENCES sincronizaciones(correlation_id)
                ON DELETE CASCADE;
            """,
            reverse_sql="""
                ALTER TABLE logs_errores
                DROP CONSTRAINT logs_errores_correlation_id_fk;

                ALTER TABLE logs_errores
                ADD CONSTRAINT logs_errores_correlation_id_41b1af10_fk_sincroniz
                FOREIGN KEY (correlation_id)
                REFERENCES sincronizaciones(correlation_id)
                DEFERRABLE INITIALLY DEFERRED;
            """,
        ),

        migrations.RunSQL(
            sql="""
                ALTER TABLE archivos_procesados
                DROP CONSTRAINT archivos_procesados_sincronizacion_id_3bcf47fe_fk_sincroniz;

                ALTER TABLE archivos_procesados
                ADD CONSTRAINT archivos_procesados_sincronizacion_id_fk
                FOREIGN KEY (sincronizacion_id)
                REFERENCES sincronizaciones(id)
                ON DELETE CASCADE;
            """,
            reverse_sql="""
                ALTER TABLE archivos_procesados
                DROP CONSTRAINT archivos_procesados_sincronizacion_id_fk;

                ALTER TABLE archivos_procesados
                ADD CONSTRAINT archivos_procesados_sincronizacion_id_3bcf47fe_fk_sincroniz
                FOREIGN KEY (sincronizacion_id)
                REFERENCES sincronizaciones(id)
                DEFERRABLE INITIALLY DEFERRED;
            """,
        ),

        migrations.RunSQL(
            sql="""
                ALTER TABLE acciones_remediacion
                DROP CONSTRAINT acciones_remediacion_sincronizacion_id_f86c7edc_fk_sincroniz;

                ALTER TABLE acciones_remediacion
                ADD CONSTRAINT acciones_remediacion_sincronizacion_id_fk
                FOREIGN KEY (sincronizacion_id)
                REFERENCES sincronizaciones(id)
                ON DELETE CASCADE;
            """,
            reverse_sql="""
                ALTER TABLE acciones_remediacion
                DROP CONSTRAINT acciones_remediacion_sincronizacion_id_fk;

                ALTER TABLE acciones_remediacion
                ADD CONSTRAINT acciones_remediacion_sincronizacion_id_f86c7edc_fk_sincroniz
                FOREIGN KEY (sincronizacion_id)
                REFERENCES sincronizaciones(id)
                DEFERRABLE INITIALLY DEFERRED;
            """,
        ),
    ]