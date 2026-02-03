from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        # Use email as username if not provided
        if not extra_fields.get('username'):
            extra_fields['username'] = email
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    gamer_tag = models.CharField(max_length=50, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    county = models.CharField(max_length=100, null=True, blank=True)

    # Use email for login instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['gamer_tag', 'phone_number', 'full_name', 'county']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.gamer_tag or self.email} ({self.full_name or 'No Name'})"

class PersonalProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    rank = models.IntegerField(default=0)
    total_kills = models.IntegerField(default=0)
    total_xp = models.IntegerField(default=0)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    deaths = models.IntegerField(default=0)
    def __str__(self):
        return f"Profile of {self.user.gamer_tag}"
