"""Version 1 API endpoints"""

import logging

from flask import Blueprint, request, make_response
from werkzeug.exceptions import BadRequest, NotFound
from src.controllers.messages import send_template, receive_message
from settings import Configurations

VERIFY_TOKEN = Configurations.WHATSAPP_VERIFY_TOKEN

v1 = Blueprint(name="v1", import_name=__name__, url_prefix="/v1")

logger = logging.getLogger(__name__)

# Security headers
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-cache",
}


@v1.after_request
def add_security_headers(response):
    """
    Add security headers to the API response.

    :param response: The API response object.
    :type response: flask.Response

    :return: The updated API response object with added security headers.
    :rtype: flask.Response
    """
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


@v1.route(rule="/send", methods=["POST"])
def send_message():
    """
    Send a message.

    :return: A tuple containing the response and the HTTP status code.
    :rtype: tuple

    :raises BadRequest: If the required parameters are missing from the request data.
    :raises NotFound: If the sender is not found.
    :raises Exception: If an unexpected error occurs.
    """
    try:
        data = request.get_json()

        if not data.get("sender"):
            logger.error("No Sender Provided")
            raise BadRequest()

        if not data.get("recipient"):
            logger.error("No Recipient Provided")
            raise BadRequest()

        sender = data.get("sender")
        recipient = data.get("recipient")
        template = "hello_world"
        components = []
        lang = "en_US"

        res = send_template(
            sender=sender,
            recipient=recipient,
            components=components,
            template=template,
            lang=lang,
        )

        if not res:
            raise NotFound(f"Sender '{sender}' Not Found")

        return res, 200

    except BadRequest as error:
        return str(error.description), 400

    except NotFound as error:
        return str(error.description), 404

    except Exception as error:
        logger.exception(error)
        return "Internal Server Error", 500


@v1.route(rule="/receive", methods=["GET", "POST"])
def receive_web_hook():
    """
    Receive webhook data.

    :return: A tuple containing an empty response and the HTTP status code.
    :rtype: tuple

    :raises BadRequest: If the request data is invalid.
    :raises NotFound: If the sender is not found.
    :raises Exception: If an unexpected error occurs.
    """
    method = request.method.lower()

    try:
        if method == "get":
            if request.args.get("hub.verify_token") == VERIFY_TOKEN:
                logger.info("Verified webhook")
                response = make_response(request.args.get("hub.challenge"), 200)
                response.mimetype = "text/plain"

                return response

            logger.error("Webhook Verification failed")
            return "Invalid verification token", 200

        if method == "post":
            data = request.get_json()

            res = receive_message(webhook_data=data)

            if not res:
                raise NotFound("Recipient Not Found")

            return "OK", 200

        logger.error("Unallowed method")
        raise BadRequest()

    except BadRequest as error:
        return str(error.description), 400

    except NotFound as error:
        return str(error.description), 404

    except Exception as error:
        logger.exception(error)
        return "Internal Server Error", 500
