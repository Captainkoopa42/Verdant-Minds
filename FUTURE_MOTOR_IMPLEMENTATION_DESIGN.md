# Future Motor Implementation Design

## Status

This is documentation only. No part of this design is present in or imported by the active Verdant runtime.

Motor implementation is deferred until physical hardware, direct observation, and emergency-stop testing are available.

## Design objective

A future motor layer must close this causal loop without allowing cognition to bypass physical safety:

```text
workspace intention
→ Council authorization
→ independent safety gate
→ bounded hardware command
→ native device telemetry
→ observed physical consequence
→ expected-versus-observed discrepancy
→ evidence and learning
```

The motor driver must never be treated as a direct extension of the cognitive graph. It is a protected physical boundary.

## Required separation

A future implementation should contain three independent layers.

### 1. Verdant command-request layer

Verdant may propose an action but cannot directly write PWM, serial, CAN, GPIO, or motor-controller values.

A request should contain:

- requested operation;
- intended physical effect;
- expected sensory consequence;
- maximum duration;
- requested speed/force envelope;
- supporting evidence references;
- Council decision reference;
- uncertainty and stop conditions.

### 2. Independent safety controller

A separate microcontroller or isolated process should enforce hard limits even when Verdant is wrong or compromised.

It should own:

- current limits;
- voltage and temperature limits;
- maximum speed and acceleration;
- watchdog timeout;
- emergency stop;
- bumper/proximity override;
- command expiry;
- replay prevention;
- safe neutral state after communication loss.

Verdant must not be able to edit these limits during operation.

### 3. Hardware adapter

The adapter translates an authorized bounded command into the exact protocol required by a specific controller. It should return native status and fault data without assigning semantic meaning.

Each adapter should expose:

- device identity and firmware revision;
- command range and units;
- measured output state;
- fault bits;
- timestamp and sequence number;
- raw payload checksum;
- command acknowledgement;
- physical stop confirmation.

## Authorization certificate

A hardware command should require a one-use certificate containing:

- operation ID;
- Council decision hash;
- device ID;
- exact allowed command range;
- issue time and expiration;
- nonce;
- maximum execution time;
- required stop conditions;
- signature or message-authentication code.

The safety controller should reject missing, altered, expired, replayed, or out-of-range certificates.

## Native evidence preservation

The future layer should preserve four separate records:

1. **Intention** — what Verdant expected to change.
2. **Issued command** — exact values sent after safety limiting.
3. **Native result** — encoder/current/fault/controller bytes exactly as returned.
4. **Observed world consequence** — synchronized camera, audio, and other sensory changes.

These records must remain distinct. A successful command acknowledgement is not proof that the intended physical outcome occurred.

## Prediction discrepancy

The later learning record should compare expected and observed consequences:

```text
error = distance(expected consequence, observed consequence)
```

The discrepancy must be recorded without automatically deciding why it occurred. Possible causes such as slip, obstruction, low power, mechanical failure, poor prediction, or sensor error remain competing hypotheses until supported.

## Initial hardware scope

The first implementation should be deliberately small:

- one differential-drive platform;
- two motor channels;
- wheel encoders;
- current sensing;
- one IMU;
- bumper or short-range stop sensor;
- physical emergency-stop switch;
- independent safety microcontroller.

No arm, gripper, autonomous docking, high-force mechanism, or unrestricted navigation should be included in the first hardware phase.

## Required tests before connection to Verdant

The hardware layer should pass independently:

- command range enforcement;
- expired-command rejection;
- replayed-command rejection;
- altered-certificate rejection;
- watchdog stop;
- communication-loss stop;
- emergency-stop response;
- overcurrent stop;
- thermal stop;
- sensor-disagreement handling;
- incorrect encoder direction detection;
- stuck-output detection;
- safe startup and shutdown;
- deterministic log reconstruction.

## Required tests after integration

Only after independent safety tests pass should Verdant be connected. Integration tests should verify:

- no command without a valid Council decision;
- no command outside the certificate envelope;
- exact command and telemetry provenance;
- expected-versus-observed comparison;
- failure preserved rather than overwritten;
- action history survives checkpoint recovery;
- cognition cannot modify hard safety limits;
- workspace expiry cannot leave a command running;
- a stopped or crashed Verdant process leaves hardware neutral.

## Implementation sequence when hardware exists

1. Select the chassis, controller, motors, encoders, power system, and safety microcontroller.
2. Document exact electrical and protocol limits.
3. Build and test the safety controller without Verdant.
4. Build a read-only telemetry logger.
5. Validate timestamps, sequence numbers, and native payload archives.
6. Add one bounded command type.
7. Add authorization certificates and replay protection.
8. Connect Council authorization.
9. Add synchronized visual consequence recording.
10. Run tethered low-speed tests with a physical emergency stop.
11. Add prediction-discrepancy records.
12. Permit learning only after the physical record is trustworthy.

## Non-negotiable boundary

The future Ethics King and Council are cognitive safeguards, not electrical safety devices. Hard physical limits must remain outside Verdant's authority.
