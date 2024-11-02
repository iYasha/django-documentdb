DATABASES = {
    "default": {
        "ENGINE": "django_mongodb",
        "NAME": "mongotest",
        "HOST": "host.docker.internal",
        "USER": "root",
        "PASSWORD": "mongoadmin",
    },
    "other": {
        "ENGINE": "django_mongodb",
        "NAME": "mongotest-other",
        "HOST": "host.docker.internal",
        "USER": "root",
        "PASSWORD": "mongoadmin",
    },
}
DEFAULT_AUTO_FIELD = "django_mongodb.fields.ObjectIdAutoField"
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
SECRET_KEY = "django_tests_secret_key"  # noqa: S105
USE_TZ = False
