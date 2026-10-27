from rest_framework import serializers
from .models import (
    Contact,
    Feedback,
    Appointment,
    AppointmentReport
)


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = "__all__"


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = "__all__"


class AppointmentReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentReport
        fields = "__all__"