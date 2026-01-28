from django.contrib.auth.views import LoginView

from apps.account.forms import LoginForm


class AccountLoginView(LoginView):
    template_name = 'account/login.j2'
    form_class = LoginForm

