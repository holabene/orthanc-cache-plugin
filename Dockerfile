FROM osimis/orthanc

RUN pip install pytz
RUN pip install diskcache

RUN mkdir /orthanc-cache-plugin
COPY orthanc-cache/* /orthanc-cache/