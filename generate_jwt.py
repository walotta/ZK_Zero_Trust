#!/usr/bin/env python3

import json
import base64
import time
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import uuid

def base64url_encode(data):
    """Base64 URL-safe encode without padding"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def base64url_decode(data):
    """Base64 URL-safe decode with padding"""
    # Add padding if needed
    padding_len = 4 - (len(data) % 4)
    if padding_len != 4:
        data += '=' * padding_len
    return base64.urlsafe_b64decode(data)

def generate_rsa_key_pair(key_size=2048):
    """Generate RSA key pair with specified key size"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    return private_key

def save_private_key_to_file(private_key, filename="jwt_key"):
    """Save private key to PEM file"""
    pem_data = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    with open(filename, 'wb') as f:
        f.write(pem_data)

def load_private_key_from_file(filename="jwt_key"):
    """Load private key from PEM file"""
    if not os.path.exists(filename):
        return None

    with open(filename, 'rb') as f:
        pem_data = f.read()

    private_key = serialization.load_pem_private_key(
        pem_data,
        password=None,
        backend=default_backend()
    )

    return private_key

def get_or_create_private_key(filename="jwt_key", key_size=2048):
    """Get existing private key from file or create new one"""
    private_key = load_private_key_from_file(filename)

    if private_key is None:
        print(f"No existing key found. Generating new {key_size}-bit RSA key pair...")
        private_key = generate_rsa_key_pair(key_size)
        save_private_key_to_file(private_key, filename)
        print(f"Saved new private key to {filename}")
    else:
        print(f"Loaded existing private key from {filename}")

    return private_key

def private_key_to_jwk(private_key, key_id=None):
    """Convert RSA private key to JWK format"""
    # Get key components
    private_numbers = private_key.private_numbers()
    public_numbers = private_numbers.public_numbers

    # Convert to bytes and base64url encode
    def int_to_base64url(value):
        # Convert integer to bytes (big endian)
        byte_length = (value.bit_length() + 7) // 8
        bytes_val = value.to_bytes(byte_length, byteorder='big')
        return base64url_encode(bytes_val)

    # Generate deterministic key ID based on modulus if not provided
    if key_id is None:
        import hashlib
        modulus_bytes = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, byteorder='big')
        key_id = hashlib.sha256(modulus_bytes).hexdigest()[:32]

    # Calculate additional JWK parameters
    dp = private_numbers.d % (private_numbers.p - 1)
    dq = private_numbers.d % (private_numbers.q - 1)
    qi = pow(private_numbers.q, -1, private_numbers.p)

    jwk = {
        "alg": "RS256",
        "d": int_to_base64url(private_numbers.d),
        "dp": int_to_base64url(dp),
        "dq": int_to_base64url(dq),
        "e": int_to_base64url(public_numbers.e),
        "key_ops": ["sign"],
        "kty": "RSA",
        "n": int_to_base64url(public_numbers.n),
        "p": int_to_base64url(private_numbers.p),
        "q": int_to_base64url(private_numbers.q),
        "qi": int_to_base64url(qi),
        "use": "sig",
        "kid": key_id
    }

    return jwk, key_id

def create_jwt_payload():
    """Create JWT payload with hardcoded claims matching the Rust code"""
    current_time = int(time.time())

    payload = {
        "iss": "https://login.example.com/",
        "subject_id": "Julius Hibbert",
        "aud": "api://payments-service",
        "exp": current_time + 3600,  # 1 hour from now
        "iat": current_time,
        "auth_time": current_time - 100,
        "email": "user@example.com",
        "email_verified": True,
        "nonce": "3e4f0f67-bc5a-413d-b528-93fd1c71fd4e",
        "scope": "openid profile email offline_access",
        "roles": "admin",
    }

    return payload

