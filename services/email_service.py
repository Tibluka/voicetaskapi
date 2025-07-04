import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from decouple import config

API_KEY = config("BREVO_API_KEY")
SENDER_EMAIL = config("EMAIL_SENDER")
SENDER_NAME = config("EMAIL_SENDER_NAME", "VoiceTask")

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key["api-key"] = API_KEY
api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
    sib_api_v3_sdk.ApiClient(configuration)
)


def send_reset_email_with_template(to_email: str, template_id: int, params: dict):
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"email": SENDER_EMAIL, "name": SENDER_NAME},
        template_id=template_id,
        params=params,
    )
    try:
        api_instance.send_transac_email(send_smtp_email)
        print(f"[DEBUG] Reset code sent via template {template_id} to {to_email}")
    except ApiException as e:
        print(f"[ERROR] Brevo sendTransacEmail failed: {e}")
        raise
