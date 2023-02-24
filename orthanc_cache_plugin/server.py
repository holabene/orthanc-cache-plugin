import json
import re

import orthanc
import hashlib
import urllib.parse
from functools import lru_cache
from datetime import datetime, timedelta
from pytz import timezone
import diskcache as dc

RFC_822 = '%a, %d %b %Y %H:%M:%S GMT'
ORTHANC_DATE = '%Y%m%dT%H%M%S'


@lru_cache(maxsize=32)
def orthanc_timezone_offset() -> int:
    """
    Get Orthanc timezone offset in seconds
    :return: timezone offset in seconds
    """
    utc = datetime.strptime(orthanc.RestApiGet('/tools/now').decode('utf-8'), ORTHANC_DATE)
    local = datetime.strptime(orthanc.RestApiGet('/tools/now-local').decode('utf-8'), ORTHANC_DATE)

    return divmod(int((local - utc).seconds), 3600)[0]


def resource_last_update(uuid, level) -> datetime:
    """
    Get last update date of a resource
    :param uuid: resource uuid
    :param level: 'patients', 'studies', 'series', 'instances'
    :return: last update date
    """
    meta = 'ReceptionDate' if level == 'instances' else 'LastUpdate'
    meta_last_update = orthanc.RestApiGet(f'/{level}/{uuid}/metadata/{meta}').decode('utf-8')

    # timezone offset in seconds
    offset = orthanc_timezone_offset()

    # parse last update in ORTHANC_DATE format, add offset, convert to UTC
    last_update = datetime.strptime(meta_last_update, ORTHANC_DATE) + timedelta(seconds=offset)
    last_update = last_update.astimezone(timezone('UTC'))

    return last_update


def cached_api_response(uri: str, version: str) -> bytes:
    """
    Get API response from cache
    :param uri: API uri
    :param version: cache version
    :return: API response
    """

    # Cache directory
    cache_dir = '/var/lib/orthanc/cache'

    # Cache size
    cache_size = 1024 ** 3  # 1GB

    # Cache expiration
    cache_expiration = 86400 * 7  # 7 days

    # Cache
    cache = dc.Cache(cache_dir, size_limit=cache_size, eviction_policy='least-recently-used', expire=cache_expiration)

    cache_key = f'{uri}#{version}'

    # Get response from cache
    if cache_key in cache:
        # log cache hit
        orthanc.LogInfo(f'Cache hit [response] {cache_key}')
        return cache[cache_key]

    # Log cache miss
    orthanc.LogInfo(f'Cache miss [response] {cache_key}')

    # Invalidate cache matching uri
    for key in cache:
        if key.startswith(uri):
            del cache[key]

    # Get response from API
    response = orthanc.RestApiGet(uri)

    # Add response to cache if not empty and not binary
    if response and not response.startswith(b'\x00'):
        cache[cache_key] = response

    return response


def detect_content_type(response) -> str:
    """
    Detect content type from response
    :param response:
    :return: mime type
    """
    # detect if supported binary response
    if response.startswith(b'\x89PNG'):
        return 'image/png'
    elif response.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    elif response.startswith(b'\x1f\x8b\x08'):
        return 'application/gzip'
    elif response.startswith(b'\x42\x5a\x68'):
        return 'application/x-bzip2'
    elif response.startswith(b'\x50\x4b\x03\x04'):
        return 'application/zip'

    # detect if text response
    try:
        response.decode('utf-8')

        # detect if json response
        try:
            json.loads(response)
            return 'application/json'
        except json.JSONDecodeError:
            pass

        return 'text/plain'
    except UnicodeDecodeError:
        pass

    return 'application/octet-stream'


def on_change_callback(change_type, level, uuid):
    """
    Warm up cache when a new study is added
    :param change_type: change type
    :param level: resource level
    :param uuid: resource uuid
    """
    path = {0: 'patients', 1: 'studies', 2: 'series', 3: 'instances'}[level] if level < 4 else None

    orthanc.LogInfo(f'Change detected: {change_type} {level} {uuid}')

    # react on stable patient/study/series change type
    if change_type in [orthanc.ChangeType.STABLE_PATIENT, orthanc.ChangeType.STABLE_STUDY, orthanc.ChangeType.STABLE_SERIES]:
        # get last update date
        last_update = resource_last_update(uuid, path)
        version = last_update.strftime(ORTHANC_DATE)

        # warm up cache for instances-tags
        orthanc.LogInfo(f'Warming up cache for /{path}/{uuid}/instances-tags')
        cached_api_response(f'/{path}/{uuid}/instances-tags', version)
        cached_api_response(f'/{path}/{uuid}/instances-tags?short', version)
        cached_api_response(f'/{path}/{uuid}/instances-tags?simplify', version)

        # warm up cache for shared-tags
        orthanc.LogInfo(f'Warming up cache for /{path}/{uuid}/shared-tags')
        cached_api_response(f'/{path}/{uuid}/shared-tags', version)
        cached_api_response(f'/{path}/{uuid}/shared-tags?short', version)
        cached_api_response(f'/{path}/{uuid}/shared-tags?simplify', version)

        # warm up cache for attachments
        orthanc.LogInfo(f'Warming up cache for /{path}/{uuid}/attachments')
        cached_api_response(f'/{path}/{uuid}/attachments', version)
        cached_api_response(f'/{path}/{uuid}/attachments?full', version)


