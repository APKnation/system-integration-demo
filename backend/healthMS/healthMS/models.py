class Patient(models.Model):
    patient_number = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20)

    class LabRequest(models.Model):
    request_id = models.UUIDField(default=uuid.uuid4, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    test_code = models.CharField(max_length=50)
    test_name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=30,
        default="PENDING"
    )
    requested_at = models.DateTimeField(auto_now_add=True)