import orthanc


def cached_response(output, uri, **request):
    if not request['method'] in ['GET', 'HEAD']:
        raise Exception("Method not supported by cache plugin")

    print(f'Cached response for {uri} from the orthanc-cache-plugin')

    # Get the response from Rest API
    response = orthanc.RestApiGet(uri)

    # Add response to output
    output.AnswerBuffer(response, 'application/json')


orthanc.RegisterRestCallback('/system', cached_response)
