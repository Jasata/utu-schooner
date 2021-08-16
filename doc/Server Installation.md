# Server Installation

Eventually, `setup.py` should automate this, but for now, manual installation notes suffice.

Target OS: Debian 10.x (production server running Ubuntu 20.04)  
`root` privileges are required (obviously).

## Related System Groups

**`postgres`:** Associated with a user `postgres`. Postgresql databases are owned by this _user and group_. All files in `/var/lib/postgresql` are owned by this user to enforce proper security.

**`www-data`:** Associated with user `www-data`. Nginx worker processes run as `www-data`. Web content should not be owned by this user, or a compromised web server would be able to rewrite a web site. Data written out by web servers, including log files, will be owned by `www-data`.

<hr>  

**Development Setup** _will_ grant write permissions to `www-data` (`chmod 775/664`) until the system is stable and considered to have entered production phase. At that time, group write permissions will be removed and shared development is no longer supported.
<hr>

## Packages

```shell
# apt install -y nginx postgresql git uwsgi uwsgi-plugin-python3 python3-pip python3-dev python3-flask
```

In addition, Python 3 connector for PostgreSQL is needed, but it has not yet released a package, and has to be installed separately:

```shell
# pip3 install git+https://github.com/psycopg/psycopg.git#subdirectory=psycopg
```

## Add developers to www-data group

```shell
# usermod -a -G www-data {username}
```

## SSL Certificates

__*.pem, *.crt, *.ca-bundle, *.cer, *.p7b, *.p7s__ files contain one or more X.509 digital certificate files that use base64 (ASCII) encoding.

### The .pem extension
PEM is a method of encoding binary data as a string (ASCII armor). It contains a header and a footer line (specifying the type of data that is encoded and showing begin/end if the data is chained together) and the data in the middle is the base 64 data. In the case that it encodes a certificate it would simply contain the base 64 encoding of the DER certificate. **PEM stands for Privacy Enhanced Mail**; mail cannot contain un-encoded binary values such as DER directly.

PEM may also encode / protect other kinds of data that is related to certificates such as public / private keys, certificate requests, etc. If the contents are a common X509v3 certificate then the PEM is encoded as:

    -----BEGIN CERTIFICATE-----
    ... base 64 encoding of the DER encoded certificate
        with line endings and padding with equals signs ...
    -----END CERTIFICATE-----

Note that a PEM file may also contain a complete certificate chain, where the chain starts with the leaf / end certificate of the service, followed by the certificate that signed it, usually up to but not including the trusted root certificate. So if you're missing certificates you may want to take a look behind the first one.

### The .cer or .crt extension
`.cer` just stands for certificate. It is normally DER encoded data, but Windows may also accept PEM encoded data. You need to take a look at the content (e.g. using the file utility on posix systems) to see what is within the file to be 100% sure.

    -----BEGIN CERTIFICATE-----
    MIIHl...
    ...
    -----END CERTIFICATE-----

### .csr - Certificate Signing Request
A CSR or Certificate Signing request is a block of encoded text that is given to a _Certificate Authority_ when applying for an SSL Certificate. It is usually generated on the server where the certificate will be installed and contains information that will be included in the certificate such as the organization name, common name (domain name), locality, and country. It also contains the **public key** that will be included in the certificate.



### .key - Private Key
**A private key** is usually created at the same time that you create the CSR, making a key pair. A CSR is generally encoded using ASN.1 according to the PKCS #10 specification.

A certificate authority will use a CSR to create your SSL certificate, but it does not need your private key. You need to keep your private key secret. The certificate created with a particular CSR will only work with the private key that was generated with it. So if you lose the private key, the certificate will no longer work.

    -----BEGIN PRIVATE KEY-----
    MIIEvwIBADAN...
    ...
    -----END PRIVATE KEY-----


## Nginx Configuration

- Create web root directory  
  `mkdir /var/www/schooner.utu.fi`  
  `chown {user}.{group} /var/www/schooner.utu.fi`  
  `chmod 775 /var/www/schooner.utu.fi` (NOTE: `www-data` write should be removed in production)
- Prepare uWSGI
  - Create `/etc/uwsgi/apps-available/schooner.utu.fi.ini`.  
    See INI file content from Appendix A.
  - Link to enable:  
    `ln -s /etc/uwsgi/apps-available/schooner.utu.fi.ini /etc/uwsgi/apps-enabled`
  - Restart uWSGI to read new enabled app:  
    `systemctl restart uwsgi.service`
