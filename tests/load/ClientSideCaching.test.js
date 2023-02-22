import { check, sleep, fail } from 'k6'
import { Httpx } from 'https://jslib.k6.io/httpx/0.0.1/index.js'

export let options = {
    vus: 100,
    duration: '10s',
}

let studyIds = []
let port = __ENV.PORT || 8042

const session = new Httpx({
    baseURL: `http://orthanc:orthanc@localhost:${port}`,
})

export function setup() {
    console.log(`Testing using baseURL: ${session.baseURL}`)


    const res = session.get('/studies')
    studyIds = res.json()

    const testData = []

    // make requests to /studies/{id}/shared-tags without If-Modified-Since header
    // to populate cache
    studyIds.forEach((studyId, index) => {
        const res = session.get(`/studies/${studyId}/shared-tags`)

        const checkOutput = check(res, {
            'Status is 200 or 304': (r) => [200, 304].includes(r.status),
            'Last-Modified is not empty': (r) => r.headers['Last-Modified'] !== '',
        })

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

        // check status code is 200 or 304
        const checkOutput = check(res, {
            'With If-Modified-Since to current time, status is 200 or 304': (r) => [200, 304].includes(r.status)
        })

        // sleep for 1 second
        sleep(1)
    })
}

export function teardown(data) {
    // nothing yet
}
