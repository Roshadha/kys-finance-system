# Company HTTPS support

HTTPS support is available in the company server EXE. Activation requires an IT-managed hostname and a certificate trusted by every client PC. It is not enabled by default and no certificate or private key is included in the release.

1. Obtain a PEM certificate/full chain and its matching unencrypted PEM private key from company IT. Restrict read access to the Windows account running the server and administrators. The certificate must cover the hostname clients use.
2. Stop the server and create `server-tls.json` beside `KYS Finance Server.exe`, containing paths to those files:

```json
{"certificate":"C:/CompanyCertificates/finance-fullchain.pem","private_key":"C:/CompanyCertificates/finance-key.pem"}
```

3. Start the server. It uses HTTPS on the existing port 5000, requires TLS 1.2 or later, and marks login cookies Secure. A missing, invalid or mismatched certificate stops startup instead of falling back to HTTP. Review `server-error.log` if startup fails.
4. Open `https://YOUR-CERTIFICATE-HOSTNAME:5000/` on the server and clients. Replace the old server browser shortcut URL with this address. The separate Start/Stop shortcuts remain valid.
5. Install the updated client launcher. Choose M for manual address and enter the full HTTPS URL including `:5000`; keep the offered port. Certificate trust and hostname checks remain enabled. HTTPS uses the saved hostname rather than IP auto-discovery. The certificate hostname must resolve to the server on the company network.
6. Verify the login page has no certificate warning, sign in, and test one approved entry and report from a client. Windows 7 clients require a browser and Windows/.NET TLS configuration that supports TLS 1.2 and the company's certificate chain.

Do not publish private keys, certificates containing private keys, `server-tls.json`, databases or backup settings to GitHub. Existing HTTP browsers must be closed/reopened with the new URL after activation. This support has local automated tests; company certificate provisioning and real-PC deployment are separate steps.