- Store SSL certificates under `/etc/ssl`  
  Files need to be copied because linking would make them in accessible to non-root users.
  - Copy the `.cer` file to `/etc/ssl/certs`:  
    `cp /root/cert/schooner_utu_fi_cert.cer /etc/ssl/certs/`
  - Copy the `.key` private key to `/etc/ssl/private/`  
    `cp /root/cert/schooner.utu.fi.key /etc/ssl/private/`  
    `chmod 640 /etc/ssl/private/schooner.utu.fi.key`  
    `chown root.ssl-cert /etc/ssl/private/schooner.utu.fi.key`
- Create site for Nginx and enable it  
  **DEV INSTANCE:**  
  ```shell
  cat << EOF >>/etc/nginx/sites-available/schooner.utu.fi
  server {
    listen 80;
    listen [::]:80;
    rewrite_log on;
    access_log /var/log/nginx/schooner.utu.fi.access.log;
    error_log /var/log/nginx/schooner.utu.fi.error.log notice;
    server_name schooner.utu.fi;
    root /var/www/schooner.utu.fi;
    index index.html;
    location / {
        try_files $uri $uri/ =404;
    }
  }
  EOF
  ```  
  **PRODUCTION INSTANCE:**  
  ```shell
  cat << EOF >>/etc/nginx/sites-available/schooner.utu.fi
  ssl_certificate /etc/ssl/certs/schooner_utu_fi_cert.cer;
  ssl_certificate_key /etc/ssl/private/schooner.utu.fi.key;

  server {
    listen 80;
    listen [::]:80;
    server_name schooner.utu.fi;
    return 301 https://schooner.utu.fi$request_uri;
  }

  server {
    listen 443 ssl;
    listen [::]:443;

    error_log /var/log/nginx/schooner.utu.fi.error.log warn;
    access_log /var/log/nginx/schooner.utu.fi.access.log;

    root /var/www/schooner.utu.fi;
    server_name schooner.utu.fi;
    index index.html;

    location / {
        include uwsgi_params;
        client_max_body_size 40M;
        uwsgi_pass unix:/run/uwsgi/app/schooner.utu.fi/schooner.utu.fi.socket;
        uwsgi_buffering off;
    }
  }
  EOF
  ```
  `ln -s /etc/nginx/sites-available/schooner.utu.fi /etc/nginx/sites-enabled/schooner.utu.fi`  
  `systemctl restart nginx.service`
- Test
  - Using local shell:  
    `wget localhost`
- **PRODUCTION INSTANCE** (Ubuntu 20.04):  
  UFW - Allow HTTP and HTTPS  
  _Ubuntu has something called "uwf" (uncomplicated firewall) that by default prevents HTTP/HTTPS access._  
  `ufw allow "Nginx HTTP"` (Nginx redirects to HTTPS)  
  `ufw allow "Nginx HTTPS"`  
  Check with `ufw status`

- **DEVELOPMENT INSTANCE**  
  Resolve `schooner.utu.fi` as your local development box. Easiest way is to simply modify your local `hosts` file. In Windows 10:  
  "Run as Administrator" Notepad, open `C:\Windows\System32\drivers\etc\hosts`, add:  
  ```
  192.168.1.23	schooner.utu.fi
  ```

# Appendix A - uWSGI .ini File

Application configuration `/etc/uwsgi/apps-available/schooner.utu.fi.ini`:
```ini
[uwsgi]
plugins = python3
module = application
callable = app
# Execute in directory...
chdir = /var/www/schooner.utu.fi/
# Execution parameters
master = true
processes = 1
threads = 4
# Logging (cmdline logging directive overrides this, unfortunately)
logto=/var/log/uwsgi/schooner.log
# Credentials that will execute Flask
uid = www-data
gid = www-data
# Since these components are operating on the same computer,
# a Unix socket is preferred because it is more secure and faster.
socket = /run/uwsgi/app/schooner.utu.fi/schooner.utu.fi.socket
chmod-socket = 664
# Clean up the socket when the process stops
vacuum = true
# This is needed because the Upstart init system and uWSGI have
# different ideas on what different process signals should mean.
# Setting this aligns the two system components, implementing
# the expected behavior:
die-on-term = true
```

# Appendix B - Developer SSH key

To avoid obnoxious password queries from VSC, public key should be added to schooner.utu.fi's authorised list:

Copy `C:\Users\%USERNAME%\.ssh\id_rsa.pub` into schooner.utu.fi `~/.ssh/authorized_keys`

```shell
mkdir ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Simply copy the contents of workstation's `id_rsa.pub` into server's `~/.ssh/authorized_keys` and save the file.

# Appendix C - Assistant SSH key

Since assistants are running a modified virtual machine, their configuration could and should be automated with:

```shell
ssh-copy-id -i ~/.ssh/id_rsa.pub {UTU ID}@schooner.utu.fi
```