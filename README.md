# MAPD Casos

Plataforma educacional de simulação clínica para estudo de infecções na Atenção Primária à Saúde (APS) do SUS, baseada no livro **Mecanismos de Agressão, Patológicos e de Defesa**, de Prof. Rodrigo Niskier Ferreira Barbosa.

## Estado atual

O projeto possui dois gates distintos:

- **Piloto gratuito controlado**: otimizado para PythonAnywhere gratuito, com 1 web worker, SQLite e cache em arquivo.
- **Produção plena multiusuário**: requer banco multiusuário, cache compartilhado e múltiplos workers.

O perfil gratuito é detectado automaticamente quando o ambiente está em `production`, usando SQLite e sem Redis. Nesse modo o sistema reduz pressão sobre o único worker e aplica limites conservadores de IA.

## O que já está implementado

- Login e cadastro de alunos por **RGM, nome, turma e senha**.
- Normalização de RGM e compatibilidade com cadastros legados formatados.
- Cadastro atômico e unicidade real no banco.
- Um fluxo de **superusuário/professor único**.
- Escolha pós-login entre **estudo com auxílio de IA** e **Árvore decisória**.
- Painel do aluno com quatro ambulatórios: **Bactérias, Fungos, Vírus e Parasitas**.
- **80 pacientes iniciais**, 20 por categoria.
- Paciente, preceptor, tutor conceitual e avaliação final por IA.
- **Árvore decisória sem IA para os 20 casos bacterianos**, com seis decisões por caso.
- Em cada decisão da árvore há quatro níveis pedagógicos: **melhor resposta**, **correta mas subótima**, **plausível mas incorreta** e **totalmente incorreta**.
- Ordem das alternativas variável e determinística por caso/ponto de decisão, evitando padrão posicional da resposta correta.
- Pontuação e feedback imediatos por decisão, com resumo final e revelação do agente etiológico.
- Trilhas IA e árvore registradas separadamente, permitindo que o mesmo aluno resolva o mesmo caso nas duas modalidades.
- Conteúdo da árvore centrado em reconhecimento sindrômico/etiológico, uso criterioso de exames, stewardship de antimicrobianos, sinais de alarme e limites da APS/SUS.
- AI Gateway centralizado com Model Router, Error Router, retry, fallback, circuit breaker e kill switches.
- Structured Output com Pydantic e validação semântica.
- Idempotência por `request_id`, single-flight, rate limiting e backpressure.
- Sessão assinada em cookie e redução de escritas no SQLite.
- Painel do professor com turmas, alunos, casos concluídos, médias, modalidade e atividade recente.
- Logs técnicos com `request_id`, usuário anonimizado, duração, modelo, erros e tokens.
- Health checks de aplicação, banco, IA e fila.
- Backup SQLite verificado e rotativo.
- Manutenção manual para o perfil gratuito.
- Gates `production_readiness` e `free_tier_readiness`.
- CI com testes de desenvolvimento, configuração production-like e perfil gratuito realista.

## Arquitetura

- Python / Django 5.2 LTS
- Django Templates + JavaScript
- Gemini Interactions API via `google-genai`
- Pydantic para validação rígida de saída
- SQLite no piloto gratuito
- PostgreSQL opcional por `DATABASE_URL`
- Cache em arquivo no perfil de 1 worker
- Redis opcional por `REDIS_URL`
- Variáveis de ambiente em `.env`

A chave Gemini nunca é enviada ao navegador. A modalidade de árvore decisória não realiza chamadas à IA.

## Modelos Gemini

```env
GEMINI_CHAT_MODEL=gemini-3.6-flash
GEMINI_CHAT_FALLBACK_MODEL=gemini-3.5-flash-lite
GEMINI_EVALUATION_MODEL=gemini-3.6-flash
GEMINI_EVALUATION_FALLBACK_MODEL=gemini-3.5-flash
```

Chat e avaliação final priorizam o 3.6 Flash, validado de ponta a ponta. Modelos da
família 2.5 (ex.: `gemini-2.5-flash-lite`) existem no catálogo da conta e funcionam
via `generateContent`, mas retornaram `404 Not Found` ao criar uma interação na API
preview de Interactions — por isso os fallbacks ficam restritos à família 3.x e a
aliases `*-latest`, confirmados diretamente contra esse endpoint em produção.

## Instalação / atualização

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

## Perfil gratuito

Use:

```env
FREE_TIER_PROFILE=auto
```

Em produção com SQLite e sem Redis, o perfil gratuito limita automaticamente:

- 1 job de IA pendente por aluno;
- 20 jobs globais;
- 8 novas solicitações/minuto por aluno;
- 60 novas solicitações/minuto globalmente;
- 50 novas solicitações/minuto por tipo de tarefa.

### Gate do piloto gratuito

```bash
python manage.py free_tier_readiness --strict
```

Passar nesse gate significa **apto para piloto controlado dentro das limitações declaradas**. Não equivale a produção plena de alta concorrência.

### Backup e manutenção

Antes de uma sessão importante:

```bash
python manage.py backup_sqlite --keep 2
python manage.py free_tier_maintenance
```

`free_tier_maintenance` cria backup por padrão, remove apenas registros técnicos antigos de `AIJob`, limpa cache descartável e remove referências locais antigas ao estado remoto da Gemini. As mensagens clínicas persistidas e os resultados acadêmicos permanecem no banco.

## Gate de produção plena

```bash
python manage.py check --deploy
python manage.py production_readiness --strict
python manage.py test
```

O gate pleno continuará apontando PostgreSQL e Redis como pendentes enquanto a hospedagem gratuita não oferecer esses recursos. Isso é intencional.

## Atualização no PythonAnywhere

```bash
workon mapdcasos
cd ~/mapdcasos
git pull origin main
pip install -U -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py test
python manage.py free_tier_readiness --strict
```

Depois, use **Reload** na aba Web.

## Observação acadêmica

A árvore bacteriana foi estruturada para treino formativo e usa como âncoras documentos oficiais brasileiros, incluindo PCDT do Ministério da Saúde, protocolos de Atenção Básica, manual nacional de tuberculose e PCDT de IST. Em condições nas quais não existe um único esquema nacional universal para todo contexto ambulatorial, a árvore ensina a selecionar tratamento de primeira linha conforme protocolo SUS/local, perfil do paciente, gravidade, resistência e necessidade de referência, evitando transformar uma regra local em recomendação nacional.

Antes de uso avaliativo institucional, recomenda-se auditoria docente periódica das condutas e links oficiais, porque protocolos clínicos podem ser atualizados.
