from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ClinicalCase, Encounter, Message, User


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
