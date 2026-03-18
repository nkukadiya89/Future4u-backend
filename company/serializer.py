import random
import re

from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from activity_log.models import ActivityLog
from company.models import Attachment, Company, CompanyEmail, KeyPersons
from user.models import CustomGroup, EmailPhoneVerify, User
from utils.generate_ip_address import get_client_ip
from utils.generate_random_password import generate_random_password


class CompanyKeyPersonsSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", required=False)
    contact_number = serializers.IntegerField(required=False)
    person_name = serializers.CharField(required=False)
    designation = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    class Meta:
        model = KeyPersons
        fields = [
            "id",
            "company",
            "company_name",
            "person_name",
            "designation",
            "email",
            "contact_number",
            "department",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def validate(self, data):
        email = data.get("email")
        if self.instance and self.instance.email == email:
            return data

        if KeyPersons.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                {"message": f"KeyPersons with this Email {email} already exists."}
            )

        contact_number = data.get("contact_number")
        if self.instance and self.instance.contact_number == contact_number:
            return data
        if KeyPersons.objects.filter(contact_number=contact_number).exists():
            raise serializers.ValidationError(
                {
                    "message": (
                        f"Keypersons with this Emergency contact {contact_number} "
                        "already exists."
                    )
                }
            )

        return data


class CompanyEmailSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", required=False)
    phone_number = serializers.IntegerField(required=False)
    person_name = serializers.CharField(required=False)
    designation = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    class Meta:
        model = CompanyEmail
        fields = [
            "id",
            "company",
            "company_name",
            "person_name",
            "designation",
            "email",
            "phone_number",
            "created_by",
            "updated_by",
        ]

        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def validate(self, data):
        email = data.get("email")
        if self.instance and self.instance.email == email:
            return data

        if CompanyEmail.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                {"message": f"CompanyEmail with this Email {email} already exists."}
            )

        phone_number = data.get("phone_number")
        if self.instance and self.instance.phone_number == phone_number:
            return data

        if CompanyEmail.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError(
                {
                    "message": (
                        f"CompanyEmail with this Phone Number {phone_number} "
                        "already exists."
                    )
                }
            )

        return data


class CompanySerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    unique_code = serializers.IntegerField(read_only=True, required=False)
    phone = serializers.IntegerField()
    sector_name = serializers.CharField(source="sector.sector_name", required=False)
    company_logo = serializers.CharField(required=False)
    keypersons = serializers.ListField(required=False)
    company_email = serializers.ListField(required=False)
    attachment = serializers.ListField(required=False)
    registered_business_address_pincode_number = serializers.CharField(
        source="registered_business_address_pincode.pincode_number", required=False
    )
    trading_address_pincode_number = serializers.CharField(
        source="trading_address_pincode.pincode_number", required=False
    )

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "first_name",
            "designation",
            "website",
            "no_of_employees",
            "company_pan",
            "company_pan_verified",
            "gst_no",
            "gst_no_verified",
            "about_company",
            "email",
            "phone",
            "password",
            "status",
            "is_active",
            "unique_code",
            "cin_no",
            "sector",
            "sector_name",
            "company_logo",
            "risk_and_compliance_title",
            "udhyam_aadharcard",
            "udhyam_aadharcard_verified",
            "registered_business_address_building",
            "registered_business_address_area",
            "registered_business_address_landmark",
            "registered_business_address_state",
            "registered_business_address_city",
            "registered_business_address_pincode",
            "registered_business_address_pincode_number",
            "trading_address_building",
            "trading_address_area",
            "trading_address_landmark",
            "trading_address_state",
            "trading_address_city",
            "trading_address_pincode",
            "trading_address_pincode_number",
            "created_by",
            "updated_by",
            "keypersons",
            "company_email",
            "attachment",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def validate(self, data):
        name = data.get("name")
        if self.instance and self.instance.name == name:
            return data
        if Company.objects.filter(name=name).exists():
            raise ValidationError(f"Company with this Name {name} already exists.")

        email = data.get("email")
        if self.instance and self.instance.email == email:
            return data
        if (
            Company.objects.filter(email=email).exists()
            or User.objects.filter(email=email).exists()
        ):
            raise ValidationError(f"Company with this Email {email} already exists.")

        phone = data.get("phone")
        if self.instance and self.instance.phone == phone:
            return data
        if (
            Company.objects.filter(phone=phone).exists()
            or User.objects.filter(phone=phone).exists()
        ):
            raise ValidationError(f"Company with this Phone {phone} already exists.")

        company_pan = data.get("company_pan")
        if company_pan is not None:
            if self.instance and self.instance.company_pan == company_pan:
                return data
            if Company.objects.filter(company_pan=company_pan).exists():
                raise ValidationError(
                    f"Company with this Pancard Number {company_pan} already exists."
                )

        gst_no = data.get("gst_no")
        if self.instance and self.instance.gst_no == gst_no:
            return data
        if Company.objects.filter(gst_no=gst_no).exists():
            raise ValidationError(
                f"Company with this GST Number {gst_no} already exists."
            )

        cin_no = data.get("cin_no")
        if self.instance and self.instance.cin_no == cin_no:
            return data
        if Company.objects.filter(cin_no=cin_no).exists():
            raise ValidationError(
                f"Company with this CIN Number {cin_no} already exists."
            )

        return data

    def create(self, validated_data):
        req = self.context.get("request")
        ip_address = get_client_ip(req)
        keypersons_data = validated_data.pop("keypersons", [])
        company_email_data = validated_data.pop("company_email", [])
        password = validated_data.pop("password", None)

        if not password:
            password = generate_random_password(self)

        unique_code = validated_data.pop("unique_code", None)
        if not unique_code:
            unique_code = str(random.randint(100000, 999999))

            if not Company.objects.filter(unique_code=unique_code).exists():
                validated_data["unique_code"] = unique_code

        phone = str(validated_data.get("phone", "")).strip()
        phone = re.sub(r"^(?:\+91|91)", "", phone)
        if not phone.isdigit() or len(phone) != 10:
            raise serializers.ValidationError(
                {
                    "success": False,
                    "message": "Please enter a valid 10-digit mobile number.",
                }
            )

        user_data = {
            "first_name": validated_data["first_name"],
            "designation": validated_data["designation"],
            "email": validated_data["email"],
            "phone": validated_data["phone"],
            "status": "pending",
        }

        user = User.objects.create(**user_data)
        user.set_password(password)
        company_instance = Company.objects.create(user=user, **validated_data)
        user.company_id = company_instance.id  # type: ignore
        try:
            company_admin_group = CustomGroup.objects.get(name="Company Admin")
            company_admin_group.user_set.add(user)
            user.role = company_admin_group.id  # type: ignore
        except CustomGroup.DoesNotExist:
            raise serializers.ValidationError(
                {"success": False, "message": "Company Admin group not found"}
            )

        ActivityLog.log.company_create(company_instance, ip_address, user)
        user.save()

        keyperson_instances = []
        if keypersons_data:
            for keyperson_data in keypersons_data:
                keyperson_data["company_id"] = company_instance.id  # type: ignore
                keyperson_instance = KeyPersons.objects.create(**keyperson_data)
                keyperson_instances.append(keyperson_instance)

        company_email_instances = []
        if company_email_data:
            for company_emails_data in company_email_data:
                company_emails_data["company_id"] = company_instance.id  # type: ignore
                company_emails_instance = CompanyEmail.objects.create(
                    **company_emails_data
                )
                company_email_instances.append(company_emails_instance)

        return company_instance

    def update(self, instance, validated_data):
        req = self.context.get("request")

        phone = str(validated_data.get("phone", "")).strip()

        phone = re.sub(r"^(?:\+91|91)", "", phone)

        if not phone.isdigit() or len(phone) != 10:
            raise serializers.ValidationError(
                {"phone": "Please enter a valid 10-digit mobile number."}
            )

        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.designation = validated_data.get("designation", instance.designation)
        instance.email = validated_data.get("email", instance.email)
        instance.phone = validated_data.get("phone", instance.phone)
        instance.name = validated_data.get("name", instance.name)
        instance.website = validated_data.get("website", instance.website)
        instance.no_of_employees = validated_data.get(
            "no_of_employees", instance.no_of_employees
        )
        instance.company_pan = validated_data.get("company_pan", instance.company_pan)
        instance.company_pan_verified = validated_data.get(
            "company_pan_verified", instance.company_pan_verified
        )
        instance.gst_no = validated_data.get("gst_no", instance.gst_no)
        instance.about_company = validated_data.get(
            "about_company", instance.about_company
        )
        instance.status = validated_data.get("status", instance.status)
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.cin_no = validated_data.get("cin_no", instance.cin_no)
        instance.sector = validated_data.get("sector", instance.sector)
        instance.company_logo = validated_data.get(
            "company_logo", instance.company_logo
        )
        instance.risk_and_compliance_title = validated_data.get(
            "risk_and_compliance_title", instance.risk_and_compliance_title
        )
        instance.udhyam_aadharcard = validated_data.get(
            "udhyam_aadharcard", instance.udhyam_aadharcard
        )
        instance.registered_business_address_building = validated_data.get(
            "registered_business_address_building",
            instance.registered_business_address_building,
        )
        instance.registered_business_address_area = validated_data.get(
            "registered_business_address_area",
            instance.registered_business_address_area,
        )
        instance.registered_business_address_landmark = validated_data.get(
            "registered_business_address_landmark",
            instance.registered_business_address_landmark,
        )
        instance.registered_business_address_state = validated_data.get(
            "registered_business_address_state",
            instance.registered_business_address_state,
        )
        instance.registered_business_address_city = validated_data.get(
            "registered_business_address_city",
            instance.registered_business_address_city,
        )
        instance.registered_business_address_pincode = validated_data.get(
            "registered_business_address_pincode",
            instance.registered_business_address_pincode,
        )
        instance.trading_address_building = validated_data.get(
            "trading_address_building", instance.trading_address_building
        )
        instance.trading_address_area = validated_data.get(
            "trading_address_area", instance.trading_address_area
        )
        instance.trading_address_landmark = validated_data.get(
            "trading_address_landmark", instance.trading_address_landmark
        )
        instance.trading_address_state = validated_data.get(
            "trading_address_state", instance.trading_address_state
        )
        instance.trading_address_city = validated_data.get(
            "trading_address_city", instance.trading_address_city
        )
        instance.trading_address_pincode = validated_data.get(
            "trading_address_pincode", instance.trading_address_pincode
        )
        instance.updated_by = req.user  # type: ignore

        users = User.objects.filter(company_id=instance.id, vendor=None, employee=None)
        for user in users:
            user.first_name = validated_data.get("first_name", user.first_name)
            user.designation = validated_data.get("designation", user.designation)
            user.email = validated_data.get("email", user.email)
            user.phone = validated_data.get("phone", user.phone)

            user.save()

        ActivityLog.log.company_update(instance, user)

        keypersons_data = validated_data.get("keypersons", None)
        keyperson_instances = []
        KeyPersons.objects.filter(company=instance).delete()

        if keypersons_data:
            for keyperson_data in keypersons_data:
                try:
                    keyperson_instance, created = KeyPersons.objects.get_or_create(
                        company=instance, **keyperson_data
                    )
                    keyperson_instances.append(keyperson_instance)

                except IntegrityError as e:
                    raise serializers.ValidationError(
                        {"success": False, "message": f"Company {e} does not exist"}
                    )

        company_email_data = validated_data.pop("company_email", [])
        company_email_instances = []
        CompanyEmail.objects.filter(company=instance).delete()

        if company_email_data:
            for company_emails_data in company_email_data:
                try:
                    (
                        company_email_instance,
                        created,
                    ) = CompanyEmail.objects.get_or_create(
                        company=instance, **company_emails_data
                    )
                    company_email_instances.append(company_email_instance)

                except IntegrityError as e:
                    raise serializers.ValidationError(
                        {"success": False, "message": f"Company {e} does not exist"}
                    )

        instance.save()

        return instance


