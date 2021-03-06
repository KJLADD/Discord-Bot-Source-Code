# -*- coding: utf-8 -*-
"""Tests for aiohttp/client.py"""

import gc
import sys
from unittest import mock

import pytest
from yarl import URL

import aiohttp
from aiohttp import http
from aiohttp.client_reqrep import ClientResponse, RequestInfo
from aiohttp.test_utils import make_mocked_coro


@pytest.fixture
def session():
    return mock.Mock()


async def test_http_processing_error(session):
    loop = mock.Mock()
    request_info = mock.Mock()
    response = ClientResponse(
        'get', URL('http://del-cl-resp.org'), request_info=request_info)
    response._post_init(loop, session)
    loop.get_debug = mock.Mock()
    loop.get_debug.return_value = True

    connection = mock.Mock()
    connection.protocol = aiohttp.DataQueue(loop=loop)
    connection.protocol.set_response_params = mock.Mock()
    connection.protocol.set_exception(http.HttpProcessingError())

    with pytest.raises(aiohttp.ClientResponseError) as info:
        await response.start(connection)

    assert info.value.request_info is request_info


def test_del(session):
    loop = mock.Mock()
    response = ClientResponse('get', URL('http://del-cl-resp.org'))
    response._post_init(loop, session)
    loop.get_debug = mock.Mock()
    loop.get_debug.return_value = True

    connection = mock.Mock()
    response._closed = False
    response._connection = connection
    loop.set_exception_handler(lambda loop, ctx: None)

    with pytest.warns(ResourceWarning):
        del response
        gc.collect()

    connection.release.assert_called_with()


def test_close(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)
    response._closed = False
    response._connection = mock.Mock()
    response.close()
    assert response.connection is None
    response.close()
    response.close()


def test_wait_for_100_1(loop, session):
    response = ClientResponse(
        'get', URL('http://python.org'), continue100=object())
    response._post_init(loop, session)
    assert response._continue is not None
    response.close()


def test_wait_for_100_2(loop, session):
    response = ClientResponse(
        'get', URL('http://python.org'))
    response._post_init(loop, session)
    assert response._continue is None
    response.close()


def test_repr(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)
    response.status = 200
    response.reason = 'Ok'
    assert '<ClientResponse(http://def-cl-resp.org) [200 Ok]>'\
        in repr(response)


def test_repr_non_ascii_url():
    response = ClientResponse('get', URL('http://fake-host.org/\u03bb'))
    assert "<ClientResponse(http://fake-host.org/%CE%BB) [None None]>"\
        in repr(response)


def test_repr_non_ascii_reason():
    response = ClientResponse('get', URL('http://fake-host.org/path'))
    response.reason = '\u03bb'
    assert "<ClientResponse(http://fake-host.org/path) [None \\u03bb]>"\
        in repr(response)


def test_url_obj_deprecated():
    response = ClientResponse('get', URL('http://fake-host.org/'))
    with pytest.warns(DeprecationWarning):
        response.url_obj


