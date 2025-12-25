"""
URL configuration for SmartForms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from depedsfportal.views_dashboard import (
    DashboardRedirectView,
    TeacherDashboardView,
    PrincipalDashboardView,
    dashboard_stats_api,
)
from depedsfportal.views_forms import (
    SchoolUpdateView,
    StudentCreateView,
    StudentUpdateView,
    AcademicRecordCreateView,
    LearningAreaListView,
    LearningAreaCreateView,
    LearningAreaUpdateView,
    LearningAreaDeleteView,
    AcademicRecordDetailView,
    SubjectGradeCreateView,
    SubjectGradeUpdateView,
    SubjectGradeDeleteView,
)
from depedsfportal.views_reports import (
    ReportDashboardView,
    ExportReportCSVView,
    ExportReportPDFView,
    ExportReportPDFView,
    AnalyticsDashboardView,
)
from depedsfportal.views_import import StudentImportView

from depedsfportal.views_sf10 import (
    SF10PrintView,
    SF10PreviewView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth
    path(
        "login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="logout"),
    # Dashboard Redirect
    path("", DashboardRedirectView.as_view(), name="dashboard_redirect"),
    path(
        "dashboard/teacher/", TeacherDashboardView.as_view(), name="teacher_dashboard"
    ),
    path(
        "dashboard/principal/",
        PrincipalDashboardView.as_view(),
        name="principal_dashboard",
    ),
    # API endpoints
    path("api/dashboard-stats/", dashboard_stats_api, name="dashboard_stats_api"),
    # Forms - Principal
    path("school/settings/", SchoolUpdateView.as_view(), name="school_settings"),
    # Forms - Teacher
    path("student/add/", StudentCreateView.as_view(), name="student_add"),
    path("student/<int:pk>/edit/", StudentUpdateView.as_view(), name="student_edit"),
    path(
        "student/<int:student_pk>/record/add/",
        AcademicRecordCreateView.as_view(),
        name="record_add",
    ),
    path("record/<int:pk>/", AcademicRecordDetailView.as_view(), name="record_detail"),
    # Forms - Learning Areas
    path("learning-areas/", LearningAreaListView.as_view(), name="learning_area_list"),
    path(
        "learning-areas/add/",
        LearningAreaCreateView.as_view(),
        name="learning_area_add",
    ),
    path(
        "learning-areas/<int:pk>/edit/",
        LearningAreaUpdateView.as_view(),
        name="learning_area_edit",
    ),
    path(
        "learning-areas/<int:pk>/delete/",
        LearningAreaDeleteView.as_view(),
        name="learning_area_delete",
    ),
    # Forms - Grades
    path(
        "grade/add/<int:record_pk>/", SubjectGradeCreateView.as_view(), name="grade_add"
    ),
    path("grade/<int:pk>/edit/", SubjectGradeUpdateView.as_view(), name="grade_edit"),
    path(
        "grade/<int:pk>/delete/", SubjectGradeDeleteView.as_view(), name="grade_delete"
    ),
    # Reports & Analytics - Principal
    path("reports/", ReportDashboardView.as_view(), name="report_dashboard"),
    path(
        "reports/export/csv/", ExportReportCSVView.as_view(), name="export_report_csv"
    ),
    path(
        "reports/export/pdf/", ExportReportPDFView.as_view(), name="export_report_pdf"
    ),
    path("analytics/", AnalyticsDashboardView.as_view(), name="analytics_dashboard"),
    # Import
    path("import/students/", StudentImportView.as_view(), name="student_import"),
    # SF10 Print
    path("sf10/print/<str:lrn>/", SF10PrintView.as_view(), name="sf10_print"),
    path("sf10/preview/<str:lrn>/", SF10PreviewView.as_view(), name="sf10_preview"),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0]
    )
