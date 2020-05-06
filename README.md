# djangovuetify
basic configuration (boilerplate) for django and vuetify to work together

* Please add these files to make the backend side work.
  * create **".env"** from **"example.env"** and specify replace value

* Installation.
  * sudo docker build . -f compose/Dockerfile-base -t ubuntu-python3
  * sudo docker build . -f compose/Dockerfile-main -t djangovuetify
  * sudo chmod 777 compose/uswgi.sock
  * sudo docker-compose up -d
  * sudo docker-compose run uwsgi python3 manage.py migrate
  * sudo docker-compose run uwsgi python3 manage.py createsuperuser
  
