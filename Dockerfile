FROM osimis/orthanc

RUN pip install pytz

RUN mkdir /orthanc-cache-plugin
COPY orthanc-cache/* /orthanc-cache/