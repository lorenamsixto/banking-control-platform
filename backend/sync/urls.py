from django.urls import path

from . import views


urlpatterns = [
    path(
        "sincronizaciones/",
        views.SincronizacionListView.as_view(),
        name="sincronizacion-list",
    ),
    path(
        "sincronizaciones/<uuid:pk>/",
        views.SincronizacionDetailView.as_view(),
        name="sincronizacion-detail",
    ),
    path(
        "logs/",
        views.LogErrorListView.as_view(),
        name="log-error-list",
    ),
    path(
        "logs/<int:pk>/",
        views.LogErrorDetailView.as_view(),
        name="log-error-detail",
    ),
    path(
        "remediaciones/",
        views.AccionRemediacionCreateView.as_view(),
        name="remediacion-create",
    ),
    path(
        "procesar/",
        views.ProcesarArchivoView.as_view(),
        name="procesar-archivo",
    ),
    path(
        "dashboard/metricas/",
        views.DashboardMetricasView.as_view(),
        name="dashboard-metricas",
    ),
]