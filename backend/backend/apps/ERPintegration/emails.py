import os
from sendgrid import SendGridAPIClient
from typing import List, Dict
from django.conf import settings

class BaseSendGridEmailTemplate(object):

    @classmethod
    def validate_template_variables(self, temp_variables: Dict) -> bool:
        """
        Method validate if all required templates variables are included in temp_variables
        :param temp_variables: dict with variables and values to send
        """
        return all([variable in temp_variables.keys() for variable in self.required_template_variables])

    @staticmethod
    def prepare_list_of_emails(email_receivers: List[str]) -> List:
        """
        Method
        :param email_receivers: List of the users email
        :return: List of dictionaries with user emails with sendgrid structure
        """
        if type(email_receivers) is not list:
            raise TypeError("'email_receivers' need to be a type of list")
        return [{"email": email} for email in email_receivers]

    @classmethod
    def send_email(cls, subject: str, email_receivers: List[str], instance) -> bool:
        """
        Method prepare data for email and send email to specific list of the users.
        :param subject: Subject of the email
        :param email_receivers: List of the users email
        :return: Status of sent email
        """
        template_variables = cls.prepare_email_content(instance)
        template_variables['email_subject'] = cls.get_email_subject(instance)
        
        if cls.validate_template_variables(template_variables):
            #print(template_variables)
            email_data = {
                "from": {
                    "email": settings.DEFAULT_FROM_EMAIL
                },
                "personalizations": [
                    {
                        "to": cls.prepare_list_of_emails(email_receivers=email_receivers),
                        "subject": cls.get_email_subject(instance),
                        "dynamic_template_data": template_variables
                    }
                ],
                "template_id": cls.template_id
            }
            client = SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))
            client.client.mail.send.post(request_body=email_data)
            #print(client).data
            return True
        return False
