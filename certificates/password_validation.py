from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class StudentPasswordValidator:
    def validate(self, password, user=None):
        if user and hasattr(user, 'student'):
            if password == user.student.phone:
                raise ValidationError(
                    _("Your password can't be your phone number."),
                    code='password_same_as_phone',
                )

    def get_help_text(self):
        return _("Your password can't be your phone number.")
