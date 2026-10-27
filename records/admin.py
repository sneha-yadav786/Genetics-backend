from django.contrib import admin
from .models import Contact, Feedback, Appointment, AppointmentReport, AppointmentSlot
from django.utils.html import format_html
from .models import HomePageContent
# ================= CONTACT =================

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'email',
        'mobile',
        'help_with',
        'message',
        'created_at',
    )

    list_filter = (
        'help_with',
        'created_at',
    )

    search_fields = (
        'name',
        'email',
        'mobile',
        'message',
    )


# ================= FEEDBACK =================

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'email',
        'feedback_about',
        'rating',
        'message',
        'created_at',
    )

    list_filter = (
        'feedback_about',
        'rating',
        'created_at',
    )

    search_fields = (
        'name',
        'email',
        'message',
    )


# ================= APPOINTMENT =================

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'email',
        'mobile',
        'age',
        'relation',
        'reason_for_consultation',
        'appointment_date',
        'appointment_time',
        'created_at',
    )

    list_filter = (
        'relation',
        'reason_for_consultation',
        'appointment_date',
        'created_at',
    )

    search_fields = (
        'name',
        'email',
        'mobile',
    )


# ================= APPOINTMENT REPORT =================


@admin.register(AppointmentReport)
class AppointmentReportAdmin(admin.ModelAdmin):

    list_display = (
        'appointment',
        'email',
        'report',
        'view_report',
        'download_report',
        'uploaded_at',
    )

    list_filter = (
        'uploaded_at',
    )

    search_fields = (
        'appointment__name',
        'appointment__email',
        'appointment__mobile',
    )

    @admin.display(description='Email')
    def email(self, obj):
        return obj.appointment.email

    @admin.display(description='View')
    def view_report(self, obj):
        if obj.report:
            return format_html(
                '<a href="{}" target="_blank">View</a>',
                obj.report.url
            )
        return '-'

    @admin.display(description='Download')
    def download_report(self, obj):
        if obj.report:
            return format_html(
                '<a href="{}" download>Download</a>',
                obj.report.url
            )
        return '-'
@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):

    list_display = (
        'date',
        'start_time',
        'end_time',
        'is_active',
        'is_booked',
    )

    list_filter = (
        'date',
        'is_active',
        'is_booked',
    )

    list_editable = (
        'is_active',
    )

    ordering = ('date', 'start_time')

    fields = (
        'date',
        'start_time',
        'end_time',
        'is_active',
        'is_booked',
    )


@admin.register(HomePageContent)
class HomePageContentAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return not HomePageContent.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False