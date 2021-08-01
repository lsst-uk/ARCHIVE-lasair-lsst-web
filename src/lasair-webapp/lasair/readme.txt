# In order to run manage.py 
# change the static files in /staticfiles DO NOT TOUCH /static
export PYTHONPATH=/home/ubuntu/lasair-lsst-web/src:/home/ubuntu/lasair-lsst-web/src/lasair-webapp/lasair

# when you change the static files do
python manage.py collectstatic
