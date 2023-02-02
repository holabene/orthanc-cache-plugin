import { check, sleep, fail } from 'k6'
import { Httpx } from 'https://jslib.k6.io/httpx/0.0.1/index.js'

export let options = {
    vus: 100,
    duration: '10s',
}

let studyIds = []

const session = new Httpx({
    baseURL: 'http://orthanc:orthanc@localhost:8042',
})

export function setup() {
    const res = session.get('/studies')
    studyIds = res.json()

    const testData = []

    // make requests to /studies/{id}/shared-tags without If-Match header
    // to populate cache
    studyIds.forEach((studyId, index) => {
        const res = session.get(`/studies/${studyId}/shared-tags`)

        const checkOutput = check(res, {
            'Status is 200': (r) => r.status === 200,
            'ETag is not empty': (r) => r.headers['Etag'] !== '',
        })

        if (!checkOutput) {
            fail('Did not get 200 or ETag is empty')
        }

        testData.push({ studyId, eTag: res.headers['Etag'] })

        // sleep for 1 second
        sleep(1)
    })

    return { testData }
}

export default function (data) {
    data.testData.forEach(({ studyId, eTag }, index) => {
        // make call to shared-tags with if-match header
        const res = session.get(`/studies/${studyId}/shared-tags`, null, {
            headers: {
                'If-Match': eTag,
            }
        })

        // log request headers
        console.log(JSON.stringify(res.request.headers))

        // check status code is 304
        const checkOutput = check(res, {
            'with if-match, status is 304': (r) => r.status === 304,
        })

        // log status code
        console.log(res.status)

        // log response headers
        console.log(JSON.stringify(res.headers))

        if (!checkOutput) {
            fail('status is not 304')
        }

        // sleep for 1 second
        sleep(1)

        // make call to shared-tags without if-match header
        const res2 = session.get(`/studies/${studyId}/shared-tags`)

        // log request headers
        console.log(JSON.stringify(res2.request.headers))

        const checkOutput2 = check(res2, {
            'without if-match, status is 200': (r) => r.status === 200,
        })

        // log status code
        console.log(res2.status)

        // log response headers
        console.log(JSON.stringify(res2.headers))

        if (!checkOutput2) {
            fail('status is not 200')
        }

        // sleep for 1 second
        sleep(1)
    })
}

export function teardown(data) {
    // nothing yet
}
