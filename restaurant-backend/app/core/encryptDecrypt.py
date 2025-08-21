import json
import os
from base64 import b64decode, b64encode
from typing import Dict, Optional

from cryptography.hazmat.primitives.asymmetric.padding import MGF1, OAEP
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class RequestData(BaseModel):
    encrypted_flow_data: str
    encrypted_aes_key: str
    initial_vector: str


class DecryptedRequestData(BaseModel):
    version: str
    action: str
    screen: Optional[str] = None
    data: Optional[Dict] = Field(default_factory=dict)
    flow_token: Optional[str] = None


class ResponseData(BaseModel):
    version: str
    screen: str
    data: dict


# Load environment variables from .env file
load_dotenv()

# Load the private key string from an environment variable
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
KEY_PASS = os.environ.get("KEY_PASS")


def decryptRequest(encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64):
    flow_data = b64decode(encrypted_flow_data_b64)
    iv = b64decode(initial_vector_b64)
    print("decrypt1")
    encrypted_aes_key = b64decode(encrypted_aes_key_b64)

    private_key = load_pem_private_key(PRIVATE_KEY.encode("utf-8"), password=KEY_PASS.encode("utf-8"))
    print("decrypt2")
    aes_key = private_key.decrypt(
        encrypted_aes_key,
        OAEP(mgf=MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    print("decrypt3")
    encrypted_flow_data_body = flow_data[:-16]
    encrypted_flow_data_tag = flow_data[-16:]
    decryptor = Cipher(algorithms.AES(aes_key), modes.GCM(iv, encrypted_flow_data_tag)).decryptor()
    decryptedDataBytes = decryptor.update(encrypted_flow_data_body) + decryptor.finalize()
    decryptedData = json.loads(decryptedDataBytes.decode("utf-8"))
    print("decrypt4")
    return decryptedData, aes_key, iv


def encryptResponse(response, aes_key, iv):
    flipped_iv = bytearray(iv)
    for i in range(len(flipped_iv)):
        flipped_iv[i] ^= 0xFF

    encryptor = Cipher(algorithms.AES(aes_key), modes.GCM(flipped_iv)).encryptor()
    encrypted_bytes = encryptor.update(json.dumps(response).encode("utf-8")) + encryptor.finalize()
    return b64encode(encrypted_bytes + encryptor.tag).decode("utf-8")
