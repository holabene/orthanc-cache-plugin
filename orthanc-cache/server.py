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

    # Get the response from Rest API
    response = orthanc.RestApiGet(uri).decode('utf-8')

    # Parse uri
    path = re.match('/studies/([-a-z0-9]+)', uri)
    uuid = path[1]

    # Check last update
    # TODO: check timezone
    last_update = orthanc.RestApiGet(f'/studies/{uuid}/metadata/LastUpdate').decode('utf-8')
    last_modified = datetime.strptime(last_update, '%Y%m%dT%H%M%S').strftime('%a, %d %b %Y %H:%M:%S')

    # Add cache control
    output.SetHttpHeader('Last-Modified', last_modified)

    # Add response to output
    output.AnswerBuffer(response, 'application/json')


orthanc.RegisterRestCallback('/studies/([-a-z0-9]+)', cached_response)
