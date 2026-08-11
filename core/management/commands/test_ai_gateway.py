import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.services.ai_gateway import poll_interaction, start_background_interaction, validate_output
from core.services.ai_schemas import PatientAIResponse


class Command(BaseCommand):
    help = 'Testa a mesma rota Gemini usada pelo paciente virtual, sem expor a API key.'

    def add_arguments(self, parser):
        parser.add_argument('--timeout', type=int, default=30, help='Tempo máximo de polling em segundos.')

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('MAPD Casos — Diagnóstico do AI Gateway'))
        self.stdout.write(f'API version solicitada no ambiente: {settings.GEMINI_API_VERSION_REQUESTED}')
        self.stdout.write(f'API version efetiva: {settings.GEMINI_API_VERSION}')
        self.stdout.write(f'Modelo chat: {settings.GEMINI_CHAT_MODEL}')
        self.stdout.write(f'Fallback chat: {settings.GEMINI_CHAT_FALLBACK_MODEL}')
        self.stdout.write(f'Background: {settings.AI_BACKGROUND_ENABLED}')
        self.stdout.write(f'API key carregada: {bool(settings.GEMINI_API_KEY)}')

        result = start_background_interaction(
            kind='PATIENT',
            system_instruction=(
                'Você é um paciente virtual em um teste técnico. Responda em português, '
                'de forma breve. Não inclua dados pessoais reais.'
            ),
            input_text='Diga apenas que está pronto para o atendimento.',
            schema_model=PatientAIResponse,
        )
        if not result.ok:
            self._fail('CREATE', result)

        self.stdout.write(self.style.SUCCESS(
            f'[OK] CREATE — model={result.model} status={result.status} id={result.interaction_id[:24]}...'
        ))

        final = result
        deadline = time.monotonic() + max(5, options['timeout'])
        while final.status not in {'completed', 'failed'} and time.monotonic() < deadline:
            time.sleep(2)
            final = poll_interaction(result.interaction_id, model=result.model)
            if not final.ok:
                self._fail('POLL', final)
            self.stdout.write(f'POLL — status={final.status}')

        if final.status != 'completed':
            raise CommandError(f'Interação não concluiu no prazo; status={final.status or "desconhecido"}.')

        parsed, validation_error = validate_output(final.output_text, PatientAIResponse)
        if validation_error:
            self._fail('SCHEMA', validation_error)

        self.stdout.write(self.style.SUCCESS('[OK] STRUCTURED OUTPUT — JSON validado pelo Pydantic.'))
        self.stdout.write(self.style.SUCCESS(
            'AI Gateway operacional: endpoint, autenticação, modelo, background, polling e schema estão funcionando.'
        ))
        if parsed:
            self.stdout.write(f'Resposta técnica recebida: {parsed.get("reply", "")[:120]}')

    def _fail(self, stage, result):
        self.stderr.write(self.style.ERROR(
            f'[FALHA] {stage} — type={result.error_type} code={result.error_code or "-"} '
            f'model={result.model or "-"}'
        ))
        self.stderr.write(self.style.ERROR(
            f'Detalhe sanitizado: {result.error_message or "sem detalhe do provedor"}'
        ))
        raise CommandError('Falha no diagnóstico do AI Gateway.')
