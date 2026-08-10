import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='encounter',
            name='patient_interaction_id',
            field=models.CharField(blank=True, max_length=512),
        ),
        migrations.AddField(
            model_name='encounter',
            name='patient_interaction_model',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.CreateModel(
            name='AIJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('kind', models.CharField(choices=[('PATIENT', 'Paciente virtual'), ('PRECEPTOR', 'Preceptor'), ('CONCEPT', 'Lembre o conceito'), ('EVALUATION', 'Avaliação final')], db_index=True, max_length=16)),
                ('status', models.CharField(choices=[('PENDING', 'Pendente'), ('RUNNING', 'Processando'), ('COMPLETED', 'Concluído'), ('FAILED', 'Falhou'), ('CANCELLED', 'Cancelado')], db_index=True, default='PENDING', max_length=16)),
                ('input_hash', models.CharField(db_index=True, max_length=64)),
                ('prompt_version', models.CharField(blank=True, max_length=64)),
                ('provider_interaction_id', models.CharField(blank=True, db_index=True, max_length=512)),
                ('model_used', models.CharField(blank=True, max_length=80)),
                ('fallback_used', models.BooleanField(default=False)),
                ('repair_attempts', models.PositiveSmallIntegerField(default=0)),
                ('result', models.JSONField(blank=True, default=dict)),
                ('error_type', models.CharField(blank=True, max_length=64)),
                ('error_code', models.CharField(blank=True, max_length=32)),
                ('error_message', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('encounter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_jobs', to='core.encounter')),
                ('source_message', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_jobs', to='core.message')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_jobs', to='core.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='aijob',
            index=models.Index(fields=['student', 'status', 'created_at'], name='aijob_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='aijob',
            index=models.Index(fields=['encounter', 'kind', 'status'], name='aijob_enc_kind_idx'),
        ),
    ]