class CompanyInfoSerializer(serializers.ModelSerializer):
    company_logo = serializers.CharField(required=False)
    registered_business_address_pincode_number = serializers.CharField(
        source="registered_business_address_pincode.pincode_number", required=False
    )
    trading_address_pincode_number = serializers.CharField(
        source="trading_address_pincode.pincode_number", required=False
    )

    class Meta:
        model = Company
        fields = [
            "id",
            "unique_code",
            "name",
            "first_name",
            "designation",
            "website",
            "no_of_employees",
            "company_pan",
            "company_pan_verified",
            "gst_no",
            "gst_no_verified",
            "about_company",
            "email",
            "phone",
            "status",
            "is_active",
            "cin_no",
            "company_logo",
            "risk_and_compliance_title",
            "udhyam_aadharcard",
            "udhyam_aadharcard_verified",
            "registered_business_address_building",
            "registered_business_address_area",
            "registered_business_address_landmark",
            "registered_business_address_state",
            "registered_business_address_city",
            "registered_business_address_pincode",
            "registered_business_address_pincode_number",
            "trading_address_building",
            "trading_address_area",
            "trading_address_landmark",
            "trading_address_state",
            "trading_address_city",
            "trading_address_pincode",
            "trading_address_pincode_number",
            "created_by",
            "updated_by",
        ]

        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        try:
            vendor_email_verifed = EmailPhoneVerify.objects.get(email=instance.email)
            ret["email_verified"] = vendor_email_verifed.email_verified
        except EmailPhoneVerify.DoesNotExist:
            ret["email_verified"] = False

        try:
            vendor_phone_verified = EmailPhoneVerify.objects.get(
                phone_number=instance.phone
            )
            ret["phone_verified"] = vendor_phone_verified.phone_verified
        except EmailPhoneVerify.DoesNotExist:
            ret["phone_verified"] = False

        keypersons_data = []
        try:
            keypersons_data = CompanyKeyPersonsSerializer(
                instance.key_person, many=True
            ).data

        except KeyPersons.DoesNotExist:
            pass
        if not keypersons_data:
            keypersons_data = [
                {
                    "person_name": None,
                    "email": None,
                    "designation": None,
                    "contact_number": None,
                    "department": None,
                }
            ]

        company_email_data = []
        try:
            company_email_data = CompanyEmailSerializer(
                instance.company_email, many=True
            ).data

        except CompanyEmail.DoesNotExist:
            pass

        if not company_email_data:
            company_email_data = [
                {
                    "company": None,
                    "email": None,
                    "person_name": None,
                    "designation": None,
                    "phone_number": None,
                }
            ]

        attachment_data = []
        try:
            attachment_data = CompanyAttachmentSerializer(
                instance.attachment, many=True
            ).data

        except Attachment.DoesNotExist:
            pass
        if not attachment_data:
            attachment_data = [
                {
                    "attachment_name": None,
                    "attachment_file": None,
                }
            ]
        ret["keypersons"] = keypersons_data
        ret["company_email_data"] = company_email_data
        ret["attachment"] = attachment_data
        return ret


