from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    path('password_change/', views.password_change, name='password_change'),
    path('', views.home, name='home'),
    path('courses/', views.course_list, name='course_list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('view/<str:certificate_id>/', views.view_certificate, name='view_certificate'),
    path('verify/', views.verify, name='verify'),
]