def sign_jwt(private_key, key_id, payload):
    """Create and sign a JWT token"""
    # Create header
    header = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": key_id
    }

    # Encode header and payload
    header_b64 = base64url_encode(json.dumps(header, separators=(',', ':')))
    payload_b64 = base64url_encode(json.dumps(payload, separators=(',', ':')))

    # Create signing input
    signing_input = f"{header_b64}.{payload_b64}"

    # Sign the input
    signature = private_key.sign(
        signing_input.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    # Encode signature
    signature_b64 = base64url_encode(signature)

    # Create complete JWT
    jwt_token = f"{signing_input}.{signature_b64}"

    return jwt_token

def generate_rust_constants_include_bytes(jwk, key_id, jwt_token, private_key,
                                          jwt_rs_path="jwt.rs",
                                          bin_dir="keys"):
    """Generate Rust constants in the required format"""
    pub_numbers = private_key.public_key().public_numbers()
    n = pub_numbers.n.to_bytes((pub_numbers.n.bit_length() + 7) // 8, "big")
    e = pub_numbers.e.to_bytes((pub_numbers.e.bit_length() + 7) // 8, "big")

    os.makedirs(os.path.dirname(jwt_rs_path) or ".", exist_ok=True)
    os.makedirs(bin_dir, exist_ok=True)

    n_path = os.path.join(bin_dir, "modulus.bin")
    e_path = os.path.join(bin_dir, "exponent.bin")
    with open(n_path, "wb") as f:
        f.write(n)
    with open(e_path, "wb") as f:
        f.write(e)

    secret_key_json = json.dumps(jwk, indent=2)
    secret_key_rust = f'static SECRET_KEY: &str = r#"\n{secret_key_json}\n"#;'

    public_key_jwk = {
        "alg": "RS256",
        "e": base64url_encode(e),
        "key_ops": ["verify"],
        "kty": "RSA",
        "n": base64url_encode(n),
        "use": "sig",
        "kid": key_id,
    }
    public_key_json = json.dumps(public_key_jwk, separators=(', ', ': '))
    public_key_inner = public_key_json[1:-1]
    public_key_json_formatted = f' {{ {public_key_inner} }} '
    public_key_rust = f'static PUBLIC_KEY: &str = r#"{public_key_json_formatted}"#;'

    rust_code = f'''// Generated JWT constants (N/E via include_bytes!, no base64 at runtime)
{secret_key_rust}

{public_key_rust}

pub const JWT: &str = "{jwt_token}";
pub const KEY_ID: &str = "{key_id}";

pub static N_BYTES: &[u8] = include_bytes!("keys/modulus.bin");
pub static E_BYTES: &[u8] = include_bytes!("keys/exponent.bin");
'''
    with open(jwt_rs_path, "w") as f:
        f.write(rust_code)

def main():
    private_key = get_or_create_private_key("jwt_key", 2048)
    print("Converting to JWK format...")
    jwk, key_id = private_key_to_jwk(private_key)

    private_numbers = private_key.private_numbers()
    public_numbers = private_numbers.public_numbers
    n_bit_size = public_numbers.n.bit_length()
    print(f"Modulus (n) size: {n_bit_size} bits")

    print("Creating JWT payload...")
    payload = create_jwt_payload()

    print("Signing JWT...")
    jwt_token = sign_jwt(private_key, key_id, payload)

    print("Generating Rust constants (include_bytes)...")
    generate_rust_constants_include_bytes(jwk, key_id, jwt_token, private_key,
                                          jwt_rs_path="jwt.rs",
                                          bin_dir="keys")

    print("Generated jwt.rs and key bins successfully!")
    print(f"Key ID: {key_id}")
    print(f"JWT length: {len(jwt_token)} characters")
    print("\nGenerated constants:")
    print(f"MODULUS_BYTES length: {(public_numbers.n.bit_length() + 7) // 8}")
    print(f"EXPONENT_BYTES length: {(public_numbers.e.bit_length() + 7) // 8}")

if __name__ == "__main__":
    main()
