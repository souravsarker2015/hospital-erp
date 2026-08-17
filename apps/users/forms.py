from django.contrib.auth.forms import AuthenticationForm

INPUT_CLASSES = (
    "block w-full rounded-lg border border-brand-900/15 bg-white px-3.5 py-2.5 text-sm "
    "text-brand-950 placeholder:text-brand-900/30 focus:border-brand-500 focus:outline-none "
    "focus:ring-2 focus:ring-brand-500/20"
)


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.setdefault("class", INPUT_CLASSES)
        self.fields["password"].widget.attrs.setdefault("class", INPUT_CLASSES)
