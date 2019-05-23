import hashlib

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

from ..core import models as core_models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, email=None, password=None, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password, **extra_fields):
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser):
    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "name", "surname", "language"]

    id = models.AutoField(db_column="USER_ID", primary_key=True)
    username = models.CharField(db_column="USERNAME", unique=True, max_length=250)
    password = models.CharField(
        db_column="PASSWORD", max_length=50, blank=True, null=True
    )
    name = models.CharField(db_column="NAME", max_length=100)
    surname = models.CharField(db_column="SURNAME", max_length=100)
    email = models.CharField(db_column="EMAIL", max_length=100, blank=True, null=True)
    phone = models.CharField(db_column="PHONE", max_length=100, blank=True, null=True)
    disabled = models.PositiveSmallIntegerField(db_column="DISABLED", default=0)
    language = models.CharField(db_column="LANGUAGE", max_length=2)
    last_login = models.DateTimeField(
        db_column="LAST_REQUEST_DATE", blank=True, null=True
    )
    address = models.CharField(
        db_column="ADDRESS", max_length=100, blank=True, null=True
    )
    city = models.CharField(db_column="CITY", max_length=100, blank=True, null=True)
    zip = models.CharField(db_column="ZIP", max_length=10, blank=True, null=True)
    groups = models.ManyToManyField("Group", through="UserGroup")

    def _make_password(self, raw_password):
        salted = settings.AUTH_PASSWORT_SALT + raw_password
        return hashlib.md5(salted.encode()).hexdigest()

    def set_password(self, raw_password):
        self.password = self._make_password(raw_password)
        self._password = raw_password

    def check_password(self, raw_password):
        """
        Check password whether it matches.

        Empty passwords are not allowed.
        """
        password_empty = raw_password in ["", None]

        return not password_empty and self.password == self._make_password(raw_password)

    def get_full_name(self):
        return "{0} {1}".format(self.name, self.surname).strip()

    @property
    def is_active(self):
        return not self.disabled

    class Meta:
        managed = True
        db_table = "USER"