# Company Multiple Deleted
class CompanyDeleteSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Company
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])

        for deleted_id in deleted_ids:
            try:
                users = User.objects.filter(company_id=deleted_id)

                if users.exists():
                    for user in users:
                        company = Company.objects.get(id=deleted_id)
                        company.deleted = 1
                        ActivityLog.log.company_archive(company, user)
                        company.save()

            except Company.DoesNotExist:
                raise serializers.ValidationError("Company does not exist")

        return company


# Company Multiple Restore
class CompanyRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Company
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])

        for deleted_id in deleted_ids:
            try:
                users = User.objects.filter(company_id=deleted_id)
                if users.exists():
                    for user in users:
                        company = Company.objects.get(id=deleted_id)
                        company.deleted = 0
                        ActivityLog.log.company_restore(company, user)
                        company.save()

            except Company.DoesNotExist:
                raise serializers.ValidationError("Company does not exist")

        return company


class CompanyAttachmentSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", required=False)
    attachment_name = serializers.CharField(required=False)
    attachment_file = serializers.CharField(required=False)

    class Meta:
        model = Attachment
        fields = [
            "id",
            "company",
            "company_name",
            "attachment_name",
            "attachment_file",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }


class CompanyAttachmentArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Attachment
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])

        for deleted_id in deleted_ids:
            try:
                comapny_attachment = Attachment.objects.get(id=deleted_id)
                comapny_attachment.deleted = 1
                comapny_attachment.save()

            except Attachment.DoesNotExist:
                raise serializers.ValidationError("Company Attchemnet does not exist")

        return comapny_attachment


class CompanyAttachmentRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Attachment
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])

        for deleted_id in deleted_ids:
            try:
                comapny_attachment = Attachment.objects.get(id=deleted_id)
                comapny_attachment.deleted = 0
                comapny_attachment.save()

            except Attachment.DoesNotExist:
                raise serializers.ValidationError("Company Attchemnet does not exist")

        return comapny_attachment


class CompanyVerifyEmailNotificationsSerializer(serializers.ModelSerializer):
    company_verify_email_notifications = serializers.ListField(required=False)

    class Meta:
        model = CompanyEmail
        fields = [
            "company",
            "company_verify_email_notifications",
            "created_by",
            "updated_by",
        ]

        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def create(self, validated_data):
        request = self.context.get("request")
        company = validated_data.get("company").id
        company_verify_emails_data = validated_data.get(
            "company_verify_email_notifications", []
        )

        company_email_instances = []

        try:
            company_instance = Company.objects.get(id=company)
        except Company.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "success": False,
                    "message": "Company Not Found",
                }
            )
        # Create CompanyEmail instances
        for company_email_data in company_verify_emails_data:
            company_email_instance = CompanyEmail.objects.create(
                company=company_instance,
                person_name=company_email_data.get("person_name"),
                designation=company_email_data.get("designation"),
                email=company_email_data.get("email"),
                phone_number=company_email_data.get("phone_number"),
                created_by=request.user,  # type: ignore
            )
            company_email_instances.append(company_email_instance)

        return company_email_instances

    def update(self, instance, validated_data):
        request = self.context.get("request")
        company_id = validated_data.get("company")
        company_verify_emails_data = validated_data.pop(
            "company_verify_email_notifications", []
        )

        company_email_instances = []

        try:
            company_instance = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "success": False,
                    "message": "Company Not Found",
                }
            )
        # Create CompanyEmail instances
        buyer_company_ids = []
        for company_email_data in company_verify_emails_data:
            company_email_id = company_email_data.get("id")
            buyer_company_ids.append(company_email_id)

            company_email_instance = None

            if company_email_id:
                try:
                    company_email_instance = CompanyEmail.objects.get(
                        id=company_email_id
                    )
                except CompanyEmail.DoesNotExist:
                    raise serializers.ValidationError(
                        {"message": "Company Email Not Found"}
                    )

            new_company_email_instance = None
            if not company_email_instance:
                new_company_email_instance = CompanyEmail.objects.create(
                    company=company_instance,
                    person_name=company_email_data.get("person_name"),
                    designation=company_email_data.get("designation"),
                    email=company_email_data.get("email"),
                    phone_number=company_email_data.get("phone_number"),
                    created_by=request.user,  # type: ignore
                )
                company_email_instances.append(new_company_email_instance)

            else:
                company_email_instance.person_name = company_email_data["person_name"]
                company_email_instance.designation = company_email_data["designation"]
                company_email_instance.email = company_email_data["email"]
                company_email_instance.phone_number = company_email_data["phone_number"]
                company_email_instance.created_by = request.user  # type: ignore
                company_email_instances.append(company_email_instance)
                company_email_instance.save()

            # Archive CompanyEmail
            if len(buyer_company_ids) > 0:
                if new_company_email_instance:
                    CompanyEmail.objects.filter(company=company_id).exclude(
                        id__in=buyer_company_ids
                    ).exclude(
                        id=new_company_email_instance.id  # type: ignore
                    ).update(
                        deleted=1
                    )

                else:
                    # Exclude the ID of the updated CompanyEmail object from deletion
                    CompanyEmail.objects.filter(company=company_instance).exclude(
                        id__in=buyer_company_ids
                    ).update(deleted=1)

        return instance


class VerifyEmailNotificationsInfoSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", required=False)

    class Meta:
        model = CompanyEmail
        fields = [
            "id",
            "company",
            "company_name",
            "person_name",
            "designation",
            "email",
            "phone_number",
        ]