def rest_callback(output, uri, **request):
    """
    REST callback
    See Class RestOutput for more information in docs/orthanc-module-api.md
    :param output: output object
    :param uri: uri
    :param request: request
    """
    # Build uri with querystring
    querystring = urllib.parse.urlencode(request['get']) if 'get' in request else ''
    api_uri = f'{uri}?{querystring}' if querystring else uri

    # Validate request method
    # Only GET and HEAD are supported
    if not request['method'] in ['GET', 'HEAD']:
        output.SendMethodNotAllowed()
        return None

    # Parse uri for resource level and uuid using regex
    level, uuid = re.match(r'^/([a-z]+)/([0-9a-f-]+)', uri).groups()

    # Get last update metadata from resource
    # If resource not found, return 404
    try:
        last_update = resource_last_update(uuid, level)
    except orthanc.OrthancException as e:
        # If resource not found
        if e.args[0] == orthanc.ErrorCode.UNKNOWN_RESOURCE:
            output.SendHttpStatusCode(404)
            return None
        else:
            raise e

    # Validate cache against If-Modified-Since header
    if 'if-modified-since' in request['headers']:
        # parse If-Modified-Since header to datetime in UTC
        modified_since = datetime.strptime(request['headers']['if-modified-since'], RFC_822).astimezone(timezone('UTC'))

        # log modified since with timezone
        orthanc.LogInfo(f'If-Modified-Since: {modified_since.strftime("%Y-%m-%d %H:%M:%S %z")}')

        # log last update with timezone
        orthanc.LogInfo(f'Last-Update: {last_update.strftime("%Y-%m-%d %H:%M:%S %z")}')

        if modified_since >= last_update:
            # log cache hit
            orthanc.LogInfo(f'Cache hit [If-Modified-Since] {api_uri}')

            # send 304
            output.SendHttpStatusCode(304)
            return None

    # Get API response
    response = cached_api_response(api_uri, last_update.strftime(ORTHANC_DATE))

    # Calculate Etag
    e_tag = hashlib.md5(response).hexdigest()

    # Validate request against If-None-Match header
    if 'if-none-match' in request['headers']:
        if request['headers']['if-none-match'] == e_tag:
            # log cache hit
            orthanc.LogInfo(f'Cache hit [If-None-Match] {api_uri}')

            # send 304
            output.SendHttpStatusCode(304)
            return None

    # Build response with cache control headers
    now = datetime.now(timezone('UTC'))
    ttl = 86400 * 7  # 7 days

    output.SetHttpHeader('Date', now.strftime(RFC_822))
    output.SetHttpHeader('Last-Modified', last_update.strftime(RFC_822))
    output.SetHttpHeader('Etag', e_tag)
    output.SetHttpHeader('Cache-Control', f'max-age={ttl}, s-maxage={ttl}, public')
    output.SetHttpHeader('Expires', (now + timedelta(seconds=ttl)).strftime(RFC_822))

    # Log cache miss
    orthanc.LogInfo(f'Cache miss [cache-control] {api_uri}')

    # If request method is HEAD, return 200
    if request['method'] == 'HEAD':
        output.SendHttpStatusCode(200)
        return None

    # Send response with content type
    output.AnswerBuffer(response, detect_content_type(response))


def enable_cache_plugin():
    orthanc.RegisterRestCallback('/(patients|studies|series)/([-a-z0-9]+)/archive', rest_callback)
    orthanc.RegisterRestCallback('/(patients|studies|series)/([-a-z0-9]+)/attachments', rest_callback)
    orthanc.RegisterRestCallback('/(patients|studies|series)/([-a-z0-9]+)/instances-tags', rest_callback)
    orthanc.RegisterRestCallback('/(patients|studies|series)/([-a-z0-9]+)/media', rest_callback)
    orthanc.RegisterRestCallback('/(patients|studies|series)/([-a-z0-9]+)/shared-tags', rest_callback)

    orthanc.RegisterRestCallback('/instances/([-a-z0-9]+)/file', rest_callback)
    orthanc.RegisterRestCallback('/instances/([-a-z0-9]+)/frames', rest_callback)
    orthanc.RegisterRestCallback('/instances/([-a-z0-9]+)/frames/(.+)', rest_callback)
    orthanc.RegisterRestCallback('/instances/([-a-z0-9]+)/header', rest_callback)
    orthanc.RegisterRestCallback('/instances/([-a-z0-9]+)/pdf', rest_callback)
    orthanc.RegisterRestCallback('/instances/([-a-z0-9]+)/preview', rest_callback)
    orthanc.RegisterRestCallback('/instances/([-a-z0-9]+)/raw', rest_callback)
    orthanc.RegisterRestCallback('/instances/([-a-z0-9]+)/simplified-tags', rest_callback)
    orthanc.RegisterRestCallback('/instances/([-a-z0-9]+)/tags', rest_callback)

    orthanc.RegisterOnChangeCallback(on_change_callback)