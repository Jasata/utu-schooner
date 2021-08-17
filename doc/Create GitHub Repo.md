# Creating a GitHub Repository for Existing Project

_This document has very little use for existing repo and on-going project._

## Create Git Repo

- Open terminal at project root.
- Create `.gitignore` (see Appendix A).
- Type `git init`.
- Type `git add .` to add all files.
- Type `git commit -m "Initial commit"`.

## Connect repo to GitHub

- Login to GitHub.
- Click the "new repository" (and make it private). **DO NOT initialize the repository with a README or LICENSE files!**.
- Use the instructions given for pushing existing repo:  
  ```shell
  git remote add origin git@github.com:{USER}/{REPO}.git
  git push -u origin master
  ```

## Pull to server

_Assuming that the site directory `/var/www/schooner.utu.fi` was created when the server was configured._

- Generate public key, unless already exists.  
  `ssh-keygen -b 4096 -t rsa -f ~/.ssh/id_rsa -q -N ""`
- Add your user's the public key (`~/ssh/id_rsa.pub`) from the server to GitHub.  
  _(Otherwise, the private repo prevents the cloning)._
  - GitHub Settings > SSH and PGP Keys > Add New Key
- Login to the server and enter `/var/www/`.
- `git clone git@github.com:{USER}/{REPO}.git schooner.utu.fi`

# Appendix A - .gitignore

This `.gitignore` file should be suitable for Flask application purposes.

```git
# Project specific
*.sqlite3
*.sqlite3-shm
*.sqlite3-wal
*.log
cron.job/site.config
# Code not-quite-thrown-away
.discard
README.LOCAL.txt

# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Visual Studio Code
.vscode

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
#  Usually these files are written by a python script from a template
#  before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3

# Flask stuff:
instance/
.webassets-cache
uwsgi.log

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# pyenv
.python-version

# celery beat schedule file
celerybeat-schedule

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
```