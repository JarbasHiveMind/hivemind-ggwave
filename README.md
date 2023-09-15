# HiveMind GGWave

Data over sound for HiveMind

- manually exchanged string [via browser](https://jarbashivemind.github.io/hivemind-ggwave/)
- with a [talking button](https://github.com/ggerganov/ggwave/discussions/27)

## Enrolling clients

pre-requisites:
- a device with a browser, eg a phone
- a hivemind-core device with mic and speaker, eg a mark2
- a voice satellite device with mic and speaker, eg a raspberry pi
- all devices need to be in audible range, they each need to be able to listen to sounds emitted by each other

workflow:
- when launching hivemind-core take note of the provided code, eg `HMPSWD:ce357a6b59f6b1f9`
- go to https://jarbashivemind.github.io/hivemind-ggwave and emit the code
- the voice satellite will decode the password, generate an access key and send it back via ggwave
- master adds a client with key + password, send an ack (containing host) via ggwave
- satellite devices get the ack then connect to received host

