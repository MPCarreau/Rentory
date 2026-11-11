"""Generate local RS256 signing keys. Never commit private.pem."""
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

folder = Path("keys")
folder.mkdir(exist_ok=True)
private_file = folder / "private.pem"
public_file = folder / "public.pem"
if private_file.exists() or public_file.exists():
    raise SystemExit("Key file already exists; refusing to overwrite")
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
private_file.write_bytes(key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
))
public_file.write_bytes(key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
))
print("Generated keys/private.pem and keys/public.pem")
