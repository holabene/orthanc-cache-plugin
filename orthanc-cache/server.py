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
        return

    orthanc.LogInfo(f'Cached response for {uri} from the orthanc-cache-plugin')

    # Check last update
    level, uuid = request['groups']
    meta = 'ReceptionDate' if level == 'instances' else 'LastUpdate'
    last_update = orthanc.RestApiGet(f'/{level}/{uuid}/metadata/{meta}').decode('utf-8')

    last_modified = datetime\
        .strptime(last_update, '%Y%m%dT%H%M%S')\
        .strftime(f'%a, %d %b %Y %H:%M:%S {timezone_offset()}')

    # Get API response
    querystring = urllib.parse.urlencode(request['get'])
    response = orthanc.RestApiGet(f'{uri}?{querystring}')

    # Calculate ETag
    # TODO: optimize in order to not make Rest API call
    e_tag = hashlib.md5(response).hexdigest()

    # Add cache control
    output.SetHttpHeader('Last-Modified', last_modified)
    output.SetHttpHeader('ETag', e_tag)

    # Passthrough
    output.AnswerBuffer(response, 'application/json')


orthanc.RegisterRestCallback('/(patients|studies|series|instances)/([-a-z0-9]+).*', cached_response)
