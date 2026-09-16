import os

from waitress import serve

from app import app


if __name__ == "__main__":
    host = os.environ.get("KYS_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    print(f"K.Y.S. Finance is running on http://{host}:{port}")
    serve(app, host=host, port=port, threads=4)

