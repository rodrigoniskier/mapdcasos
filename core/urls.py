from django.urls import path

from . import attempt_views, tree_views, views

urlpatterns = [
    path('', views.home, name='home'),
    path('cadastro/', views.signup, name='signup'),
    path('modo-de-estudo/', views.study_mode, name='study_mode'),
    path('painel/', views.dashboard, name='dashboard'),
    path('casos/<str:category>/', views.category_cases, name='category_cases'),
    path('atendimento/<int:case_id>/', views.case_chat, name='case_chat'),
    path('atendimento/<int:case_id>/mensagem/', views.send_message, name='send_message'),
    path('atendimento/<int:case_id>/preceptor/', views.ask_preceptor, name='ask_preceptor'),
    path('atendimento/<int:case_id>/conceito/', views.remember_concept, name='remember_concept'),
    path('atendimento/<int:case_id>/concluir/', views.conclude_case, name='conclude_case'),
    path('atendimento/<int:case_id>/resumo/', views.case_summary, name='case_summary'),
    path('atendimento/<int:case_id>/conversa/', attempt_views.ai_transcript, name='ai_transcript'),
    path('atendimento/<int:case_id>/reiniciar/', attempt_views.restart_ai_case, name='restart_ai_case'),
    path('arvore/<int:case_id>/', tree_views.decision_tree_case, name='decision_tree_case'),
    path('arvore/<int:case_id>/resumo/', tree_views.tree_summary, name='tree_summary'),
    path('arvore/<int:case_id>/historico/', attempt_views.tree_transcript, name='tree_transcript'),
    path('arvore/<int:case_id>/reiniciar/', attempt_views.restart_tree_case, name='restart_tree_case'),
    path('ai/jobs/<uuid:request_id>/', views.ai_job_status, name='ai_job_status'),
    path('professor/', views.professor_dashboard, name='professor_dashboard'),
    path('professor/aluno/<int:user_id>/', views.professor_student, name='professor_student'),
    path('healthz/', views.healthz, name='healthz'),
    path('app-health/', views.app_health, name='app_health'),
    path('database-health/', views.database_health, name='database_health'),
    path('ai-health/', views.ai_health, name='ai_health'),
    path('queue-health/', views.queue_health, name='queue_health'),
]
