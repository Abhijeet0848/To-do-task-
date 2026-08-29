"""
WSGI config for ZenTask application.
Exposes the WSGI callable as a module-level variable named `application`.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import app as application

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    application.run(host="0.0.0.0", port=port)
