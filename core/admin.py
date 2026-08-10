from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AIJob, ClinicalCase, Encounter, Message, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("MAPD Casos", {'fields': ('rgm', 'turma', 'role')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("MAPD Casos", {'fields': ('rgm', 'turma', 'role')}),)
    list_display = ('username', 'get_full_name', 'rgm', 'turma', 'role', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name', 'rgm', 'turma')


@admin.register(ClinicalCase)
class ClinicalCaseAdmin(admin.ModelAdmin):
    list_display = ('code', 'category', 'order', 'public_title', 'pathogen', 'difficulty', 'active')
    list_filter = ('category', 'difficulty', 'active')
    search_fields = ('code', 'public_title', 'pathogen', 'diagnosis')


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ('student', 'case', 'status', 'outcome', 'score', 'updated_at')
    list_filter = ('status', 'outcome', 'case__category')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'case__code')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('encounter', 'role', 'created_at', 'preview')
    list_filter = ('role',)

    @admin.display(description='Mensagem')
    def preview(self, obj):
        return obj.content[:90]


@admin.register(AIJob)
class AIJobAdmin(admin.ModelAdmin):
    list_display = (
        'request_id', 'kind', 'status', 'student', 'model_used',
        'fallback_used', 'repair_attempts', 'error_type', 'created_at',
    )
    list_filter = ('kind', 'status', 'model_used', 'fallback_used', 'error_type')
    search_fields = ('request_id', 'student__username', 'encounter__case__code', 'error_type')
    readonly_fields = (
        'request_id', 'encounter', 'student', 'source_message', 'kind', 'status',
        'input_hash', 'prompt_version', 'provider_interaction_id', 'model_used',
        'fallback_used', 'repair_attempts', 'result', 'error_type', 'error_code',
        'error_message', 'created_at', 'started_at', 'completed_at', 'updated_at',
    )

    def has_add_permission(self, request):
        return False
