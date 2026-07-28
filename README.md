# Future4u-backend

## Setup for local setup
1. clone the repository
2. create a virtual environment
``` python -m venv env ```
3. Activate the virtual environment
    for mac / linux 
    ``` source env/bin/activate ```
    for windows
    ``` env/Scripts/activate    ```
4. Install all the dependencies
``` pip install -r requirements.txt```
5. Run the project using the command
``` python manage.py runserver ```
6. Run the test suite using command
``` pytest -s ```
    this will make the data available till all the test cases are executed
``` pytest --reuse-db    ```
7. Run the server using command 
``` python manage.py runserver  ```
8. Run the celery and celery beat to run the scheduled tasks
``` celery -A future4u worker -l info --pool=threads --concurrency=4   ```
  to run the celery beat process 
```For develop celery restart : sudo systemctl restart celery ```
9. To format all the files use below command
``` black . ```
10. To check for issue give below command
``` flake8  ```
    if virtual environment foler is in the project folder then below command
``` flake8 --exclude=env  ```
    where env is environment foler
11. To remove unused import from all the files
``` pip install autoflake   ```
```
 autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place .    
```

