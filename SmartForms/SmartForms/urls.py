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
    get_adviser_api,
)
from depedsfportal.views_forms import (
    SchoolUpdateView,
    StudentCreateView,
    StudentUpdateView,
    AcademicRecordCreateView,
    AcademicRecordUpdateView,
    LearningAreaListView,
    LearningAreaCreateView,
    LearningAreaUpdateView,
    LearningAreaDeleteView,
    AcademicRecordDetailView,
    SubjectGradeCreateView,
    SubjectGradeUpdateView,
    SubjectGradeDeleteView,
    SectionListView,
    SectionCreateView,
    SectionUpdateView,
    TeacherListView,
    TeacherCreateView,
    TeacherUpdateView,
    TeacherDetailView,
    AcademicRecordPromoteView,
    AcademicRecordRetainView,
    SubjectGradeRemedialUpdateView,
    AcademicYearListView,
    AcademicYearCreateView,
    AcademicYearUpdateView,
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
    path("api/get-adviser/", get_adviser_api, name="get_adviser_api"),
    # Forms - Principal
    path("school/settings/", SchoolUpdateView.as_view(), name="school_settings"),
    # Forms - Teacher
    path("student/add/", StudentCreateView.as_view(), name="student_add"),
    path("student/<str:pk>/edit/", StudentUpdateView.as_view(), name="student_edit"),
    path(
        "student/<str:student_pk>/record/add/",
        AcademicRecordCreateView.as_view(),
        name="record_add",
    ),
    path(
        "student/<str:student_pk>/record/<int:pk>/edit/",
        AcademicRecordUpdateView.as_view(),
        name="record_edit",
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
    # Section & Teacher Management
    path("sections/", SectionListView.as_view(), name="section_list"),
    path("sections/add/", SectionCreateView.as_view(), name="section_add"),
    path("sections/<int:pk>/edit/", SectionUpdateView.as_view(), name="section_edit"),
    path("teachers/", TeacherListView.as_view(), name="teacher_list"),
    path("teachers/add/", TeacherCreateView.as_view(), name="teacher_add"),
    path("teachers/<int:pk>/", TeacherDetailView.as_view(), name="teacher_detail"),
    path("teachers/<int:pk>/edit/", TeacherUpdateView.as_view(), name="teacher_edit"),
    # Academic Evaluation Actions
    path(
        "record/<int:pk>/promote/",
        AcademicRecordPromoteView.as_view(),
        name="record_promote",
    ),
    path(
        "record/<int:pk>/retain/",
        AcademicRecordRetainView.as_view(),
        name="record_retain",
    ),
    path(
        "grade/<int:pk>/remedial/",
        SubjectGradeRemedialUpdateView.as_view(),
        name="grade_remedial",
    ),
    # Academic Year Management
    path("academic-years/", AcademicYearListView.as_view(), name="academic_year_list"),
    path(
        "academic-years/add/",
        AcademicYearCreateView.as_view(),
        name="academic_year_add",
    ),
    path(
        "academic-years/<int:pk>/edit/",
        AcademicYearUpdateView.as_view(),
        name="academic_year_edit",
    ),
    path('record/<int:pk>/edit/', AcademicRecordUpdateView.as_view(), name='record_edit'),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0]
    )
