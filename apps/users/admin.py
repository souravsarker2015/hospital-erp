from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ["username", "email", "hospital", "role", "is_active"]
    list_filter = ["role", "hospital", "is_active"]
    fieldsets = DjangoUserAdmin.fieldsets + (("Hospital ERP", {"fields": ("hospital", "role", "phone_number")}),)
