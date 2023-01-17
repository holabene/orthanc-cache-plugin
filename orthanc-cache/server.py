import orthanc
import hashlib
import urllib.parse
from functools import lru_cache
from datetime import datetime


# Get timezone offset
@lru_cache(maxsize=32)
def timezone_offset():
    utc = datetime.strptime(orthanc.RestApiGet('/tools/now').decode('utf-8'), '%Y%m%dT%H%M%S')
    local = datetime.strptime(orthanc.RestApiGet('/tools/now-local').decode('utf-8'), '%Y%m%dT%H%M%S')
    diff = divmod(int((local - utc).seconds), 3600)[0]

    return '{:+03d}00'.format(diff)


def cached_response(output, uri, **request):
    """
    Methods available in output
    'AnswerBuffer', 'CompressAndAnswerJpegImage', 'CompressAndAnswerPngImage', 'Redirect', 'SendHttpStatus',
    'SendHttpStatusCode', 'SendMethodNotAllowed', 'SendMultipartItem', 'SendUnauthorized', 'SetCookie',
    'SetHttpErrorDetails', 'SetHttpHeader', 'StartMultipartAnswer'
    """
    if not request['method'] in ['GET', 'HEAD']:
        output.SendMethodNotAllowed(request['method'])
        return None

    orthanc.LogInfo(f'Cached response for {uri} from the orthanc-cache-plugin')

    # Check last update
    level, uuid = request['groups']
    meta = 'ReceptionDate' if level == 'instances' else 'LastUpdate'
    last_update = datetime.strptime(
        orthanc.RestApiGet(f'/{level}/{uuid}/metadata/{meta}').decode('utf-8') + timezone_offset(),
        '%Y%m%dT%H%M%S%z'
    )

    last_modified = last_update.strftime('%a, %d %b %Y %H:%M:%S %z')

    # Get API response
    querystring = urllib.parse.urlencode(request['get'])
    response = orthanc.RestApiGet(f'{uri}?{querystring}')

    # Calculate ETag
    # TODO: optimize in order to not make Rest API call
    e_tag = hashlib.md5(response).hexdigest()

    # Add cache control
    output.SetHttpHeader('Date', datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000'))
    output.SetHttpHeader('Last-Modified', last_modified)
    output.SetHttpHeader('ETag', e_tag)

    # Validate request
    if 'if-match' in request['headers']:
        if request['headers']['if-match'] == e_tag:
            output.SendHttpStatus(304)
            return None
    elif 'if-modified-since' in request['headers']:
        modified_since = datetime.strptime(request['headers']['if-modified-since'], '%a, %d %b %Y %H:%M:%S %z')

        if modified_since >= last_update:
            output.SendHttpStatus(304)
            return None

    # Passthrough
    output.AnswerBuffer(response, 'application/json')


orthanc.RegisterRestCallback('/(patients|studies|series|instances)/([-a-z0-9]+).*', cached_response)
