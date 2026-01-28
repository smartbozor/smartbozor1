from django.utils.functional import lazy
from django.utils.translation import get_language
from django.conf import settings
from django.db import models


def _get_i18n_display(property_name):
    def __method(self):
        lng = get_language()
        prop = f"{property_name}_{lng}"
        if lng is None or not hasattr(self, prop):
            return getattr(self, f"{property_name}_{settings.LANGUAGE_CODE}")

        return getattr(self, prop)

    return __method


def _get_i18n_gettext(proxy, lang):
    return str(proxy) + f" ({lang})"


def _get__str__(name):
    def __method(self):
        return getattr(self, name)

    return __method


_gettext_lazy_lang = lazy(_get_i18n_gettext, str)


def _i18n(cls):
    if not issubclass(cls, models.Model):
        return cls

    codes = set(row[0] for row in settings.LANGUAGES)

    for field in cls._meta.fields:
        suffix = field.name[-3:]
        if not suffix.startswith("_") or suffix[1:] not in codes:
            continue

        verbose_name = field.verbose_name
        property_name = field.name[:-3]
        has_trans = 'VERBOSE_NAMES' in cls.__dict__ and property_name in cls.VERBOSE_NAMES

        if property_name not in cls.__dict__:
            p = _get_i18n_display(property_name)
            setattr(cls, property_name, property(p))

            if has_trans:
                p.short_description = cls.VERBOSE_NAMES[property_name]
            elif verbose_name:
                p.short_description = verbose_name

        if has_trans:
            field.verbose_name = _gettext_lazy_lang(cls.VERBOSE_NAMES[property_name], suffix[1:])

    return cls


def i18n(name):
    if isinstance(name, str):
        def set_str_wrapper(cls):
            setattr(cls, '__str__', _get__str__(name))

            return _i18n(cls)

        return set_str_wrapper

    return _i18n(name)
