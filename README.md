# HiveMind GGWave

Data over sound for HiveMind

## Enrolling clients

- master emits a password via ggwave (periodically until an access key is received)
- devices wanting to connect grab password, generate an access key and send it via ggwave
- master adds a client with key + password, send an ack (containing host) via ggwave
- slave devices get the ack then connect to received host

## out of band password emit

set password manually and enable silent mode (if silent mode is disabled the pswd is emitted evey 3 seconds)

- manually exchanged string [via browser](https://ggwave-js.ggerganov.com/)
- with a [talking button](https://github.com/ggerganov/ggwave/discussions/27)
