import orthanc
import hashlib
import urllib.parse
from functools import lru_cache
from datetime import datetime, timedelta
from pytz import timezone

RFC_822 = '%a, %d %b %Y %H:%M:%S GMT'


@lru_cache(maxsize=32)
def orthanc_timezone_offset():
    """
    Get Orthanc timezone offset in seconds
    """
    utc = datetime.strptime(orthanc.RestApiGet('/tools/now').decode('utf-8'), '%Y%m%dT%H%M%S')
    local = datetime.strptime(orthanc.RestApiGet('/tools/now-local').decode('utf-8'), '%Y%m%dT%H%M%S')
    return divmod(int((local - utc).seconds), 3600)[0]


def resource_last_update(uuid, level):
    """
    Get last update date of a resource
    """
    meta = 'ReceptionDate' if level == 'instances' else 'LastUpdate'
    meta_last_update = orthanc.RestApiGet(f'/{level}/{uuid}/metadata/{meta}').decode('utf-8')

    # timezone offset in seconds
    offset = orthanc_timezone_offset()

    # parse last update in YYYYMMDDTHHMMSS, add offset, convert to UTC
    last_update = datetime.strptime(meta_last_update, '%Y%m%dT%H%M%S') + timedelta(seconds=offset)
    last_update = last_update.astimezone(timezone('UTC'))

    return last_update


def cached_api_response(uri):
    # TODO: add cache for slow endpoints
    return orthanc.RestApiGet(uri)


def rest_callback(output, uri, **request):
    """
    Methods available in output
    'AnswerBuffer', 'CompressAndAnswerJpegImage', 'CompressAndAnswerPngImage', 'Redirect', 'SendHttpStatus',
    'SendHttpStatusCode', 'SendMethodNotAllowed', 'SendMultipartItem', 'SendUnauthorized', 'SetCookie',
    'SetHttpErrorDetails', 'SetHttpHeader', 'StartMultipartAnswer'
    """
    # Validate request method
    if not request['method'] in ['GET', 'HEAD']:
        # pass through
        orthanc.LogInfo(f'Pass through {uri} from the orthanc-cache-plugin')
        return None

    # Check last update
    level, uuid = request['groups']
    last_update = resource_last_update(uuid, level)

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
            orthanc.LogInfo('Cache hit If-Modified-Since')

            # send 304
            output.SendHttpStatusCode(304)

            return None

    # Get API response
    querystring = urllib.parse.urlencode(request['get'])

    # Build uri with querystring
    api_uri = f'{uri}?{querystring}' if querystring else uri
    response = cached_api_response(api_uri)

    # Calculate Etag
    e_tag = hashlib.md5(response).hexdigest()

    # Validate request against If-Match header
    if 'if-match' in request['headers']:
        if request['headers']['if-match'] == e_tag:
            # log cache hit
            orthanc.LogInfo('Cache hit If-Match')

            # send 304
            output.SendHttpStatusCode(304)

            return None

    # Build response with cache control headers
    now = datetime.now(timezone('UTC'))
    ttl = 86400 * 7  # 7 days

    output.SetHttpHeader('Date', now.strftime(RFC_822))
    output.SetHttpHeader('Last-Modified', last_update.strftime(RFC_822))
    output.SetHttpHeader('Etag', e_tag)
    output.SetHttpHeader('Cache-Control', f'max-age={ttl}, s-maxage={ttl}')
    output.SetHttpHeader('Expires', (now + timedelta(seconds=ttl)).strftime(RFC_822))

    # log cache miss
    orthanc.LogInfo('Cache miss')

    # if request method is HEAD, return 200
    if request['method'] == 'HEAD':
        output.SendHttpStatusCode(200)
        return None

    # send response with content type
    # TODO: add support for other content types
    content_type = request['headers']['accept'] if 'accept' in request['headers'] else 'application/json'
    output.AnswerBuffer(response, content_type)


orthanc.RegisterRestCallback('/(patients|studies|series|instances)/([-a-z0-9]+).*', rest_callback)
