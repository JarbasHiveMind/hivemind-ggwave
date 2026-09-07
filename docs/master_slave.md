# Master and slave

The library provides two roles. Both are thin primitives — orchestration is the
caller's job.

## `GGWaveMaster` (hub side)

Runs on the `hivemind-core` device. Listens for `HMKEY:` and drives the pairing:

- Holds the pairing **password** (provided, or generated).
- Broadcasts `HMPSWD:<password>` so satellites can hear it (unless in silent
  mode — see below).
- On `HMKEY:<key>`, registers the satellite as a client and emits `HMHOST:<ip>`
  so the satellite learns where to connect.

Registration itself is delegated to the caller via a callback: the master hands
back the new access key and password, and the caller persists the client in
`hivemind-core`.

### Silent mode

When silent mode is enabled the master does **not** broadcast the password
automatically. The caller displays the code in a UI and emits it on user demand
(e.g. a button press). This transmits the password once rather than looping, which
is the recommended production behaviour. The browser tool provides the same
"emit on demand" capability when the hub has no speaker.

## `GGWaveSlave` (satellite side)

Runs on the unpaired satellite. Listens for `HMPSWD:` and `HMHOST:`:

- On `HMPSWD:<password>`, stores the password, generates an access key, and emits
  `HMKEY:<key>` back to the hub.
- On `HMHOST:<ip>`, saves the `NodeIdentity` (password, key, host) and stops.

Once the identity is saved the satellite has everything it needs to open the
encrypted HiveMind connection to the hub.
