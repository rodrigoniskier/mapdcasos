# MAPD Casos — Auditoria Protocolo RN v1.0

Data: 2026-08-10

## Estado geral

A aplicação foi submetida ao hardening previsto no Protocolo RN para aplicações web com IA generativa. Há agora dois níveis operacionais explicitamente separados:

1. **Piloto gratuito controlado** — compatível com a infraestrutura gratuita atual, com 1 worker, SQLite e cache em arquivo, usando limites conservadores e Gemini em background.
2. **Produção plena multiusuário** — exige banco multiusuário, cache compartilhado, múltiplos web workers e teste de carga compatível com turma real.

Essa separação evita classificar como bug aquilo que é limitação deliberada da hospedagem gratuita.

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
- Execução Gemini em `background=true` para liberar rapidamente o request web.
- Polling progressivo no frontend para reduzir pressão sobre o único worker.
- Saída renderizada como texto, sem HTML bruto da IA.
- Logs com request_id, usuário anonimizado, endpoint, duração e métricas da IA.
- Health checks de app, banco, IA e fila.
- Sessão assinada em cookie, sem escrita de sessão no banco.
- `last_login` desativado para reduzir escrita concorrente.
- Perfil gratuito automático quando `production + SQLite + sem Redis`.
- No perfil gratuito: máximo de 1 job/aluno, 20 jobs globais, 8 req/min/aluno, 60 req/min globais e 50 req/min/tipo.
- Backup SQLite consistente, verificado por `PRAGMA integrity_check` e com retenção rotativa.
- Manutenção manual para remover AIJobs técnicos antigos, cache descartável e referências remotas expiráveis, preservando histórico clínico.
- Testes de autenticação, normalização, schema, Error Router, rate limiting e idempotência.
- CI em três cenários: desenvolvimento, production-like e perfil gratuito operacional.
- Comando `production_readiness` para produção plena.
- Comando `free_tier_readiness` para piloto gratuito controlado.

## Gate do piloto gratuito

Antes de uso controlado:

```bash
python manage.py test
python manage.py free_tier_readiness --strict
python manage.py backup_sqlite --keep 2
```

Antes de uma sessão importante, executar:

```bash
python manage.py free_tier_maintenance
```

O piloto gratuito é considerado apto quando `free_tier_readiness --strict` passa. SQLite e cache em arquivo aparecem como **limitações declaradas**, não como falhas desse gate.

## Limitações aceitas no piloto gratuito

### SQLite

Aceito somente porque há um único web worker e o fluxo de IA foi retirado do request síncrono longo. Continua inadequado para produção multiworker.

### Cache em arquivo

É suficiente para o único worker atual. Não deve ser usado como mecanismo de coordenação quando houver múltiplos workers.

### Um único web worker

A aplicação reduz trabalho síncrono, usa Gemini em background e polling progressivo. Ainda assim, picos de navegação/login podem formar fila. O piloto deve ser gradual e monitorado.

### Manutenção manual

Sem processo always-on gratuito, backup e limpeza são tarefas operacionais manuais antes de sessões relevantes.

## Pendências para produção plena

### P1 — PostgreSQL

Configurar `DATABASE_URL` e migrar os dados para banco multiusuário.

### P1 — Redis compartilhado

Configurar `REDIS_URL` para rate limiter, circuit breakers e coordenação entre processos.

### P1 — Múltiplos web workers

Dimensionar workers conforme carga real.

### P1 — Teste de carga de turma real

Executar jornadas completas em 5, 20, 50 e, se necessário, 100 usuários concorrentes, observando P50/P95/P99, 429, 5xx, tempo de fila, falhas de schema e recuperação.

## Gates

### Piloto gratuito

```bash
python manage.py free_tier_readiness --strict
```

### Produção plena

```bash
python manage.py check --deploy
python manage.py production_readiness --strict
python manage.py test
```

O gate de produção plena deve continuar falhando enquanto a infraestrutura paga não estiver disponível. Isso é intencional e preserva a definição de pronto do Protocolo RN.
