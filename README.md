# Zero-Knowledge Zero Trust
Updated on Sep 5, 2025

# How to install

1. install `risc0`

# Running with batch

```bash
python batch_exec.py
```
--------------------------------------

Created by Dec 3, 2024

# Next Step

- [ ] get cycle before gen proof
- [ ] generate asm code by compiler
- [ ] imp policy code

# Experiment of benchmarking risc0

## Data metrics 

| Name                  | Cycle Num | Compile time | Gen time | Verify time |
| --------------------- | --------- | ------------ | -------- | ----------- |
| Matrix mul(2x3 * 3x4) | 9328      | 1m 23s       | 7.56s    | 30.8ms      |
| json lookup           | 11973     | 1m 21s       | 12.96s   | 31.53ms     |
| sha                   | 3288      | 1m 32s       | 7.77s    | 26.70ms     |
| digital-signature     | 5126      | 1m 54s       | 7.58s    | 31.87ms     |

# Codebase outline

## Process of generate proof

### Init

1. Generate Auth certificat(PK) and secret(SK) 
1. Generate user certificat(PK) and secret(SK)
1. Register user certificat(PK) to the Auth server with role
1. Depoly Auth server certificat(PK) to the client
1. Depoly Policy code signature to the client: `(hash(policy_code), sign(policy_code))`

### Process

1. User request Auth server to get a token(represent both role and user certificat) and `s0 = sign(token + role)`
1. User generate a proof with `policy(token, s0, role, policy_code, req)->Accept`
1. User send request to client: `(req, sign(token, req), proof(policy), token, role, s0, sign(token, time_stamp))`

### Verify on client

1. Verify `s0` -> know token and role is valid
1. Verify `proof(policy)` -> user with this token has access for this request
1. Verify `sign(token, req)` -> request is from the user with this token
1. Verify `sign(token, time_stamp)` -> request is not replayed

### Unsolved issue

- [ ] How to include policy code in the proof