class UserT(models.Model):
    user = models.ForeignKey(
        User, models.DO_NOTHING, db_column="USER_ID", related_name="+"
    )
    language = models.CharField(db_column="LANGUAGE", max_length=2)
    city = models.CharField(db_column="CITY", max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "USER_T"


class Group(core_models.MultilingualModel, models.Model):
    group_id = models.AutoField(db_column="GROUP_ID", primary_key=True)
    role = models.ForeignKey(
        "user.Role", models.PROTECT, db_column="ROLE_ID", related_name="+"
    )
    service = models.ForeignKey(
        "user.Service",
        models.SET_NULL,
        db_column="SERVICE_ID",
        related_name="groups",
        blank=True,
        null=True,
    )
    disabled = models.PositiveSmallIntegerField(db_column="DISABLED", default=0)
    name = models.CharField(db_column="NAME", max_length=100, blank=True, null=True)
    phone = models.CharField(db_column="PHONE", max_length=100, blank=True, null=True)
    zip = models.CharField(db_column="ZIP", max_length=10, blank=True, null=True)
    city = models.CharField(db_column="CITY", max_length=100, blank=True, null=True)
    address = models.CharField(
        db_column="ADDRESS", max_length=100, blank=True, null=True
    )
    email = models.CharField(db_column="EMAIL", max_length=100, blank=True, null=True)
    website = models.CharField(
        db_column="WEBSITE", max_length=1000, blank=True, null=True
    )
    locations = models.ManyToManyField("Location", through="GroupLocation")

    class Meta:
        managed = True
        db_table = "GROUP"


class GroupT(models.Model):
    group = models.ForeignKey(
        Group, models.CASCADE, db_column="GROUP_ID", related_name="trans"
    )
    language = models.CharField(db_column="LANGUAGE", max_length=2)
    name = models.CharField(db_column="NAME", max_length=200, blank=True, null=True)
    city = models.CharField(db_column="CITY", max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "GROUP_T"


class Location(core_models.MultilingualModel, models.Model):
    location_id = models.AutoField(db_column="LOCATION_ID", primary_key=True)
    communal_cantonal_number = models.IntegerField(
        db_column="COMMUNAL_CANTONAL_NUMBER", blank=True, null=True
    )
    communal_federal_number = models.CharField(
        db_column="COMMUNAL_FEDERAL_NUMBER", max_length=255, blank=True, null=True
    )
    district_number = models.IntegerField(
        db_column="DISTRICT_NUMBER", blank=True, null=True
    )
    section_number = models.IntegerField(
        db_column="SECTION_NUMBER", blank=True, null=True
    )
    name = models.CharField(db_column="NAME", max_length=100, blank=True, null=True)
    commune_name = models.CharField(
        db_column="COMMUNE_NAME", max_length=100, blank=True, null=True
    )
    district_name = models.CharField(
        db_column="DISTRICT_NAME", max_length=100, blank=True, null=True
    )
    section_name = models.CharField(
        db_column="SECTION_NAME", max_length=100, blank=True, null=True
    )
    zip = models.CharField(db_column="ZIP", max_length=10, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "LOCATION"


class LocationT(models.Model):
    location = models.ForeignKey(
        Location, models.CASCADE, db_column="LOCATION_ID", related_name="trans"
    )
    language = models.CharField(db_column="LANGUAGE", max_length=2)
    name = models.CharField(db_column="NAME", max_length=100, blank=True, null=True)
    commune_name = models.CharField(
        db_column="COMMUNE_NAME", max_length=100, blank=True, null=True
    )
    district_name = models.CharField(
        db_column="DISTRICT_NAME", max_length=100, blank=True, null=True
    )
    section_name = models.CharField(
        db_column="SECTION_NAME", max_length=100, blank=True, null=True
    )

    class Meta:
        managed = True
        db_table = "LOCATION_T"


class GroupLocation(models.Model):
    id = models.AutoField(db_column="ID", primary_key=True)
    group = models.ForeignKey(
        Group, models.CASCADE, db_column="GROUP_ID", related_name="+"
    )
    location = models.ForeignKey(
        Location, models.CASCADE, db_column="LOCATION_ID", related_name="+"
    )

    class Meta:
        managed = True
        db_table = "GROUP_LOCATION"
        unique_together = (("group", "location"),)


class UserGroup(models.Model):
    id = models.AutoField(db_column="ID", primary_key=True)
    user = models.ForeignKey(
        User, models.CASCADE, db_column="USER_ID", related_name="user_groups"
    )
    group = models.ForeignKey(
        Group, models.CASCADE, db_column="GROUP_ID", related_name="+"
    )
    default_group = models.PositiveSmallIntegerField(db_column="DEFAULT_GROUP")

    class Meta:
        managed = True
        db_table = "USER_GROUP"
        unique_together = (("user", "group"),)


class Role(core_models.MultilingualModel, models.Model):
    role_id = models.AutoField(db_column="ROLE_ID", primary_key=True)
    role_parent = models.ForeignKey(
        "self",
        models.SET_NULL,
        db_column="ROLE_PARENT_ID",
        related_name="+",
        blank=True,
        null=True,
    )
    name = models.CharField(db_column="NAME", max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "ROLE"


class RoleT(models.Model):
    role = models.ForeignKey(
        Role, models.CASCADE, db_column="ROLE_ID", related_name="trans"
    )
    language = models.CharField(db_column="LANGUAGE", max_length=2)
    name = models.CharField(db_column="NAME", max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "ROLE_T"


class ServiceGroup(models.Model):
    service_group_id = models.AutoField(db_column="SERVICE_GROUP_ID", primary_key=True)
    name = models.CharField(db_column="NAME", max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "SERVICE_GROUP"


class ServiceGroupT(models.Model):
    service_group = models.ForeignKey(
        ServiceGroup, models.CASCADE, db_column="SERVICE_GROUP_ID", related_name="+"
    )
    language = models.CharField(db_column="LANGUAGE", max_length=2)
    name = models.CharField(db_column="NAME", max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "SERVICE_GROUP_T"


class Service(core_models.MultilingualModel, models.Model):
    service_id = models.AutoField(db_column="SERVICE_ID", primary_key=True)
    service_group = models.ForeignKey(
        ServiceGroup, models.PROTECT, db_column="SERVICE_GROUP_ID", related_name="+"
    )
    service_parent = models.ForeignKey(
        "self",
        models.SET_NULL,
        db_column="SERVICE_PARENT_ID",
        related_name="+",
        blank=True,
        null=True,
    )
    name = models.CharField(db_column="NAME", max_length=100, blank=True, null=True)
    description = models.CharField(
        db_column="DESCRIPTION", max_length=255, blank=True, null=True
    )
    sort = models.IntegerField(db_column="SORT")
    phone = models.CharField(db_column="PHONE", max_length=100, blank=True, null=True)
    zip = models.CharField(db_column="ZIP", max_length=10, blank=True, null=True)
    city = models.CharField(db_column="CITY", max_length=100, blank=True, null=True)
    address = models.CharField(
        db_column="ADDRESS", max_length=100, blank=True, null=True
    )
    email = models.CharField(db_column="EMAIL", max_length=100, blank=True, null=True)
    website = models.CharField(
        db_column="WEBSITE", max_length=1000, blank=True, null=True
    )
    disabled = models.PositiveSmallIntegerField(db_column="DISABLED", default=0)
    notification = models.PositiveSmallIntegerField(default=1)

    class Meta:
        managed = True
        db_table = "SERVICE"


class ServiceT(models.Model):
    service = models.ForeignKey(
        Service, models.CASCADE, db_column="SERVICE_ID", related_name="trans"
    )
    language = models.CharField(db_column="LANGUAGE", max_length=2)
    name = models.CharField(db_column="NAME", max_length=200, blank=True, null=True)
    description = models.CharField(
        db_column="DESCRIPTION", max_length=255, blank=True, null=True
    )
    city = models.CharField(db_column="CITY", max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "SERVICE_T"
