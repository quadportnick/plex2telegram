FROM python:latest
WORKDIR /usr/app/src
COPY requirements.txt ./
RUN pip3 install -r requirements.txt
CMD [ "python", "-u", "./plex2telegram.py" ]
