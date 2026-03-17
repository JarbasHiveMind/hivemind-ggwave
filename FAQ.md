
# FAQ — hivemind-ggwave

## What is GGWave?
GGWave is a tiny data-over-sound library. `hivemind-ggwave` uses it to allow "audio pairing" between a HiveMind hub and a new satellite.

## How do I use audio pairing?
1. The hub (Master) starts `GGWaveMaster` and begins chirping the password.
2. The satellite (Slave) starts `GGWaveSlave` and listens for the chirp.
3. Once received, the satellite chirps back its generated access key.
4. The hub registers the key and chirps the connection details (URL/Host).
5. The satellite saves the identity and connects.

## Does it require special hardware?
It requires a microphone and a speaker on both ends.

## Is it secure?
The password is transmitted over sound, which can be overheard. It is intended for convenient initial pairing in a controlled environment. Once paired, standard HiveMind encryption (AES-256) is used for the network connection.