async def test_read_and_release_connection(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result(b'payload')
        return fut
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect

    res = await response.read()
    assert res == b'payload'
    assert response._connection is None


async def test_read_and_release_connection_with_error(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)
    content = response.content = mock.Mock()
    content.read.return_value = loop.create_future()
    content.read.return_value.set_exception(ValueError)

    with pytest.raises(ValueError):
        await response.read()
    assert response._closed


async def test_release(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)
    fut = loop.create_future()
    fut.set_result(b'')
    content = response.content = mock.Mock()
    content.readany.return_value = fut

    response.release()
    assert response._connection is None


@pytest.mark.skipif(sys.implementation.name != 'cpython',
                    reason="Other implementations has different GC strategies")
async def test_release_on_del(loop, session):
    connection = mock.Mock()
    connection.protocol.upgraded = False

    def run(conn):
        response = ClientResponse('get', URL('http://def-cl-resp.org'))
        response._post_init(loop, session)
        response._closed = False
        response._connection = conn

    run(connection)

    assert connection.release.called


async def test_response_eof(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)
    response._closed = False
    conn = response._connection = mock.Mock()
    conn.protocol.upgraded = False

    response._response_eof()
    assert conn.release.called
    assert response._connection is None


async def test_response_eof_upgraded(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    conn = response._connection = mock.Mock()
    conn.protocol.upgraded = True

    response._response_eof()
    assert not conn.release.called
    assert response._connection is conn


async def test_response_eof_after_connection_detach(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)
    response._closed = False
    conn = response._connection = mock.Mock()
    conn.protocol = None

    response._response_eof()
    assert conn.release.called
    assert response._connection is None


async def test_text(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result('{"тест": "пройден"}'.encode('cp1251'))
        return fut

    response.headers = {
        'Content-Type': 'application/json;charset=cp1251'}
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect

    res = await response.text()
    assert res == '{"тест": "пройден"}'
    assert response._connection is None


async def test_text_bad_encoding(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result('{"тестkey": "пройденvalue"}'.encode('cp1251'))
        return fut

    # lie about the encoding
    response.headers = {
        'Content-Type': 'application/json;charset=utf-8'}
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect
    with pytest.raises(UnicodeDecodeError):
        await response.text()
    # only the valid utf-8 characters will be returned
    res = await response.text(errors='ignore')
    assert res == '{"key": "value"}'
    assert response._connection is None


async def test_text_custom_encoding(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result('{"тест": "пройден"}'.encode('cp1251'))
        return fut

    response.headers = {
        'Content-Type': 'application/json'}
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect
    response.get_encoding = mock.Mock()

    res = await response.text(encoding='cp1251')
    assert res == '{"тест": "пройден"}'
    assert response._connection is None
    assert not response.get_encoding.called


async def test_text_detect_encoding(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result('{"тест": "пройден"}'.encode('cp1251'))
        return fut

    response.headers = {'Content-Type': 'text/plain'}
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect

    await response.read()
    res = await response.text()
    assert res == '{"тест": "пройден"}'
    assert response._connection is None


async def test_text_detect_encoding_if_invalid_charset(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result('{"тест": "пройден"}'.encode('cp1251'))
        return fut

    response.headers = {'Content-Type': 'text/plain;charset=invalid'}
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect

    await response.read()
    res = await response.text()
    assert res == '{"тест": "пройден"}'
    assert response._connection is None
    assert response.get_encoding().lower() in ('windows-1251', 'maccyrillic')


async def test_text_after_read(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result('{"тест": "пройден"}'.encode('cp1251'))
        return fut

    response.headers = {
        'Content-Type': 'application/json;charset=cp1251'}
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect

    res = await response.text()
    assert res == '{"тест": "пройден"}'
    assert response._connection is None


async def test_json(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result('{"тест": "пройден"}'.encode('cp1251'))
        return fut

    response.headers = {
        'Content-Type': 'application/json;charset=cp1251'}
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect

    res = await response.json()
    assert res == {'тест': 'пройден'}
    assert response._connection is None


async def test_json_extended_content_type(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result('{"тест": "пройден"}'.encode('cp1251'))
        return fut

    response.headers = {
        'Content-Type':
            'application/this.is-1_content+subtype+json;charset=cp1251'}
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect

    res = await response.json()
    assert res == {'тест': 'пройден'}
    assert response._connection is None


async def test_json_custom_content_type(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result('{"тест": "пройден"}'.encode('cp1251'))
        return fut

    response.headers = {
        'Content-Type': 'custom/type;charset=cp1251'}
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect

    res = await response.json(content_type='custom/type')
    assert res == {'тест': 'пройден'}
    assert response._connection is None


async def test_json_custom_loader(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)
    response.headers = {
        'Content-Type': 'application/json;charset=cp1251'}
    response._content = b'data'

    def custom(content):
        return content + '-custom'

    res = await response.json(loads=custom)
    assert res == 'data-custom'


async def test_json_invalid_content_type(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)
    response.headers = {
        'Content-Type': 'data/octet-stream'}
    response._content = b''

    with pytest.raises(aiohttp.ContentTypeError) as info:
        await response.json()

    assert info.value.request_info == response.request_info


async def test_json_no_content(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)
    response.headers = {
        'Content-Type': 'data/octet-stream'}
    response._content = b''

    res = await response.json(content_type=None)
    assert res is None


async def test_json_override_encoding(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result('{"тест": "пройден"}'.encode('cp1251'))
        return fut

    response.headers = {
        'Content-Type': 'application/json;charset=utf8'}
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect
    response.get_encoding = mock.Mock()

    res = await response.json(encoding='cp1251')
    assert res == {'тест': 'пройден'}
    assert response._connection is None
    assert not response.get_encoding.called


@pytest.mark.xfail
def test_override_flow_control(loop, session):
    class MyResponse(ClientResponse):
        flow_control_class = aiohttp.StreamReader
    response = MyResponse('get', URL('http://my-cl-resp.org'))
    response._post_init(loop, session)
    response._connection = mock.Mock()
    assert isinstance(response.content, aiohttp.StreamReader)
    response.close()


def test_get_encoding_unknown(loop, session):
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response._post_init(loop, session)

    response.headers = {'Content-Type': 'application/json'}
    with mock.patch('aiohttp.client_reqrep.chardet') as m_chardet:
        m_chardet.detect.return_value = {'encoding': None}
        assert response.get_encoding() == 'utf-8'


def test_raise_for_status_2xx():
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response.status = 200
    response.reason = 'OK'
    response.raise_for_status()  # should not raise


def test_raise_for_status_4xx():
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response.status = 409
    response.reason = 'CONFLICT'
    with pytest.raises(aiohttp.ClientResponseError) as cm:
        response.raise_for_status()
    assert str(cm.value.code) == '409'
    assert str(cm.value.message) == "CONFLICT"


def test_resp_host():
    response = ClientResponse('get', URL('http://del-cl-resp.org'))
    assert 'del-cl-resp.org' == response.host


def test_content_type():
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response.headers = {'Content-Type': 'application/json;charset=cp1251'}

    assert 'application/json' == response.content_type


def test_content_type_no_header():
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response.headers = {}

    assert 'application/octet-stream' == response.content_type


def test_charset():
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response.headers = {'Content-Type': 'application/json;charset=cp1251'}

    assert 'cp1251' == response.charset


def test_charset_no_header():
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response.headers = {}

    assert response.charset is None


def test_charset_no_charset():
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response.headers = {'Content-Type': 'application/json'}

    assert response.charset is None


def test_content_disposition_full():
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response.headers = {'Content-Disposition':
                        'attachment; filename="archive.tar.gz"; foo=bar'}

    assert 'attachment' == response.content_disposition.type
    assert 'bar' == response.content_disposition.parameters["foo"]
    assert 'archive.tar.gz' == response.content_disposition.filename
    with pytest.raises(TypeError):
        response.content_disposition.parameters["foo"] = "baz"


def test_content_disposition_no_parameters():
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response.headers = {'Content-Disposition': 'attachment'}

    assert 'attachment' == response.content_disposition.type
    assert response.content_disposition.filename is None
    assert {} == response.content_disposition.parameters


def test_content_disposition_no_header():
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response.headers = {}

    assert response.content_disposition is None


def test_content_disposition_cache():
    response = ClientResponse('get', URL('http://def-cl-resp.org'))
    response.headers = {'Content-Disposition': 'attachment'}
    cd = response.content_disposition
    ClientResponse.headers = {'Content-Disposition': 'spam'}
    assert cd is response.content_disposition


def test_response_request_info():
    url = 'http://def-cl-resp.org'
    headers = {'Content-Type': 'application/json;charset=cp1251'}
    response = ClientResponse(
        'get', URL(url),
        request_info=RequestInfo(
            url,
            'get',
            headers
        )
    )
    assert url == response.request_info.url
    assert 'get' == response.request_info.method
    assert headers == response.request_info.headers


def test_response_request_info_empty():
    url = 'http://def-cl-resp.org'
    response = ClientResponse(
        'get', URL(url),
    )
    assert response.request_info is None


def test_request_info_in_exception():
    url = 'http://def-cl-resp.org'
    headers = {'Content-Type': 'application/json;charset=cp1251'}
    response = ClientResponse(
        'get',
        URL(url),
        request_info=RequestInfo(
            url,
            'get',
            headers
        )
    )
    response.status = 409
    response.reason = 'CONFLICT'
    with pytest.raises(aiohttp.ClientResponseError) as cm:
        response.raise_for_status()
    assert cm.value.request_info == response.request_info


def test_no_redirect_history_in_exception():
    url = 'http://def-cl-resp.org'
    headers = {'Content-Type': 'application/json;charset=cp1251'}
    response = ClientResponse(
        'get',
        URL(url),
        request_info=RequestInfo(
            url,
            'get',
            headers
        )
    )
    response.status = 409
    response.reason = 'CONFLICT'
    with pytest.raises(aiohttp.ClientResponseError) as cm:
        response.raise_for_status()
    assert () == cm.value.history


def test_redirect_history_in_exception():
    hist_url = 'http://def-cl-resp.org'
    url = 'http://def-cl-resp.org/index.htm'
    hist_headers = {'Content-Type': 'application/json;charset=cp1251',
                    'Location': url
                    }
    headers = {'Content-Type': 'application/json;charset=cp1251'}
    response = ClientResponse(
        'get',
        URL(url),
        request_info=RequestInfo(
            url,
            'get',
            headers
        )
    )
    response.status = 409
    response.reason = 'CONFLICT'

    hist_response = ClientResponse(
        'get',
        URL(hist_url),
        request_info=RequestInfo(
            url,
            'get',
            headers
        )
    )

    hist_response.headers = hist_headers
    hist_response.status = 301
    hist_response.reason = 'REDIRECT'

    response._history = [hist_response]
    with pytest.raises(aiohttp.ClientResponseError) as cm:
        response.raise_for_status()
    assert [hist_response] == cm.value.history


async def test_response_read_triggers_callback(loop, session):
    trace = mock.Mock()
    trace.send_response_chunk_received = make_mocked_coro()
    response_body = b'This is response'

    response = ClientResponse(
        'get', URL('http://def-cl-resp.org'),
        traces=[trace]
    )
    response._post_init(loop, session)

    def side_effect(*args, **kwargs):
        fut = loop.create_future()
        fut.set_result(response_body)
        return fut

    response.headers = {
        'Content-Type': 'application/json;charset=cp1251'}
    content = response.content = mock.Mock()
    content.read.side_effect = side_effect

    res = await response.read()
    assert res == response_body
    assert response._connection is None

    assert trace.send_response_chunk_received.called
    assert (
        trace.send_response_chunk_received.call_args ==
        mock.call(response_body)
    )
