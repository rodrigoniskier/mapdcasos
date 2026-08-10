# MAPD Casos

Plataforma educacional de simulação clínica por chatbot para estudo de infecções na Atenção Primária à Saúde (APS) do SUS, baseada no livro **Mecanismos de Agressão, Patológicos e de Defesa**, de Prof. Rodrigo Niskier Ferreira Barbosa.

## O que já está implementado

- Login e cadastro de alunos por **RGM, nome, turma e senha**.
- Um fluxo de **superusuário/professor único**, criado por comando e protegido contra criação acidental de outro superusuário pelo comando do projeto.
- Painel do aluno com quatro ambulatórios: **Bactérias, Fungos, Vírus e Parasitas**.
- **80 pacientes iniciais**, 20 por categoria, com ficha-mestra oculta, diagnóstico, patógeno, sinais de alarme, conceito-âncora e conduta esperada.
- Chat clínico com Gemini em quatro papéis lógicos:
  - Paciente;
  - Preceptor;
  - Tutor “Lembre o conceito”;
  - Avaliador final.
- Desfecho imediato quando o aluno propõe uma conduta terapêutica; condutas inadequadas podem gerar retorno do paciente.
- Avaliação final de 0 a 100 com resumo do caso, resumo do atendimento, pontos fortes, necessidades de reforço e tópicos de revisão.
- Painel do professor com turmas, alunos, casos concluídos, médias e atividades recentes.
- Django Admin em `/django-admin/` para manutenção dos casos.
- Endpoint de saúde em `/healthz/`.

## Arquitetura

- Python / Django 5.2 LTS
- Django Templates + JavaScript
- Gemini API via pacote `google-genai`
- SQLite como fallback local; suporte a PostgreSQL por `DATABASE_URL`
- Variáveis de ambiente com `.env`

A chave Gemini nunca é enviada ao navegador. Todas as chamadas à IA acontecem no backend.

## Agentes de IA

O paciente recebe a ficha-mestra completa e é instruído a não revelar diagnóstico, agente ou gabarito. O preceptor e o tutor recebem a mesma ficha e o histórico da conversa, mas têm prompts diferentes. O avaliador recebe a conversa completa apenas quando o estudante conclui o caso.

## Instalação local / PythonAnywhere

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_cases
python manage.py bootstrap_admin
python manage.py collectstatic --noinput
```

Edite `.env` antes de `bootstrap_admin`.

## Variáveis principais

```env
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=mapdcasos.pythonanywhere.com
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.5-flash
SUPERUSER_USERNAME=rodrigo
SUPERUSER_NAME=Prof. Rodrigo Niskier
SUPERUSER_PASSWORD=...
```

Para PostgreSQL:

```env
DATABASE_URL=postgresql://usuario:senha@host:porta/banco
```

## Observação acadêmica

Os 80 casos são uma primeira carga didática estruturada para validação docente. Antes de uso avaliativo institucional, recomenda-se revisar as condutas esperadas e sinais de alarme contra os PCDT, manuais e notas técnicas vigentes do Ministério da Saúde. O sistema foi desenhado para permitir essa revisão diretamente pelo Django Admin, sem alterar a lógica do chatbot.
