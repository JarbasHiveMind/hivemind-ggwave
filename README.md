# HiveMind GGWave

Data over sound for HiveMind

## Enrolling clients

- master emits a password via ggwave (periodically until an access key is received)
- devices wanting to connect grab password, generate an access key and send it via ggwave
- master adds a client with key + password, send an ack (containing host) via ggwave
- slave devices keep emitting message until they get the ack (then connect to received host)