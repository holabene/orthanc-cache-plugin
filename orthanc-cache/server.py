import urllib.parse

import orthanc
import re
from datetime import datetime


def cached_response(output, uri, **request):
    """
    Methods available in output
    'AnswerBuffer', 'CompressAndAnswerJpegImage', 'CompressAndAnswerPngImage', 'Redirect', 'SendHttpStatus',
    'SendHttpStatusCode', 'SendMethodNotAllowed', 'SendMultipartItem', 'SendUnauthorized', 'SetCookie',
    'SetHttpErrorDetails', 'SetHttpHeader', 'StartMultipartAnswer''AnswerBuffer',
    'CompressAndAnswerJpegImage', 'CompressAndAnswerPngImage', 'Redirect',
    'SendHttpStatus', 'SendHttpStatusCode', 'SendMethodNotAllowed', 'SendMultipartItem',
    'SendUnauthorized', 'SetCookie', 'SetHttpErrorDetails', 'SetHttpHeader', 'StartMultipartAnswer'
    """
    if not request['method'] in ['GET', 'HEAD']:
        output.SendMethodNotAllowed(request['method'])
        return

    orthanc.LogInfo(f'Cached response for {uri} from the orthanc-cache-plugin')

    # Check last update
    level, uuid = request['groups']
    meta = 'ReceptionDate' if level == 'instances' else 'LastUpdate'
    last_update = orthanc.RestApiGet(f'/{level}/{uuid}/metadata/{meta}').decode('utf-8')

    # TODO: ensure correct timezone
    last_modified = datetime.strptime(last_update, '%Y%m%dT%H%M%S').strftime('%a, %d %b %Y %H:%M:%S')

    # Add cache control
    output.SetHttpHeader('Last-Modified', last_modified)

    # Passthrough
    querystring = urllib.parse.urlencode(request['get'])
    output.AnswerBuffer(orthanc.RestApiGet(f'{uri}?{querystring}'), 'application/json')


orthanc.RegisterRestCallback('/(patients|studies|series|instances)/([-a-z0-9]+).*', cached_response)
