from django.urls import path

from inspection import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.list_view, name="list"),
    path("inspections/new/", views.create_view, name="create"),
    path("inspections/<int:pk>/", views.detail_view, name="detail"),
    path("inspections/<int:pk>/edit/", views.edit_view, name="edit"),
    path("sheets/", views.sheet_list_view, name="sheet_list"),
    path("sheets/new/", views.sheet_create_view, name="sheet_create"),
    path("sheets/<int:pk>/", views.sheet_detail_view, name="sheet_detail"),
]
