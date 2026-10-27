from django.urls import path
from . import views
from .views import (
    contact_submit,
    feedback_submit,
    appointment_submit,
    appointment_report_submit,
    create_order,
    verify_payment
)


urlpatterns = [

    path(
        "contact/",
        contact_submit,
        name="contact_submit"
    ),

    path(
        "feedback/",
        feedback_submit,
        name="feedback_submit"
    ),

    path(
        "appointment/",
        appointment_submit,
        name="appointment_submit"
    ),

    path(
        "appointment-report/",
        appointment_report_submit,
        name="appointment_report_submit"
    ),
    path(
        "appointment-slots/",
        views.get_appointment_slots,
        name='appointment-slots'
    ),

    path(
        "homepage-content/",
        views.get_homepage_content,
        name="homepage-content"
    ),
    path("create-order/", create_order, name="create_order"),
    path("verify-payment/", verify_payment, name="verify_payment"),
    path(
    "webhook/razorpay/",
    views.razorpay_webhook,
    name="razorpay_webhook"
),
    path(
    "payment-amount/",
    views.get_payment_amount,
    name="payment_amount"
),
]