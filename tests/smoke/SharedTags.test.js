import { check, sleep } from 'k6'
import { Httpx } from 'https://jslib.k6.io/httpx/0.0.1/index.js'

export let options = {
    vus: 1,
    iterations: 1,
    duration: '30s',
}

let studyIds = []

const session = new Httpx({
    baseURL: 'http://orthanc:orthanc@localhost:8042',
})

export function setup() {
    const res = session.get('/studies')
    studyIds = res.json()

    return { studyIds }
}

export default function (data) {
    // Make call to shared-tags
    data.studyIds.forEach((studyId, index) => {
        const res = session.get(`/studies/${studyId}/shared-tags`)

        check(res, {
            'status is 200': (r) => r.status === 200,
        })

        // log study ID and shared tags
        const data = res.json()
        console.log(`Study #${index + 1} ${studyId} ${JSON.stringify(data)}`)

        // log http headers
        console.log(JSON.stringify(res.headers))

        // sleep for 1 second
        sleep(1)
    })
}

export function teardown(data) {
    // nothing yet
}
