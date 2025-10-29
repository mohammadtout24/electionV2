from django.db import models
from django.contrib.auth.models import User # Use default Django User
from ckeditor.fields import RichTextField

# 1. New Model for User Profile (to store extra fields like phone number)
class UserProfile(models.Model):
    # One-to-one link to the default Django User model
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Field to store the phone number
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="رقم الهاتف")

    def __str__(self):
        return f"Profile for {self.user.username}"


# 2. Candidate model uses the default User
class Candidate(models.Model):
    user = models.OneToOneField(
        User,  # Use default User model
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Linked User Account",
        help_text="User account for the candidate to manage their profile."
    )

    name = models.CharField(max_length=100, default="Unknown Candidate")
    party = models.CharField(max_length=100, default="Independent")
    
    # ✅ ADD THIS NEW FIELD: topic
    topic = models.CharField(max_length=100, default="General Topic", verbose_name="Main Topic") 
    
    description = RichTextField(blank=True, verbose_name="Biography/Bio", default=" محتوى السيرة الذاتية هنا...")
    image = models.ImageField(upload_to='candidates/', blank=True, null=True)
    
    # You had this field before, but since we are focusing on users (not candidates)
    # in the new table, I'm removing it from Candidate to avoid confusion.
    # phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Phone Number") 

    def __str__(self):
        return f"{self.name} ({self.party})"


# 3. Vote model uses the default User
class Vote(models.Model):
    candidate = models.ForeignKey('Candidate', on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    voted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vote for {self.candidate.name} by {self.user.username if self.user else 'Anon'}"