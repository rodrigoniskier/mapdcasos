# MAPD Casos — Auditoria Protocolo RN v1.0

Data: 2026-08-10

## Estado geral

A aplicação foi submetida ao hardening previsto no Protocolo RN para aplicações web com IA generativa. O código está preparado para operação multiusuário, mas a infraestrutura de produção ainda precisa substituir SQLite por PostgreSQL e, com múltiplos web workers, usar Redis compartilhado.

## Implementado

- Backend-first: nenhuma chave Gemini no frontend.
- Autenticação e autorização no servidor.
- RGM normalizado, unicidade no banco e cadastro atômico.
- Idempotência por `request_id` em ações de IA.
- `AIJob` para controle de solicitações, single-flight e backpressure.
- Limites por usuário, globais e por tipo de tarefa.
- AI Gateway único; integração direta legada removida.
- Model Router por tipo de tarefa.
- Error Router para 400/401/403, 429, 408/5xx/rede, safety, schema e saída vazia.
- Retry do SDK limitado com exponential backoff e jitter.
- Fallback orientado por classe de erro.
- Circuit breaker por modelo.
- Kill switches globais e por função.
- Structured Output com schema do provedor e validação Pydantic `extra=forbid`.
- Validação semântica de tratamento e soma da rubrica de avaliação.
- Repair retry limitado para erro de schema.
- Token budget distinto para chat e avaliação.
- Prompts versionados e separados da entrada do usuário.
- Histórico/contexto limitado e estado de conversa do provedor reutilizado quando disponível.
- Saída renderizada como texto, sem HTML bruto da IA.
- Logs com request_id, usuário anonimizado, endpoint, duração e métricas da IA.
- Health checks de app, banco, IA e fila.
- Sessão assinada em cookie, compatível com múltiplos workers sem escrita de sessão no banco.
- `last_login` desativado para reduzir escrita concorrente.
- Testes de autenticação, normalização, schema, Error Router, rate limiting e idempotência.
- Comando `python manage.py production_readiness` para auditoria operacional.

## Pendências de infraestrutura antes de turma real

### P1 — PostgreSQL

Não operar turma simultânea sobre SQLite. Configurar `DATABASE_URL` com PostgreSQL e executar migrações.

### P1 — Redis compartilhado

Com múltiplos web workers, configurar `REDIS_URL` para compartilhar rate limiter e circuit breakers entre processos.

### P1 — Web workers

Dimensionar múltiplos workers no provedor de hospedagem. A fila lógica reduz bloqueio, mas o front controller ainda precisa capacidade concorrente para login, dashboard, criação e polling de jobs.

### P1 — Teste de carga real

Executar jornadas completas em 5, 20, 50 e, se necessário, 100 usuários concorrentes, observando P50/P95/P99, 429, 5xx, tempo de fila, falhas de schema e recuperação.

## Gate recomendado antes da aula

```bash
python manage.py check --deploy
python manage.py production_readiness --strict
python manage.py test
```

Somente liberar para turma quando o gate estrito passar em ambiente de produção e o teste de carga confirmar degradação controlada.
