from humanize import intcomma


def currency(number):
    return str(intcomma(number)).replace(",", " ") + " so'm"