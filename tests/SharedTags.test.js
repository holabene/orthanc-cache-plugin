import { check, sleep } from 'k6'
import { Httpx } from 'https://jslib.k6.io/httpx/0.0.1/index.js'

export let options = {
    vus: 100,
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
    })
}

export function teardown(data) {
    // nothing yet
}
