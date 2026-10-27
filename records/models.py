
from django.db import models


class Contact(models.Model):
    HELP_OPTIONS = [
        ('genetic_counselling', 'Genetic Counselling'),
        ('genetic_testing', 'Genetic Testing'),
        ('appointment_related_query', 'Appointment Related Query'),
        ('services_information', 'Services Information'),
        ('general_enquiry', 'General Enquiry'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    help_with = models.CharField(max_length=100, choices=HELP_OPTIONS)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Feedback(models.Model):
    FEEDBACK_ABOUT_OPTIONS = [
        ('consultation', 'Consultation'),
        ('communication', 'Communication'),
        ('appointment_process', 'Appointment Process'),
        ('website_experience', 'Website Experience'),
        ('information_provided', 'Information Provided'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    feedback_about = models.CharField(max_length=400)
    rating = models.IntegerField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or "Anonymous Feedback"


class Appointment(models.Model):

    RELATION_OPTIONS = [
        ('self', 'Self'),
        ('parent', 'Parent'),
        ('child', 'Child'),
        ('sibling', 'Sibling'),
        ('spouse', 'Spouse'),
        ('grandparent', 'Grandparent'),
        ('grandchild', 'Grandchild'),
        ('other_family_member', 'Other Family Member'),
        ('caregiver', 'Caregiver'),
        ('other', 'Other'),
    ]

    CONSULTATION_REASON_OPTIONS = [
        ('family_history_of_genetic_condition', 'Family History of Genetic Condition'),
        ('genetic_testing_guidance', 'Genetic Testing Guidance'),
        ('suspected_inherited_condition', 'Suspected Inherited Condition'),
        ('pregnancy', 'Pregnancy / Prenatal'),
        ('other', 'Other'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('not_required', 'Not Required'),
    ]

    APPOINTMENT_STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    age = models.PositiveIntegerField()

    relation = models.CharField(
        max_length=50,
        choices=RELATION_OPTIONS
    )

    reason_for_consultation = models.CharField(
        max_length=100,
        choices=CONSULTATION_REASON_OPTIONS
    )

    appointment_date = models.DateField()
    appointment_time = models.TimeField()

    # Payment and appointment status
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='not_required'
    )

    appointment_status = models.CharField(
        max_length=20,
        choices=APPOINTMENT_STATUS_CHOICES,
        default='confirmed'
    )

    # Temporary reservation expiry
    payment_expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Payment(models.Model):

    PAYMENT_STATUS_CHOICES = [
        ('created', 'Created'),
        ('authorized', 'Authorized'),
        ('captured', 'Captured'),
        ('failed', 'Failed'),
    ]

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.PROTECT,
        related_name='payments'
    )

    razorpay_order_id = models.CharField(
        max_length=100,
        unique=True
    )

    razorpay_payment_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    amount = models.PositiveIntegerField()

    currency = models.CharField(
        max_length=3,
        default='INR'
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='created'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.razorpay_order_id} - {self.status}"


class AppointmentReport(models.Model):

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='reports'
    )

    report = models.FileField(upload_to='appointment_reports/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.appointment.name} - {self.report.name}"


class AppointmentSlot(models.Model):

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    is_active = models.BooleanField(default=True)
    is_booked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ('date', 'start_time')

    def __str__(self):
        return f"{self.date} - {self.start_time} to {self.end_time}"


class HomePageContent(models.Model):

    image = models.ImageField(
        upload_to='homepage/',
        blank=True,
        null=True
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Home Page Image"

    class Meta:
        verbose_name = "Home Page Image"
        verbose_name_plural = "Home Page Image"