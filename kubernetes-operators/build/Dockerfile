FROM python:3.10
COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt
COPY templates ./templates
COPY mysql-operator.py ./mysql-operator.py
CMD kopf run /mysql-operator.py