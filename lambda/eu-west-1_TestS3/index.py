# -*- coding: utf-8 -*-

import logging
import boto3
import six


from ask_sdk.standard_s3 import StandardSkillBuilder
from ask_sdk_core.dispatch_components import (AbstractRequestHandler, AbstractExceptionHandler, AbstractRequestInterceptor, AbstractResponseInterceptor)
from ask_sdk_core import attributes_manager
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response, request_envelope, RequestEnvelope
from ask_sdk_model.ui import SimpleCard
from ask_sdk_s3_persistence import S3PersistenceAdapter
from datetime import datetime

from ask_sdk_s3_persistence.ObjectKeyGenerators import applicationId


s3_client = boto3.client('s3')
#object_generator = applicationId(request_envelope)
path_prefix = 'test_prefix'

ssb = StandardSkillBuilder(bucket_name='testpersistence', object_generator=applicationId, s3_client=s3_client, path_prefix=path_prefix)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        logger.info('In LaunchRequest')
        logger.info(f'LAUNCH: {handler_input.request_envelope}')
        speechText = 'Welcome to the global persistence demo. You can tell me a key value pair, with a four digit key and a country as value. For example you can say assign Australia to <say-as interpret-as="digits">1234</say-as>'

        handler_input.response_builder.speak(speechText).set_card(SimpleCard("Launch Request", speechText)).ask(speechText).set_should_end_session(False)

        return handler_input.response_builder.response


class GetAttributeIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetAttributeIntent")(handler_input)

    def handle(self, handler_input):
        logger.info('In GetAttributeIntent')
        request = handler_input.request_envelope.request
        intent = request.intent

        slot_values = get_slot_values(intent.slots)

        key = slot_values['key'] if slot_values['key'] else None
        value = slot_values['value'] if slot_values['value'] else None

        speechText = 'I don\'t know that! You can tell me a key value pair, with a four digit key and a country as value. For example you can say assign Australia to <say-as interpret-as="digits">1234</say-as>'

        if (key and value):
            attributes = handler_input.attributes_manager.session_attributes
            attributes[key] = value
            handler_input.attributes_manager.session_attributes = attributes
            speechText = 'Key value pair <say-as interpret-as="digits">' + key + '</say-as> ' + value + ' registered! Will be saved on exit';

        handler_input.response_builder.speak(speechText).set_card(SimpleCard("Get Attributes Intent", speechText)).ask(speechText).set_should_end_session(False)

        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        logger.info('In HelpIntent')

        speechText = 'You can tell me a key value pair, with a four digit key and a country as value. For example you can say assign Australia to <say-as interpret-as="digits">1234</say-as>'

        handler_input.response_builder.speak(speechText).ask(speechText).set_card(SimpleCard("Help Intent", speechText))

        return handler_input.response_builder.response


class CancelAndStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.CancelIntent")(handler_input) or is_intent_name("AMAZON.StopIntent")(handler_input)

    def handle(self, handler_input):
        logger.info('In CancelAndStopIntentHandler')
        speechText = "Goodbye!"

        handler_input.response_builder.speak(speechText).set_card(SimpleCard("Stop and Cancel Intents", speechText))

        return handler_input.response_builder.set_should_end_session(True).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class AllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        # Log the exception in CloudWatch
        logger.info('In AllExceptionHandler')
        print(exception)
        logger.info(exception, exc_info=True)
        speechText = "Sorry, I think I did not get it. Say, help to get more information"
        handler_input.response_builder.speak(speechText).set_card(SimpleCard("Error", speechText)).ask(speechText)
        return handler_input.response_builder.response


class RequestLogger(AbstractRequestInterceptor):
    def process(self, handler_input):
        #logger.debug(f'Alexa Request: {handler_input.request_envelope.request}')
        logger.info(f'Alexa Request: {handler_input.request_envelope.request}')


class ResponseLogger(AbstractResponseInterceptor):
    def process(self, handler_input, response):
        # type: (HandlerInput, Response) -> None
        #logger.debug(f'Alexa Response: {response}')
        logger.info(f'Alexa Response: {response}')


class SavePersistenceAttributesResponseInterceptor(AbstractResponseInterceptor):
    """Save persistence attributes before sending response to user."""
    def process(self, handler_input, response):
        logger.info('In SavePersistenceAttributesResponseInterceptor')
        ses = response.should_end_session if response.should_end_session else True
        if (ses or handler_input.request_envelope.request.type == 'SessionEndedRequest'):

            attributes = handler_input.attributes_manager.session_attributes
            attributes['lastUseTimestamp'] = f"SAVE NOW {attributes['launchCount']+1}"
            handler_input.attributes_manager.save_persistent_attributes()


class LoadPersistenceAttributesRequestInterceptor(AbstractRequestInterceptor):
    def process(self, handler_input):
        # type: (HandlerInput) -> None
        logger.info('In LoadPersistenceAttributesRequestInterceptor')
        attributes = handler_input.attributes_manager.persistent_attributes
        logger.info(f'LOAD ATTRS: {attributes}')

        if len(attributes) == 0:
            # First time skill user
            attributes['loadedAtTimestamp'] = 'LOAD'
            attributes['launchCount'] = 0
        else:
            if 'launchCount' in attributes:
                attributes['launchCount'] += 1
            else:
                attributes['launchCount'] = 0

        handler_input.attributes_manager.session_attributes = attributes


def get_slot_values(filled_slots):
    """Return slot values with additional info."""
    # type: (Dict[str, Slot]) -> Dict[str, Any]
    slot_values = {}
    logger.info("Filled slots: {}".format(filled_slots))

    for key, slot_item in six.iteritems(filled_slots):
        name = slot_item.name
        if slot_item.resolutions:
            status_code = resolutions_per_authority[0].status.code
            if status_code == StatusCode.ER_SUCCESS_MATCH:
                slot_values[name] = {
                    "synonym": slot_item.value,
                    "resolved": slot_item.resolutions.resolutions_per_authority[0].values[0].value.name,
                    "is_validated": True,
                }
            elif status_code == StatusCode.ER_SUCCESS_NO_MATCH:
                slot_values[name] = {
                    "synonym": slot_item.value,
                    "resolved": slot_item.value,
                    "is_validated": False,
                }
        else:
            slot_values[name] = slot_item.value
    return slot_values


ssb.add_request_handler(LaunchRequestHandler())
ssb.add_request_handler(CancelAndStopIntentHandler())
ssb.add_request_handler(SessionEndedRequestHandler())
ssb.add_request_handler(HelpIntentHandler())
ssb.add_request_handler(GetAttributeIntentHandler())


ssb.add_exception_handler(AllExceptionHandler())

ssb.add_global_request_interceptor(RequestLogger())
ssb.add_global_request_interceptor(LoadPersistenceAttributesRequestInterceptor())

ssb.add_global_response_interceptor(ResponseLogger())
ssb.add_global_response_interceptor(SavePersistenceAttributesResponseInterceptor())


handler = ssb.lambda_handler()
