Orthanc Cache Plugin
====================

This is a python plugin for Orthanc to enable caching of responses and provide 
HTTP cache control headers to the REST API

**This is still a work in progress. Please use with caution. Contributions are welcome.**

## Server-side caching

The plugin will cache the responses to GET requests to the REST API. The cache 
is stored on disk in a directory `/var/lib/orthanc/cache`. 

Cache expiration is in 7 days since the cache was created.

Cache is done using the diskcache library, and the cache size is limited to 1GB,
using the LRU eviction policy. Cache is versioned using resource's `LastUpdate`
metadata.

Responses with binary data are not cached on the server-side, for example
`/instances/{id}/file` and `/instances/{id}/preview`, but the client-side
caching will still work.

## Client-side caching

The plugin will add HTTP cache control headers to the responses to GET requests.

```
Date: Mon, 20 Feb 2023 15:00:00 GMT
Last-Modified: Mon, 20 Feb 2023 14:00:00 GMT
ETag: 2e31e40208063db2c9edccf2ec012753
Cache-Control: max-age=604800, s-maxage=604800, public
Expires: Mon, 27 Feb 2023 15:00:00 GMT    
```

This allows clients to cache the responses and only request new data when the
cache expires. Also, if the client is behind a proxy, the proxy can cache the
response and serve it to other clients. CDN's can also cache the response.

Make sure to configure the proxy or CDN to always revalidate the cache with the server
before serving the cached response and always forward the http authentication headers
to the server, in order to get the correct response.

This plugin will return a 304 Not Modified response if the client has a valid cache.

## Server-side cache warmup

The plugin registers with the Orthanc event system and will warm the cache
when a new patient or study or series is stable.

At this point, the resource is safe to cache, so when the client requests the
resource, it will be served from the cache.

## Endpoints that are cached

The following endpoints are cached:

```
GET /instances/{id}/file
GET /instances/{id}/preview
GET /instances/{id}/tags
GET /instances/{id}/simplified-tags
GET /instances/{id}/metadata
GET /instances/{id}/raw
GET /instances/{id}/frames
GET /instances/{id}/frames/{frame}/*

GET patients/{id}/instances-tags
GET patients/{id}/shared-tags
GET patients/{id}/attachments
GET patients/{id}/media
GET patients/{id}/archive

GET studies/{id}/instances-tags
GET studies/{id}/shared-tags
GET studies/{id}/attachments
GET studies/{id}/media
GET studies/{id}/archive

GET series/{id}/instances-tags
GET series/{id}/shared-tags
GET series/{id}/attachments
GET series/{id}/media
GET series/{id}/archive
```

## Orthanc module API

See documentation at [/docs/orthanc-module-api.md](/docs/orthanc-module-api.md)
