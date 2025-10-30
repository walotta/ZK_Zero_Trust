# RSA Signature Verification

This example demonstrates how to verify an RS256 signature inside the RISC Zero zkVM using the same static key from the `jwt-validator` example. The host constructs a realistic authentication JWT containing common claims (issuer, subject, audience, expiry, scopes, roles, etc.), signs it with the embedded RSA private key, and the guest verifies the signature with the matching public key.

## Running the Example

From the `examples` workspace root run:

```bash
cargo run --release -p jwt-rsa-verify
```

The program will prove inside the zkVM that the signature validates against the fixed JWT and publish the decoded payload JSON to the journal when verification succeeds.
