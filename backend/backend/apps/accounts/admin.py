from django import forms
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Count

from .models import PERMISSION_SCHEMA, Role, User


class UserCreationForm(forms.ModelForm):
    """Create a user with a repeated password (hashed on save)."""
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "name", "phone", "role")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Django's built-in change form is used (it shows the password hash
    # read-only with the "change password" link), so no custom change form.
    add_form = UserCreationForm

    list_display = ("email", "name", "role", "phone", "is_active", "created_at")
    list_filter = ("role", "is_active")
    list_select_related = ("role",)
    search_fields = ("email", "name", "phone")
    ordering = ("name",)
    readonly_fields = ("id", "last_login", "created_at", "updated_at")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal info", {"fields": ("name", "phone", "notes")}),
        ("Access", {"fields": ("role", "is_active", "is_superuser")}),
        ("Django permissions (rarely needed)", {
            "classes": ("collapse",),
            "fields": ("groups", "user_permissions"),
        }),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    # add_fieldsets is used by BaseUserAdmin.get_fieldsets when creating a user.
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "phone", "role", "password1", "password2"),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "status", "is_system", "users_count", "updated_at")
    list_filter = ("status", "is_system")
    search_fields = ("name", "description")
    readonly_fields = ("id", "is_system", "created_at", "updated_at")
    fields = ("id", "name", "description", "status", "permissions", "is_system",
              "created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_users_count=Count("users"))

    @admin.display(description="Users", ordering="_users_count")
    def users_count(self, obj):
        return obj._users_count

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        keys = ", ".join(f"{r}: {'/'.join(a)}" for r, a in PERMISSION_SCHEMA.items())
        form.base_fields["permissions"].help_text = (
            'JSON, e.g. {"inquiries": {"view": true, "create": true}, "users": {}}. '
            f"Allowed keys - {keys}. Unknown keys are dropped on save."
        )
        return form

    def has_delete_permission(self, request, obj=None):
        # System roles (ADMIN, RM) can never be deleted.
        if obj is not None and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)


# We don't use Django's Group-based permissions; roles replace them.
try:
    admin.site.unregister(Group)
except NotRegistered:
    pass