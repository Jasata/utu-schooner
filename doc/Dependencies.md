# Dependencies

- **Pip**  
For installing needed libraries  
`# apt install python3-pip`  
- **GitPython 3**  
For cloning Github repositories, creating issues etc.  
`# pip install GitPython`
- **Requests**  
For GitHub API calls.  
`# pip install requests`
- **Psycopg 3**  
For postgreSQL database operations.  
Install prerequisites:  
``# install python3-dev libpq-dev``  
Install psycopg:  
`# pip3 install git+https://github.com/psycopg/psycopg.git#subdirectory=psycopg`  
(Possibly ``$ pip install psycopg`` if the Psycopg 3 is now released)