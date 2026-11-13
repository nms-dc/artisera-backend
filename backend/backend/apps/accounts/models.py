import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

# --------------------------------------------------------------------------
# Permission schema (single source of truth, mirrors the API spec: A01/R02)
# --------------------------------------------------------------------------
CRUD_ACTIONS = ("view", "create", "edit", "delete", "assignRm")

PERMISSION_SCHEMA = {
    "inquiries": CRUD_ACTIONS,
    "customers": CRUD_ACTIONS,
    "masters": CRUD_ACTIONS,
    "reports": ("view",),
    "users": CRUD_ACTIONS,
}

ADMIN_ROLE_ID = "ADMIN"
RM_ROLE_ID = "RM"

FULL_PERMISSIONS = {
    resource: {action: True for action in actions}
    for resource, actions in PERMISSION_SCHEMA.items()
}


def normalize_permissions(raw):
    """
    Return a clean permissions dict:
      - every resource key is present (R03 sends "users": {} for no access)
      - only known actions are kept
      - only True flags are stored (missing key == False, per A03 note)
    """
    raw = raw or {}
    clean = {}
    for resource, actions in PERMISSION_SCHEMA.items():
        given = raw.get(resource) or {}
        clean[resource] = {a: True for a in actions if given.get(a) is True}
    return clean


def new_role_id():
    # Custom roles get a UUID string; system roles use fixed ids 'ADMIN' / 'RM'.
    return str(uuid.uuid4())


# --------------------------------------------------------------------------
# Role
# --------------------------------------------------------------------------
class Role(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"

    # String PK so the API can expose 'ADMIN', 'RM' and UUIDs through one `id`.
    id = models.CharField(primary_key=True, max_length=64, default=new_role_id, editable=False)
    # Case-insensitive duplicates ("sales" vs "Sales") are rejected in the
    # serializer (name__iexact); the DB constraint covers the exact match.
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    permissions = models.JSONField(default=dict, blank=True)
    is_system = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_admin_role(self):
        return self.pk == ADMIN_ROLE_ID

    @property
    def effective_permissions(self):
        # Admin always has everything, whatever is stored (see R05 note).
        if self.is_admin_role:
            return FULL_PERMISSIONS
        return normalize_permissions(self.permissions)

    def save(self, *args, **kwargs):
        self.permissions = normalize_permissions(self.permissions)
        if self.is_admin_role:
            # R05: "The Admin role cannot be deactivated."
            self.status = self.Status.ACTIVE
            self.is_system = True
        super().save(*args, **kwargs)


# --------------------------------------------------------------------------
# User
# --------------------------------------------------------------------------
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("role_id", RM_ROLE_ID)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra["role_id"] = ADMIN_ROLE_ID
        extra["is_superuser"] = True
        return self._create(email, password, **extra)

    def options(self, role_id=None):
        """U01: active users only, optionally filtered by role."""
        qs = self.filter(is_active=True).order_by("name")
        return qs.filter(role_id=role_id) if role_id else qs


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, default="unknown")
    email = models.EmailField(max_length=255, unique=True)
    phone = models.CharField(max_length=20, blank=True, default="")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="users",default="RM")
    # API "status" ('Active'/'Inactive') maps to this boolean; see `status` below.
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    # --- API helpers ------------------------------------------------------
    @property
    def status(self):
        return Role.Status.ACTIVE if self.is_active else Role.Status.INACTIVE

    @status.setter
    def status(self, value):
        self.is_active = value == Role.Status.ACTIVE

    @property
    def role_name(self):
        return self.role.name

    @property
    def permissions_map(self):
        """Shape returned by A01 / A03."""
        return self.role.effective_permissions

    def can(self, resource, action):
        """Used by the DRF permission class: user.can('inquiries', 'assignRm')."""
        return bool(self.permissions_map.get(resource, {}).get(action))

    @property
    def is_admin(self):
        return self.role_id == ADMIN_ROLE_ID

    # --- Django admin -----------------------------------------------------
    @property
    def is_staff(self):
        return self.is_admin or self.is_superuser

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

class Address(models.Model):
    pass