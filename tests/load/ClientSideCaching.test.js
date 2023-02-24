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

    studyIds.forEach((studyId, index) => {
        // count instance in study
        let res = session.get(`/studies/${studyId}/instances`)
        const instanceIds = res.json()
        const instanceCount = instanceIds.length
        console.log(`Study #${index + 1} ${studyId} has ${instanceCount} instances`)

        // make requests to /studies/{id}/shared-tags without cache control headers to populate cache
        res = session.get(`/studies/${studyId}/shared-tags`)

        const checkOutput = check(res, {
            'Status is 200': (r) => r.status === 200,
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
        // Make call to shared-tags with If-Modified-Since header
        const res = session.get(`/studies/${studyId}/shared-tags`, null, {
            headers: {
                'If-Modified-Since': lastModified
            }
        })

        // check status code is 200 or 304
        // depending if we test against a server with or without client side caching
        const checkOutput = check(res, {
            'Expected status' : (r) => r.status === port === 8042 ? 304 : 200,
        })

        // sleep for 1 second
        sleep(1)
    })
}

export function teardown(data) {
    // nothing yet
}
