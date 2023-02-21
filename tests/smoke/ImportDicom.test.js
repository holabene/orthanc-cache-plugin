import { check, sleep } from 'k6'
import { Httpx } from 'https://jslib.k6.io/httpx/0.0.1/index.js'

export let options = {
    vus: 1,
    iterations: 1,
    duration: '2h',
    setupTimeout: '30m',
    teardownTimeout: '5m',
}

let files = []

for (let i = 1; i <= 100; i++) {
  let filePath = `../../.data/test/image${i.toString().padStart(3, "0")}.dcm`;
  files.push(open(filePath, 'b'));
}

const session = new Httpx({
    baseURL: 'http://orthanc:orthanc@localhost:8042',
})

export function setup() {
    // nothing yet
}

export default function (data) {
    // Import DICOM file
    files.forEach((file, index) => {
        const res = session.post('/instances', file)

        check(res, {
            'status is 200': (r) => r.status === 200,
        })

        const data = res.json()
        const instanceId = data['ID']
        console.log(`Uploaded instance #${index + 1} ${instanceId}`)
    })
}

export function teardown(data) {
    // nothing yet
}
