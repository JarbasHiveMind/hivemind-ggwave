# HiveMind GGWave

Data over sound for HiveMind

- manually exchanged string [via browser](https://jarbashivemind.github.io/hivemind-ggwave/)
- with a [talking button](https://github.com/ggerganov/ggwave/discussions/27)

## Enrolling clients

- when launching hivemind-core take note of the provided code, eg `HMPSWD:ce357a6b59f6b1f9`
- go to https://jarbashivemind.github.io/hivemind-ggwave and emit the code from any device in audible range of your satellite
- the voice satellite will decode the password, generate an access key and send it back via ggwave
- master adds a client with key + password, send an ack (containing host) via ggwave
- satellite devices get the ack then connect to received host

