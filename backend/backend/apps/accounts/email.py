from common.emails import BaseSendGridEmailTemplate
#from common.services.base import get_absolute_link
from datetime import date

from django.conf import settings


def get_absolute_link(link):
    """
    Method check if path contains domain name in link and return absolute link
    :param link: Absolute or relative link
    :return: Absolute link with domain
    """
    if settings.WWW_ROOT not in link:
        return settings.WWW_ROOT + link
    return link


class BusinessClaimAcceptedEmailTemplate(BaseSendGridEmailTemplate):
    template_id = 'd-c14073d9702b4a6598bc53e5fa02782a'
    required_template_variables = ['business_name', 'business_url', 'year']

    @staticmethod
    def prepare_email_content(instance):
        return {
            'business_name': 'pugal',
            'business_url': 'narayana.s@deductiveclouds.com',
            'year': date.today().year
        }

    @staticmethod
    def get_email_subject(instance):
        return f'Hurray! Your Registrations with Chabson app is completed.'