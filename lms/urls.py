from django.urls import path
from . import views

app_name = 'lms'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/import-material/', views.import_course_material_view, name='import_course_material'),
    path('courses/<slug:slug>/', views.course_detail, name='course_detail'),
    path('courses/<slug:slug>/feedback/', views.submit_course_feedback_view, name='submit_course_feedback'),
    path('courses/<slug:slug>/lessons/<int:lesson_id>/', views.lesson_view, name='lesson_view'),
    path('courses/<slug:slug>/lessons/<int:lesson_id>/complete/', views.lesson_toggle_complete, name='lesson_toggle_complete'),
    path('courses/<slug:slug>/lessons/<int:lesson_id>/mcq-score/', views.record_lesson_mcq_score, name='record_lesson_mcq_score'),
    path('api/execute-code/', views.execute_python_code_view, name='execute_python_code'),
    path('live-classes/', views.live_classes, name='live_classes'),
    path('assignments/', views.assignments_list, name='assignments_list'),
    path('assignments/<int:assignment_id>/', views.assignment_detail, name='assignment_detail'),
    path('assignments/<int:assignment_id>/submit/', views.assignment_submit, name='assignment_submit'),
    path('assignments/batch/<int:assignment_id>/submit/', views.submit_batch_assignment_view, name='submit_batch_assignment'),
    path('mentors/', views.mentors_list, name='mentors_list'),
    path('student-chats/', views.teacher_student_chats_view, name='teacher_student_chats'),
    path('mentors/<int:mentor_id>/chat/', views.mentor_chat_api, name='mentor_chat_api'),
    path('mentor/chat/<int:student_id>/reply/', views.mentor_reply_chat_api, name='mentor_reply_chat_api'),
    path('mentor/assignments/create/', views.mentor_create_assignment_view, name='mentor_create_assignment'),
    path('profile/', views.profile_view, name='profile'),
    path('admin-hub/', views.admin_hub, name='admin_hub'),
    path('admin-hub/courses/create/', views.create_course_view, name='create_course'),
    path('courses/<int:pk>/edit/', views.edit_course_view, name='edit_course'),
    path('admin-hub/courses/join-students/', views.join_students_view, name='join_students'),
    path('admin-hub/courses/add-module/', views.add_course_module_view, name='add_course_module'),
    path('admin-hub/courses/add-lesson/', views.add_course_lesson_view, name='add_course_lesson'),
    path('admin-hub/cohort-user/add/', views.add_cohort_user_view, name='add_cohort_user'),
    path('admin-hub/command-message/', views.create_command_message, name='create_command_message'),
    path('admin-hub/live-class/', views.schedule_live_class_view, name='schedule_live_class'),
    path('admin-hub/assignment/', views.create_assignment_view, name='create_assignment'),
    path('admin-hub/cohort-user/', views.manage_cohort_user_view, name='manage_cohort_user'),

    # Batches Management
    path('batches/create/', views.create_batch_view, name='create_batch'),
    path('batches/<int:pk>/', views.batch_detail_view, name='batch_detail'),
    path('batches/<int:pk>/edit/', views.edit_batch_view, name='edit_batch'),
    path('batches/<int:pk>/delete/', views.delete_batch_view, name='delete_batch'),
    path('batches/<int:pk>/members/', views.assign_batch_members_view, name='assign_batch_members'),

    # Batch Sessions (Meeting links) & Materials (Links & Attachments)
    path('batches/<int:batch_id>/sessions/add/', views.add_batch_session_view, name='add_batch_session'),
    path('sessions/add/', views.add_batch_session_view, name='add_general_session'),
    path('batches/sessions/<int:pk>/edit/', views.edit_batch_session_view, name='edit_batch_session'),
    path('batches/sessions/<int:pk>/delete/', views.delete_batch_session_view, name='delete_batch_session'),
    path('batches/<int:batch_id>/materials/add/', views.add_batch_material_view, name='add_batch_material'),
    path('materials/add/', views.add_batch_material_view, name='add_general_material'),
    path('batches/materials/<int:pk>/delete/', views.delete_batch_material_view, name='delete_batch_material'),

    # Batch Assignments (For Each Student or Send to All) & Session Attendance
    path('batches/<int:batch_id>/assignments/add/', views.add_batch_assignment_view, name='add_batch_assignment'),
    path('batches/<int:batch_id>/assignments/assess/', views.assess_batch_assignment_view, name='assess_batch_assignment'),
    path('batches/<int:batch_id>/assignments/<int:pk>/delete/', views.delete_batch_assignment_view, name='delete_batch_assignment'),
    path('batches/<int:batch_id>/attendance/mark/', views.mark_session_attendance_view, name='mark_session_attendance'),

    # User Profile Edit & Password Reset
    path('cohort-users/<int:pk>/edit/', views.edit_cohort_user_view, name='edit_cohort_user'),
    path('cohort-users/<int:pk>/reset-password/', views.reset_cohort_user_password_view, name='reset_cohort_user_password'),

    # Fees & Payments
    path('payments/', views.student_payments_view, name='student_payments'),
    path('payments/record/', views.record_student_payment_view, name='record_student_payment'),
]
