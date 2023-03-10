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

    // make requests to /studies/{id}/shared-tags without If-Modified-Since header
    // to populate cache
    studyIds.forEach((studyId, index) => {
        const res = session.get(`/studies/${studyId}/shared-tags`)

        const checkOutput = check(res, {
            'Status is 200': (r) => r.status === 200,
            'Last-Modified is not empty': (r) => r.headers['Last-Modified'] !== '',
        })

        if (!checkOutput) {
            fail('Did not get 200 or Last-Modified is empty')
        }

        testData.push({ studyId, lastModified: res.headers['Last-Modified'] })

        // sleep for 1 second
        sleep(1)
    })

    return { testData }
}

export default function (data) {
    data.testData.forEach(({ studyId, lastModified }, index) => {
        // Make call to shared-tags with If-Modified-Since header to current time
        const res = session.get(`/studies/${studyId}/shared-tags`, null, {
            headers: {
                'If-Modified-Since': new Date().toUTCString(),
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
            'With If-Modified-Since to current time, status is 304': (r) => r.status === 304,
        })

        if (!checkOutput) {
            fail(`Study #${index + 1} ${studyId} ${JSON.stringify(res.json())}`)
        }

        // sleep for 1 second
        sleep(1)

        // Make call to shared-tags with If-Modified-Since header to last modified time less 1 second
        const res2 = session.get(`/studies/${studyId}/shared-tags`, null, {
            headers: {
                'If-Modified-Since': new Date(new Date(lastModified).getTime() - 1000).toUTCString(),
            }
        })

        // log request headers
        console.log(JSON.stringify(res2.request.headers))

        // log status code
        console.log(res2.status)

        // log response headers
        console.log(JSON.stringify(res2.headers))

        // check status code is 200
        const checkOutput2 = check(res2, {
            'With If-Modified-Since before last modified date, status is 200': (r) => r.status === 200,
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
