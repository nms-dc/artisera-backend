
from rest_framework import serializers
from accounts.models import (
    User,
    Role,
    normalize_permissions,
)


class UserOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name"]


class CurrentUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role_id", read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "role",
            "permissions",
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
    roleId = serializers.CharField(write_only=True)
    status = serializers.ChoiceField(
        choices=["Active", "Inactive"],
        write_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "roleId",
            "status",
            "notes",
        ]
        read_only_fields = ["id"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value

    def validate_roleId(self, value):
        from .models import Role

        if not Role.objects.filter(id=value).exists():
            raise serializers.ValidationError("Role does not exist.")
        return value

    def create(self, validated_data):
        role_id = validated_data.pop("roleId")
        status = validated_data.pop("status")

        user = User.objects.create_user(
            password=None,
            role_id=role_id,
            is_active=(status == "Active"),
            **validated_data
        )
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    roleId = serializers.CharField(required=False)
    status = serializers.ChoiceField(
        choices=["Active", "Inactive"],
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "name",
            "email",
            "phone",
            "roleId",
            "status",
            "notes",
        ]

    def validate_email(self, value):
        queryset = User.objects.filter(
            email__iexact=value
        ).exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return value

    def validate_roleId(self, value):
        from accounts.models import Role

        if not Role.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Role does not exist."
            )

        return value

    def update(self, instance, validated_data):
        role_id = validated_data.pop("roleId", None)
        status_value = validated_data.pop("status", None)

        # Update normal fields.
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update role only if supplied.
        if role_id is not None:
            instance.role_id = role_id

        # Update status only if supplied.
        if status_value is not None:
            instance.is_active = (
                status_value == "Active"
            )

        instance.save()
        return instance


class RoleOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]


class RoleListSerializer(serializers.ModelSerializer):
    usersCount = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "status",
            "usersCount",
            "permissions",
        ]

    def get_usersCount(self, obj):
        return obj.users.count()

    def get_permissions(self, obj):
        return obj.effective_permissions


class RoleCreateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=["Active", "Inactive"]
    )
    permissions = serializers.JSONField()

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "status",
            "permissions",
        ]
        read_only_fields = ["id"]

    def validate_name(self, value):
        if Role.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                "This role already exists."
            )
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
        queryset = Role.objects.filter(
            name__iexact=value
        ).exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "This role already exists."
            )

        return value

    def validate_permissions(self, value):
        return normalize_permissions(value)

    def validate(self, attrs):
        # Admin role can never be deactivated.
        if (
            self.instance.is_admin_role
            and attrs.get("status") == Role.Status.INACTIVE
        ):
            raise serializers.ValidationError({
                "status": [
                    "The Admin role cannot be deactivated."
                ]
            })

        return attrs

"""


CHABSONS OLD SERIALIZERS ARE HERE;
==================================

from rest_framework import serializers
from accounts.models import User, create_username, Image, DailyVisit
from product.models import Address
#from product.api.serializers import AddressSerializer


class UserImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Image
        fields = '__all__'


class UserRegistrationSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'phone_no', 'password', 'password2', 'first_name', 'last_name', 'is_terms_accepted' ,'is_verified','is_admin']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        username = create_username(self.validated_data['email'])
        user = User(
            email=self.validated_data['email'],
            username=username,
            phone_no=self.validated_data['phone_no'],
            first_name=self.validated_data['first_name'],
            last_name=self.validated_data['last_name'],
        )
        password = self.validated_data['password']
        password2 = self.validated_data['password2']

        if password != password2:
            raise serializers.ValidationError({'password': 'Passwords must match.'})
        user.set_password(password)
        user.save()
        return user
    
    # def update(self, instance, validated_data):
    #     print(validated_data['email'])
    #     user = User.objects.get(email=validated_data['email'])
    #     user.set_password(validated_data['password'])
    #     user.save()
    #     return user


class UserBasicInfoSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'email', 'phone_no', 'first_name', 'last_name', 'username', 'is_verified', "is_admin"]


class UserProfileInfoSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField(read_only=True)
    user_images = UserImageSerializer(many=True, read_only=True)
    #addresses = serializers.SerializerMethodField()

    def get_addresses(self,obj):
        address_data = Address.objects.filter(user=obj.id).values()
        #serialize = AddressSerializer(address_data, many=True).data
        return address_data

    class Meta:
        model = User
        fields = ['id', 'email', 'phone_no', 'first_name', 'last_name', 'username', 'company_name', 'user_images',
                  'sic_gst_code', 'pan_no', 'address_one', 'address_two', 'pincode', 'website', 'is_verified', 
                  'is_terms_accepted', "is_admin", 'city', 'country']

    def create(self, validated_data):
        image_data = self.context.get('view').request.FILES
        user_instance = User.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_no=validated_data['phone_no'],
            company_name=validated_data['company_name'],
            sic_gst_code=validated_data['sic_gst_code'],
            pan_no=validated_data['pan_no'],
            address_one=validated_data['address_one'],
            address_two=validated_data['address_two'],
            pincode=validated_data['pincode'],
            website=validated_data['website'],
            email=validated_data['email'],
            is_admin=validated_data['is_admin'],
            city=validated_data['city'],
            country=validated_data['country']
        )
        for data in image_data.getlist('user_images'):
            name = data.name
            Image.objects.create(images=user_instance, image_name=name, image=data)
            print(user_instance)
        return user_instance

    def update(self, instance, validated_data):
        image_data = self.context.get('view').request.FILES
        data = self.context['request'].data.get('user_images_id', None)
        '''#filtering 'pond_image_id' and converting it into an integer list'''
        int_Userimage_id = []
        if data:
            trim_image_id = data.replace('[', '').replace(']', '').replace(" ", "").split(',')
            for id in trim_image_id:
                int_Userimage_id.append(int(id))
        #print('cycle update validated data',validated_data)
        #print('image_data details',int_Userimage_id)        
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.phone_no = validated_data.get('phone_no', instance.phone_no)
        instance.company_name = validated_data.get('company_name', instance.company_name)
        instance.sic_gst_code = validated_data.get('sic_gst_code', instance.sic_gst_code)
        instance.pan_no = validated_data.get('pan_no', instance.pan_no)
        instance.address_one = validated_data.get('address_one', instance.address_one)
        instance.address_two = validated_data.get('address_two', instance.address_two)
        instance.pincode = validated_data.get('pincode', instance.pincode)
        instance.website = validated_data.get('website', instance.website)
        instance.email = validated_data.get('email', instance.email)
        instance.is_admin = validated_data.get('is_admin', instance.is_admin)
        instance.city = validated_data.get('city', instance.city)
        instance.country = validated_data.get('country', instance.country)
        instance.save()

        userimage_with_same_profile_instance = Image.objects.filter(images=instance.pk).values_list('id', flat=True)
        
        

        if len(image_data.getlist('user_images')) != 0:
            if userimage_with_same_profile_instance:
                for delete_id in userimage_with_same_profile_instance:
                        Image.objects.filter(pk=delete_id).delete()
            for image_data in image_data.getlist('user_images'):
                name = image_data.name
                Image.objects.create(images=instance, image_name=name, image=image_data)

        return instance
    
class DailyVisitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyVisit
        fields = ['count','date']

"""

