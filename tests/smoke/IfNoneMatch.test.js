import { check, sleep, fail } from 'k6'
import { Httpx } from 'https://jslib.k6.io/httpx/0.0.1/index.js'

export let options = {
    vus: 1,
    iterations: 1,
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

    // make requests to /studies/{id}/shared-tags without If-None-Match header
    // to populate cache
    studyIds.forEach((studyId, index) => {
        const res = session.get(`/studies/${studyId}/shared-tags`)

        const checkOutput = check(res, {
            'Status is 200': (r) => r.status === 200,
            'Etag is not empty': (r) => r.headers['Etag'] !== '',
        })

        if (!checkOutput) {
            fail('Did not get 200 or Etag is empty')
        }

        testData.push({ studyId, eTag: res.headers['Etag'] })

        // sleep for 1 second
        sleep(1)
    })

    return { testData }
}

export default function (data) {
    data.testData.forEach(({ studyId, eTag }, index) => {
        // make call to shared-tags with if-none-match header
        const res = session.get(`/studies/${studyId}/shared-tags`, null, {
            headers: {
                'If-None-Match': eTag,
            }
        })

        // log request headers
        console.log(JSON.stringify(res.request.headers))

        // log status code
        console.log(res.status)

        // log response headers
        console.log(JSON.stringify(res.headers))

        // check status code is 304
        const checkOutput = check(res, {
            'With If-None-Match, status is 304': (r) => r.status === 304,
        })

        if (!checkOutput) {
            fail('Status is not 304')
        }

        // sleep for 1 second
        sleep(1)

        // make call to shared-tags without if-none-match header
        const res2 = session.get(`/studies/${studyId}/shared-tags`)

        // log request headers
        console.log(JSON.stringify(res2.request.headers))

        // log status code
        console.log(res2.status)

        // log response headers
        console.log(JSON.stringify(res2.headers))

        const checkOutput2 = check(res2, {
            'Without If-None-Match, status is 200': (r) => r.status === 200,
        })

        if (!checkOutput2) {
            fail('Status is not 200')
        }

        // sleep for 1 second
        sleep(1)
    })
}

export function teardown(data) {
    // nothing yet
}
