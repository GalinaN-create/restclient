import allure
import requests
from requests import session, Response
import structlog
import uuid
import curlify
import allure
import json


def allure_attach(fn):
    def wrapper(*args, **kwargs):
        body = kwargs.get('json')
        if body:
            allure.attach(
                json.dumps(kwargs.get('json'), indent=2),
                name='request',
                attachment_type=allure.attachment_type.JSON
            )
        response = fn(*args, **kwargs)
        try:
            response_json = response.json()
        except requests.exceptions.JSONDecodeError:
            response_text = response.text
            status_code = f'< status_code {response.status_code}>'
            allure.attach(
                response_text if len(response_text) > 0 else status_code,
                name='response',
                attachment_type=allure.attachment_type.TEXT
            )
        else:
            allure.attach(
                json.dumps(response_json, indent=2),
                name='request',
                attachment_type=allure.attachment_type.JSON
            )
        return response
    return wrapper


class Restclient:

    def __init__(self, host, headers=None):
        self.host = host
        self.session = session()
        if headers:
            self.session.headers.update(headers)
        self.log = structlog.get_logger(self.__class__.__name__).bind(service='api')

    # Обёртка над rest методами
    @allure_attach
    def post(self, path: str, **kwargs) -> Response:
        allure.attach(json.dumps
                      (kwargs.get('json'), indent=2),
                      name="request",
                      attachment_type=allure.attachment_type.JSON)
        return self._send_request('POST', path, **kwargs)

    @allure_attach
    def get(self, path: str, **kwargs) -> Response:
        return self._send_request('GET', path, **kwargs)

    @allure_attach
    def put(self, path: str, **kwargs) -> Response:
        return self._send_request('PUT', path, **kwargs)

    @allure_attach
    def delete(self, path: str, **kwargs) -> Response:
        return self._send_request('DELETE', path, **kwargs)

    # Метод принимает запрос, оборачивает его в лог и после этого отдаёт обёрнутый запрос
    def _send_request(self, method, path, **kwargs):
        full_url = self.host + path
        log = self.log.bind(event_id=str(uuid.uuid4()))
        # Формируем лог - те необх данные, которые нам нужны
        # Параметры, которые увилдим до отправки
        log.msg(
            event='request',
            method=method,
            full_url=full_url,
            params=kwargs.get('params'),
            headers=kwargs.get('headers'),
            json=kwargs.get('json'),
            data=kwargs.get('data')
        )
        # формируем запрос с нашими переменными, Куда будут возвращаться результаты нашего запроса
        response = self.session.request(
            method=method,
            url=full_url,
            **kwargs
        )
        # Формирование curl по запросу
        curl = curlify.to_curl(response.request)
        allure.attach(
            curl,
            name='curl',
            attachment_type=allure.attachment_type.TEXT
        )
        print(curl)
        # Подробный ответ (запуск курла)
        log.msg(
            event='response',
            status_code=response.status_code,
            headers=response.headers,
            json=self.get_json(response),
            text=response.text,
            content=response.content,
            curl=curl
        )
        return response

    @staticmethod
    def get_json(response):
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return
