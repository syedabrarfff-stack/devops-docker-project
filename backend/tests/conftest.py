import pytest
import os

# Set test environment at module load time to prevent config validation errors
os.environ["ALLOW_INSECURE_DEV_DEFAULTS"] = "true"
os.environ["DEBUG"] = "true"
os.environ.setdefault("SES_FROM_EMAIL", "test@example.com")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
