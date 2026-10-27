from django.conf import settings
from django.utils import timezone
from .models import Payment
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from datetime import datetime, timedelta
import json
import razorpay

import hmac
import hashlib
import logging

from .models import (
    Contact,
    Feedback,
    Appointment,
    AppointmentReport,
    AppointmentSlot,
    Payment,
    HomePageContent
)

logger = logging.getLogger(__name__)
# =====================================================
# HELPER: CHECK SLOT OVERLAP
# =====================================================
def get_razorpay_client():

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise ValueError("Razorpay API keys are not configured.")

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    return client

def is_overlapping(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1


# HELPER: EXPIRE PENDING APPOINTMENTS AND RELEASE SLOTS


@transaction.atomic
def expire_pending_appointments():

    current_time = timezone.now()

    expired_appointments = Appointment.objects.select_for_update().filter(
        appointment_status="pending_payment",
        payment_expires_at__isnull=False,
        payment_expires_at__lte=current_time
    )

    for appointment in expired_appointments:

        # Safety check:captured payment ko expire nahi karnahai.
        captured_payment = Payment.objects.filter(
            appointment=appointment,
            status="captured"
        ).exists()

        if captured_payment:
            appointment.payment_status = "paid"
            appointment.appointment_status = "confirmed"
            appointment.payment_expires_at = None

            appointment.save(update_fields=[
                "payment_status",
                "appointment_status",
                "payment_expires_at"
            ])
            continue

        # Find the temporarily reserved slot.
        slot = AppointmentSlot.objects.select_for_update().filter(
            date=appointment.appointment_date,
            start_time=appointment.appointment_time,
            is_booked=True
        ).first()

        # Release the slot.
        if slot:
            slot.is_booked = False
            slot.save(update_fields=["is_booked"])

        # Mark appointment as expired.
        appointment.payment_status = "failed"
        appointment.appointment_status = "expired"
        appointment.payment_expires_at = None

        appointment.save(update_fields=[
            "payment_status",
            "appointment_status",
            "payment_expires_at"
        ])

# HELPER: EXPIRE PENDING APPOINTMENTS AND RELEASE SLOTS


@transaction.atomic
def expire_pending_appointments():

    current_time = timezone.now()

    expired_appointments = Appointment.objects.select_for_update().filter(
        appointment_status="pending_payment",
        payment_expires_at__isnull=False,
        payment_expires_at__lte=current_time
    )

    for appointment in expired_appointments:

        # Safety check: captured payment ko expire nahi karna.
        captured_payment = Payment.objects.filter(
            appointment=appointment,
            status="captured"
        ).exists()

        if captured_payment:
            appointment.payment_status = "paid"
            appointment.appointment_status = "confirmed"
            appointment.payment_expires_at = None

            appointment.save(update_fields=[
                "payment_status",
                "appointment_status",
                "payment_expires_at"
            ])
            continue

        # Find the temporarily reserved slot.
        slot = AppointmentSlot.objects.select_for_update().filter(
            date=appointment.appointment_date,
            start_time=appointment.appointment_time,
            is_booked=True
        ).first()

        # Release the slot.
        if slot:
            slot.is_booked = False
            slot.save(update_fields=["is_booked"])

        # Mark appointment as expired.
        appointment.payment_status = "failed"
        appointment.appointment_status = "expired"
        appointment.payment_expires_at = None

        appointment.save(update_fields=[
            "payment_status",
            "appointment_status",
            "payment_expires_at"
        ])


# =====================================================
# CONTACT
# =====================================================

@csrf_exempt
def contact_submit(request):

    if request.method == "POST":

        try:
            data = json.loads(request.body)

            contact = Contact.objects.create(
                name=data.get("name"),
                email=data.get("email"),
                mobile=data.get("mobile"),
                help_with=data.get("help_with"),
                message=data.get("message"),
            )

            return JsonResponse({
                "message": "Contact submitted successfully",
                "id": contact.id
            })

        except Exception as e:
            return JsonResponse({
                "error": str(e)
            }, status=400)

    return JsonResponse(
        {"error": "Only POST method allowed"},
        status=405
    )


# =====================================================
# FEEDBACK
# =====================================================

@csrf_exempt
def feedback_submit(request):

    if request.method == "POST":

        try:
            data = json.loads(request.body)

            categories = data.get("categories", [])

            feedback = Feedback.objects.create(
                name=data.get("name") or None,
                email=data.get("email") or None,
                feedback_about=", ".join(categories),
                rating=data.get("rating"),
                message=data.get("message"),
            )

            return JsonResponse({
                "message": "Feedback submitted successfully",
                "id": feedback.id
            })

        except Exception as e:
            print("FEEDBACK ERROR:", str(e))

            return JsonResponse({
                "error": str(e)
            }, status=400)

    return JsonResponse(
        {"error": "Only POST method allowed"},
        status=405
    )


# GET AVAILABLE APPOINTMENT SLOTS
@require_GET
def get_appointment_slots(request):
    # Expire old pending appointments and release their slots.
    expire_pending_appointments()
    today = timezone.localdate()
    current_time = timezone.localtime().time()

    slots = AppointmentSlot.objects.filter(
        is_active=True,
        is_booked=False,
        date__gte=today
    ).order_by('date', 'start_time')

    available_slots = []

    for slot in slots:

        # Aaj ke past-time slots ko skip karo
        if slot.date == today and slot.start_time <= current_time:
            continue

        # Booked slots ke saath overlapping slots check karo
        booked_slots = AppointmentSlot.objects.filter(
            date=slot.date,
            is_booked=True
        )

        is_overlapping = False

        for booked in booked_slots:

            if (
                slot.start_time < booked.end_time
                and slot.end_time > booked.start_time
            ):
                is_overlapping = True
                break

        if is_overlapping:
            continue

        available_slots.append({
            "id": slot.id,
            "date": slot.date.strftime("%Y-%m-%d"),
            "start_time": slot.start_time.strftime("%H:%M:%S"),
            "end_time": slot.end_time.strftime("%H:%M:%S"),
        })

    return JsonResponse({
        "slots": available_slots
    })


# =====================================================
# APPOINTMENT BOOKING
# =====================================================

@csrf_exempt
@transaction.atomic
def appointment_submit(request):

    if request.method != "POST":

        return JsonResponse(
            {"error": "Only POST method allowed"},
            status=405
        )

    try:
        data = json.loads(request.body)
        expire_pending_appointments()

        slot_id = data.get("slot_id")

        if not slot_id:
            return JsonResponse({
                "error": "Appointment slot is required"
            }, status=400)

        # Get selected slot
        try:
            initial_slot = AppointmentSlot.objects.get(
                id=slot_id
            )

        except AppointmentSlot.DoesNotExist:

            return JsonResponse({
                "error": "Invalid appointment slot"
            }, status=400)

        today = timezone.localdate()
        current_time = timezone.localtime().time()

        # Lock all slots for the selected date
        locked_slots = list(
            AppointmentSlot.objects.select_for_update().filter(
                date=initial_slot.date
            ).order_by('start_time')
        )

        # Find selected slot from locked records
        slot = next(
            (
                s for s in locked_slots
                if s.id == initial_slot.id
            ),
            None
        )

        if (
            slot is None
            or not slot.is_active
            or slot.is_booked
            or slot.date < today
        ):

            return JsonResponse({
                "error": "This appointment slot is no longer available."
            }, status=400)

        # Prevent past-time booking
        if (
            slot.date == today
            and slot.start_time <= current_time
        ):

            return JsonResponse({
                "error": "This appointment time has already passed."
            }, status=400)

        # Selected slot start and end time
        selected_start = datetime.combine(
            slot.date,
            slot.start_time
        )

        selected_end = datetime.combine(
            slot.date,
            slot.end_time
        )

        # Check overlapping booked slots
        for booked in locked_slots:

            if booked.is_booked:

                booked_start = datetime.combine(
                    booked.date,
                    booked.start_time
                )

                booked_end = datetime.combine(
                    booked.date,
                    booked.end_time
                )

                if is_overlapping(
                    selected_start,
                    selected_end,
                    booked_start,
                    booked_end
                ):

                    return JsonResponse({
                        "error": "This time overlaps with another appointment."
                    }, status=400)

        # Check overlapping existing appointments
        existing_appointments = Appointment.objects.filter(
    appointment_date=slot.date,
    appointment_status__in=[
        "pending_payment",
        "confirmed"
    ]
).values_list('appointment_time', flat=True)
        for booked_time in existing_appointments:

            booked_start = datetime.combine(
                slot.date,
                booked_time
            )

            booked_end = booked_start + timedelta(hours=1)

            if is_overlapping(
                selected_start,
                selected_end,
                booked_start,
                booked_end
            ):

                return JsonResponse({
                    "error": "This time overlaps with another appointment."
                }, status=400)

        # Create appointment
        appointment = Appointment.objects.create(
           name=data.get("name"),
           email=data.get("email"),
           mobile=data.get("mobile"),
           age=data.get("age"),
           relation=data.get("relation"),
           reason_for_consultation=data.get("reason_for_consultation"),
           appointment_date=slot.date,
           appointment_time=slot.start_time,

           payment_status="pending",
           appointment_status="pending_payment",
           payment_expires_at=timezone.now() + timedelta(minutes=10),
        )
        # Mark selected slot as booked
        slot.is_booked = True

        slot.save(
            update_fields=['is_booked']
        )

        return JsonResponse({
            "message": "Appointment booked successfully!",
            "appointment_id": appointment.id
        })

    except (ValueError, TypeError, json.JSONDecodeError):

        return JsonResponse({
            "error": "Invalid appointment data."
        }, status=400)

    except Exception as e:

        print("APPOINTMENT ERROR:", str(e))

        return JsonResponse({
            "error": "Something went wrong while booking your appointment."
        }, status=500)


# =====================================================
# APPOINTMENT REPORT
# =====================================================

@csrf_exempt
def appointment_report_submit(request):

    if request.method == "POST":

        appointment_id = request.POST.get("appointment_id")
        report_file = request.FILES.get("report")

        if not appointment_id:

            return JsonResponse(
                {"error": "Appointment ID is required"},
                status=400
            )

        if not report_file:

            return JsonResponse(
                {"error": "Report file is required"},
                status=400
            )

        try:
            appointment = Appointment.objects.get(
                id=appointment_id
            )

        except Appointment.DoesNotExist:

            return JsonResponse(
                {"error": "Appointment not found"},
                status=404
            )

        report = AppointmentReport.objects.create(
            appointment=appointment,
            report=report_file
        )

        return JsonResponse({
            "message": "Report uploaded successfully",
            "id": report.id,
            "appointment_id": appointment.id
        })

    return JsonResponse(
        {"error": "Only POST method allowed"},
        status=405
    )

@csrf_exempt
@transaction.atomic
def create_order(request):

    if request.method != "POST":
        return JsonResponse(
            {"error": "Only POST method allowed"},
            status=405
        )

    try:
        
        data = json.loads(request.body)

        expire_pending_appointments()

        appointment_id = data.get("appointment_id")

       
        if not appointment_id:
            return JsonResponse(
                {"error": "Appointment ID is required"},
                status=400
            )

        # Lock appointment to avoid duplicate order creation
        try:
            appointment = Appointment.objects.select_for_update().get(
                id=appointment_id
            )
        except Appointment.DoesNotExist:
            return JsonResponse(
                {"error": "Appointment not found"},
                status=404
            )

        # Check appointment status
        if appointment.appointment_status != "pending_payment":
            return JsonResponse(
                {"error": "Appointment is not pending payment"},
                status=400
            )

        if appointment.payment_status == "paid":
            return JsonResponse(
                {"error": "Payment is already completed"},
                status=400
            )

        # Check payment expiry
        if (
            not appointment.payment_expires_at
            or appointment.payment_expires_at <= timezone.now()
        ):
            return JsonResponse(
                {"error": "Appointment payment session has expired"},
                status=400
            )

        # Reuse an existing created order if one exists
        existing_payment = Payment.objects.filter(
            appointment=appointment,
            status="created"
        ).first()

        if existing_payment:
            return JsonResponse({
                "message": "Existing payment order found",
                "key_id": settings.RAZORPAY_KEY_ID,
                "order_id": existing_payment.razorpay_order_id,
                "amount": existing_payment.amount,
                "currency": existing_payment.currency,
                "appointment_id": appointment.id
            })

        # Amount is controlled by backend settings
        amount = settings.CONSULTATION_FEE_PAISE

        if amount < 100:
            return JsonResponse(
                {"error": "Consultation fee must be at least ₹1"},
                status=400
            )

        # Initialize Razorpay client
        client = get_razorpay_client()

        # Create Razorpay order
        order_data = {
            "amount": amount,
            "currency": "INR",
            "receipt": f"GC-{appointment.id}",
            "notes": {
                "appointment_id": str(appointment.id),
                "customer_name": appointment.name
            }
        }

        razorpay_order = client.order.create(data=order_data)

        # Save payment details in database
        payment = Payment.objects.create(
            appointment=appointment,
            razorpay_order_id=razorpay_order["id"],
            amount=amount,
            currency="INR",
            status="created"
        )

        return JsonResponse({
            "message": "Razorpay order created successfully",
            "key_id": settings.RAZORPAY_KEY_ID,
            "order_id": payment.razorpay_order_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "appointment_id": appointment.id
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON data"},
            status=400
        )

    except Exception as e:
        print("RAZORPAY ORDER ERROR:", str(e))

        return JsonResponse(
            {"error": "Unable to create payment order"},
            status=500
        )


@require_GET
def get_payment_amount(request):
    amount = settings.CONSULTATION_FEE_PAISE

    return JsonResponse({
        "amount": amount,
        "currency": "INR"
    })

# HOMEPAGE IMAGE API


@require_GET
def get_homepage_content(request):

    content = HomePageContent.objects.first()

    if not content or not content.image:
        return JsonResponse({
            "image": None
        })

    return JsonResponse({
        "image": request.build_absolute_uri(
            content.image.url
        )
    })


@csrf_exempt
@transaction.atomic
def verify_payment(request):

    if request.method != "POST":
        return JsonResponse(
            {"error": "Only POST method allowed"},
            status=405
        )

    try:
        data = json.loads(request.body)

        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_signature = data.get("razorpay_signature")

        if not all([
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature
        ]):
            return JsonResponse(
                {"error": "Payment verification details are required"},
                status=400
            )

        # Find payment using our saved Razorpay order ID
        try:
            payment = Payment.objects.select_for_update().get(
                razorpay_order_id=razorpay_order_id
            )
        except Payment.DoesNotExist:
            return JsonResponse(
                {"error": "Payment order not found"},
                status=404
            )

        appointment = Appointment.objects.select_for_update().get(
            id=payment.appointment_id
        )

        # Prevent duplicate verification
        if payment.status == "captured":
            return JsonResponse({
                "message": "Payment already verified",
                "payment_status": "paid",
                "appointment_status": appointment.appointment_status
            })

        client = get_razorpay_client()

        # Verify Razorpay signature
        client.utility.verify_payment_signature({
            "razorpay_order_id": payment.razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })

        # Fetch actual payment details from Razorpay
        razorpay_payment = client.payment.fetch(
            razorpay_payment_id
        )

        # Verify payment belongs to our saved order
        if razorpay_payment.get("order_id") != payment.razorpay_order_id:
            return JsonResponse(
                {"error": "Payment does not belong to this order"},
                status=400
            )

        # Verify amount and currency
        if (
            razorpay_payment.get("amount") != payment.amount
            or razorpay_payment.get("currency") != payment.currency
        ):
            return JsonResponse(
                {"error": "Payment amount or currency mismatch"},
                status=400
            )

        # Only captured payments can confirm appointments
        if razorpay_payment.get("status") != "captured":
            return JsonResponse({
                "message": "Payment is not captured yet",
                "payment_status": razorpay_payment.get("status")
            }, status=202)

        # Update Payment record
        payment.razorpay_payment_id = razorpay_payment_id
        payment.status = "captured"
        payment.save(update_fields=[
            "razorpay_payment_id",
            "status",
            "updated_at"
        ])

        # Confirm appointment
        appointment.payment_status = "paid"
        appointment.appointment_status = "confirmed"
        appointment.payment_expires_at = None

        appointment.save(update_fields=[
            "payment_status",
            "appointment_status",
            "payment_expires_at"
        ])

        return JsonResponse({
            "message": "Payment verified successfully",
            "payment_status": "paid",
            "appointment_status": "confirmed",
            "appointment_id": appointment.id
        })

    except razorpay.errors.SignatureVerificationError:
        return JsonResponse(
            {"error": "Invalid payment signature"},
            status=400
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON data"},
            status=400
        )

    except Exception as e:
        print("PAYMENT VERIFICATION ERROR:", str(e))

        return JsonResponse(
            {"error": "Unable to verify payment"},
            status=500
        )
@csrf_exempt
@require_POST
@transaction.atomic
def razorpay_webhook(request):

    # 1. Verify webhook signature using the RAW request body.
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    received_signature = request.headers.get("X-Razorpay-Signature")

    if not webhook_secret or not received_signature:
        return JsonResponse({"error": "Webhook configuration missing"}, status=400)

    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        request.body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, received_signature):
        return JsonResponse({"error": "Invalid webhook signature"}, status=400)

    # 2. Parse payload only after signature verification.
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    event = payload.get("event")

    if event not in ["payment.captured", "payment.failed"]:
        return JsonResponse({"status": "event ignored"}, status=200)

    payment_entity = (
        payload.get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")
    amount = payment_entity.get("amount")
    currency = payment_entity.get("currency")

    if not all([order_id, payment_id, amount, currency]):
        return JsonResponse({"error": "Incomplete payment data"}, status=400)

    # 3. Find and lock our saved payment.
    try:
        payment = Payment.objects.select_for_update().select_related(
            "appointment"
        ).get(razorpay_order_id=order_id)
    except Payment.DoesNotExist:
        logger.warning("Webhook received for unknown order: %s", order_id)
        return JsonResponse({"status": "unknown order ignored"}, status=200)

    appointment = Appointment.objects.select_for_update().get(
        id=payment.appointment_id
    )

    # 4. Verify amount and currency against our database.
    if int(amount) != payment.amount or currency != payment.currency:
        logger.error("Webhook amount/currency mismatch for order %s", order_id)
        return JsonResponse({"error": "Payment details mismatch"}, status=400)

    # 5. Handle successful payment.
    if event == "payment.captured":

        # Duplicate captured events must not change the result.
        if payment.status == "captured":
            return JsonResponse({"status": "already processed"}, status=200)

        payment.status = "captured"
        payment.razorpay_payment_id = payment_id
        payment.save(update_fields=[
            "status",
            "razorpay_payment_id",
            "updated_at"
        ])

        appointment.payment_status = "paid"

        # Confirm only if the original appointment is still valid
        # and its reserved slot has not been released.
        slot_is_reserved = AppointmentSlot.objects.filter(
            date=appointment.appointment_date,
            start_time=appointment.appointment_time,
            is_booked=True
        ).exists()

        appointment_is_valid = (
            appointment.appointment_status == "pending_payment"
            and appointment.payment_expires_at is not None
            and appointment.payment_expires_at > timezone.now()
            and slot_is_reserved
        )

        if appointment_is_valid:
            appointment.appointment_status = "confirmed"
            appointment.payment_expires_at = None
        elif appointment.appointment_status == "confirmed":
            # Already confirmed by the frontend verification callback.
            appointment.payment_expires_at = None
        else:
            # Payment captured, but appointment can no longer be confirmed.
            # Admin must review this payment for a refund/rescheduling.
            logger.critical(
                "Captured payment needs manual review. Appointment ID: %s, Order ID: %s",
                appointment.id,
                order_id
            )

        appointment.save(update_fields=[
            "payment_status",
            "appointment_status",
            "payment_expires_at"
        ])

        return JsonResponse({"status": "payment captured"}, status=200)

    # 6. Handle failed payment attempt.
    if event == "payment.failed":

        # A late failure event must never downgrade a captured payment.
        if payment.status != "captured":
            payment.status = "failed"
            payment.save(update_fields=["status", "updated_at"])

        # Keep appointment pending until its 10-minute expiry.
        # Another payment attempt can be made during this period.
        return JsonResponse({"status": "payment failure recorded"}, status=200)