from rest_framework import serializers
from accounts.models import (
    User,
    Role,
    normalize_permissions,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from accounts.models import ADMIN_ROLE_ID
from django.conf import settings
from django.db import IntegrityError

NEW_MODULES = ("sales", "orders", "shipments", "certificates")
ACTIONS = ("view", "create", "edit", "delete", "assignRm")


class UserOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name"]


class CurrentUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.name", read_only=True)
    permissions = serializers.SerializerMethodField()
    mustChangePassword = serializers.BooleanField(
        source="must_change_password", read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "role",
            "permissions",
            "mustChangePassword",
        ]

    def get_permissions(self, obj):
        return obj.permissions_map


class UserListSerializer(serializers.ModelSerializer):
    roleId = serializers.CharField(source="role_id", read_only=True)
    roleName = serializers.CharField(source="role.name", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "roleId",
            "roleName",
            "status",
            "notes",
        ]

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"


class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255)  # no auto UniqueValidator
    roleId = serializers.CharField(write_only=True)
    status = serializers.ChoiceField(choices=["Active", "Inactive"], write_only=True)

    class Meta:
        model = User
        fields = ["id", "name", "email", "phone", "roleId", "status", "notes"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_roleId(self, value):
        try:
            exists = Role.objects.filter(id=value).exists()
        except (ValueError, TypeError, DjangoValidationError):
            exists = False
        if not exists:
            raise serializers.ValidationError("Role does not exist.")
        return value

    def create(self, validated_data):
        role_id = validated_data.pop("roleId")
        account_status = validated_data.pop("status")

        try:
            return User.objects.create_user(
                password=settings.DEFAULT_USER_PASSWORD,
                role_id=role_id,
                is_active=(account_status == "Active"),
                must_change_password=True,
                **validated_data,
            )
        except IntegrityError:
            # Lost the race on the unique email constraint
            raise serializers.ValidationError(
                {"email": ["A user with this email already exists."]}
            )


class UserUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        max_length=255, required=False
    )  # no auto UniqueValidator
    roleId = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=["Active", "Inactive"], required=False)

    class Meta:
        model = User
        fields = ["name", "email", "phone", "roleId", "status", "notes"]

    def validate_email(self, value):
        value = value.strip().lower()
        if (
            User.objects.filter(email__iexact=value)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_roleId(self, value):
        try:
            exists = Role.objects.filter(id=value).exists()
        except (ValueError, TypeError, DjangoValidationError):
            exists = False
        if not exists:
            raise serializers.ValidationError("Role does not exist.")
        return value

    def update(self, instance, validated_data):
        role_id = validated_data.pop("roleId", None)
        status_value = validated_data.pop("status", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if role_id is not None:
            instance.role_id = role_id

        if status_value is not None:
            instance.is_active = status_value == "Active"

        instance.save()
        return instance


class RoleOptionSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    usersCount = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "name", "permissions", "usersCount"]

    def get_permissions(self, obj):
        perms = {k: dict(v) for k, v in obj.effective_permissions.items()}
        for module in NEW_MODULES:
            if obj.pk == ADMIN_ROLE_ID:
                perms[module] = {a: True for a in ACTIONS}
            else:
                existing = perms.get(module, {})
                perms[module] = {a: bool(existing.get(a, False)) for a in ACTIONS}
        return perms

    def get_usersCount(self, obj):
        return getattr(obj, "users_count", None) or obj.users.count()


class RoleListSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    usersCount = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "status",
            "permissions",
            "usersCount",
        ]

    def get_permissions(self, obj):
        perms = obj.effective_permissions
        is_admin = obj.pk == ADMIN_ROLE_ID
        modules = set(perms) | set(NEW_MODULES)
        return {
            m: {a: is_admin or bool(perms.get(m, {}).get(a, False)) for a in ACTIONS}
            for m in modules
        }

    def get_usersCount(self, obj):
        count = getattr(obj, "users_count", None)
        return count if count is not None else obj.users.count()


class RoleCreateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=["Active", "Inactive"],
        required=False,
        default="Active",
    )
    permissions = serializers.JSONField()

    class Meta:
        model = Role
        fields = ["id", "name", "description", "status", "permissions"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        if Role.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("This role already exists.")
        return value

    def validate_permissions(self, value):
        return normalize_permissions(value)

    def create(self, validated_data):
        return Role.objects.create(**validated_data)


class RoleUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=["Active", "Inactive"],
        required=False,
    )
    permissions = serializers.JSONField(required=False)

    class Meta:
        model = Role
        fields = [
            "name",
            "description",
            "status",
            "permissions",
        ]

    def validate_name(self, value):
        queryset = Role.objects.filter(name__iexact=value).exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("This role already exists.")

        return value

    def validate_permissions(self, value):
        return normalize_permissions(value)

    def validate(self, attrs):
        # Admin role can never be deactivated.
        if self.instance.is_admin_role and attrs.get("status") == Role.Status.INACTIVE:
            raise serializers.ValidationError(
                {"status": ["The Admin role cannot be deactivated."]}
            )

        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    currentPassword = serializers.CharField(write_only=True, trim_whitespace=False)
    newPassword = serializers.CharField(
        write_only=True, min_length=8, max_length=128, trim_whitespace=False
    )
    confirmPassword = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["newPassword"] != attrs["confirmPassword"]:
            raise serializers.ValidationError(
                {"confirmPassword": ["Passwords do not match."]}
            )
        if attrs["newPassword"] == attrs["currentPassword"]:
            raise serializers.ValidationError(
                {
                    "newPassword": [
                        "New password must be different from the current one."
                    ]
                }
            )
        return attrs
