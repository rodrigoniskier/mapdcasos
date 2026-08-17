from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_aijob_and_interaction_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='encounter',
            name='mode',
            field=models.CharField(
                choices=[('AI', 'Com auxílio de IA'), ('TREE', 'Árvore decisória')],
                db_index=True,
                default='AI',
                max_length=8,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='encounter',
            name='unique_student_case_encounter',
        ),
        migrations.AddConstraint(
            model_name='encounter',
            constraint=models.UniqueConstraint(
                fields=('student', 'case', 'mode'),
                name='unique_student_case_mode_encounter',
            ),
        ),
        migrations.CreateModel(
            name='DecisionAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('node_id', models.CharField(max_length=64)),
                ('prompt', models.TextField()),
                ('selected_option_id', models.CharField(max_length=24)),
                ('selected_text', models.TextField()),
                ('quality', models.CharField(
                    choices=[
                        ('BEST', 'Melhor resposta'),
                        ('SUBOPTIMAL', 'Correta, mas subótima'),
                        ('PLAUSIBLE', 'Plausível, mas incorreta'),
                        ('WRONG', 'Totalmente incorreta'),
                    ],
                    max_length=16,
                )),
                ('points', models.PositiveSmallIntegerField(default=0)),
                ('feedback', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('encounter', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='decision_answers',
                    to='core.encounter',
                )),
            ],
            options={'ordering': ['created_at', 'id']},
        ),
        migrations.AddConstraint(
            model_name='decisionanswer',
            constraint=models.UniqueConstraint(
                fields=('encounter', 'node_id'),
                name='unique_decision_answer_per_node',
            ),
        ),
    ]
