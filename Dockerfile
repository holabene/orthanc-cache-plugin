FROM osimis/orthanc

RUN mkdir /orthanc-cache-plugin
COPY orthanc-cache/* /orthanc-cache/