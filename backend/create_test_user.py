"""
Script to create or verify a test/demo user in CloudGuard.
Reads credentials from local environment variables or optional CLI arguments.

Usage:
    python create_test_user.py [email] [password] [full_name]

Environment Variables:
    DEMO_USER_EMAIL
    DEMO_USER_PASSWORD
    DEMO_USER_NAME
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from seed import seed_demo_environment

if __name__ == "__main__":
    # If CLI arguments are provided, set environment variables so seed picks them up
    if len(sys.argv) > 1:
        os.environ["DEMO_USER_EMAIL"] = sys.argv[1]
    if len(sys.argv) > 2:
        os.environ["DEMO_USER_PASSWORD"] = sys.argv[2]
    if len(sys.argv) > 3:
        os.environ["DEMO_USER_NAME"] = sys.argv[3]

    seed_demo_environment()
