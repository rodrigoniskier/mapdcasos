from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('cadastro/', views.signup, name='signup'),
    path('painel/', views.dashboard, name='dashboard'),
    path('casos/<str:category>/', views.category_cases, name='category_cases'),
    path('atendimento/<int:case_id>/', views.case_chat, name='case_chat'),
    path('atendimento/<int:case_id>/mensagem/', views.send_message, name='send_message'),
    path('atendimento/<int:case_id>/preceptor/', views.ask_preceptor, name='ask_preceptor'),
    path('atendimento/<int:case_id>/conceito/', views.remember_concept, name='remember_concept'),
    path('atendimento/<int:case_id>/concluir/', views.conclude_case, name='conclude_case'),
    path('atendimento/<int:case_id>/resumo/', views.case_summary, name='case_summary'),
    path('professor/', views.professor_dashboard, name='professor_dashboard'),
    path('professor/aluno/<int:user_id>/', views.professor_student, name='professor_student'),
    path('healthz/', views.healthz, name='healthz'),
]
