"""
Generate Self-Signed SSL Certificate untuk HTTPS
=================================================

CARA PAKAI:
python generate_ssl.py

OUTPUT:
- cert.pem (SSL Certificate)
- key.pem (Private Key)

Gunakan untuk jalankan server dengan HTTPS
"""

import os
from datetime import datetime, timedelta

def generate_ssl_certificate():
    """Generate self-signed SSL certificate"""
    
    print("""
╔═══════════════════════════════════════════════╗
║                                               ║
║          SSL Certificate Generator            ║
║                                               ║
╚═══════════════════════════════════════════════╝
""")
    
    # Check if openssl is available
    if os.system("openssl version > /dev/null 2>&1") != 0:
        print("❌ ERROR: OpenSSL tidak terinstall!")
        print("\nInstall OpenSSL:")
        print("  Ubuntu/Debian: sudo apt-get install openssl")
        print("  macOS: brew install openssl")
        print("  Windows: Download dari https://slproweb.com/products/Win32OpenSSL.html")
        return False
    
    print("✅ OpenSSL detected\n")
    print("Generating SSL certificate...\n")
    
    # Generate private key and certificate
    cmd = """
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout key.pem \
    -out cert.pem \
    -days 365 \
    -subj "/C=ID/ST=East Java/L=Gresik/O=UISI/CN=10.16.132.142" \
    -addext "subjectAltName=IP:10.16.132.142,DNS:localhost"
    """
    
    # Windows compatible version
    if os.name == 'nt':
        openssl = r"C:\Program Files\OpenSSL-Win64\bin\openssl.exe"
        cmd = f'"{openssl}" req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/C=ID/ST=East Java/L=Gresik/O=UISI/CN=10.16.132.142" -addext "subjectAltName=IP:10.16.132.142,DNS:localhost"'
    
    result = os.system(cmd)
    
    if result != 0:
        print("❌ Failed to generate certificate")
        return False
    
    print("\n" + "="*60)
    print("SSL CERTIFICATE GENERATED!")
    print("="*60)
    return True

if __name__ == "__main__":
    try:
        success = generate_ssl_certificate()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        exit(1)
