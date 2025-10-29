from django.urls import path
from . import views

urlpatterns = [
    # Public views
    path('home/', views.home, name='home'),
    path('candidate/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),

    # Auth views
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Voting functionality
    path('vote/', views.submit_vote, name='submit_vote'),

    # Candidate results page (for candidates)
    path('candidate/results/', views.candidate_results, name='candidate_results'),

    # ✅ New page: view all users (for candidates only)
    path('all-users/', views.all_users_list, name='all_users'),
]