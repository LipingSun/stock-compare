FROM python:2.7.11-alpine
MAINTAINER Liping
# Create app directory
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
# Install app dependencies
COPY requirements.txt /usr/src/app/
RUN pip install -r requirements.txt
# Bundle app source
COPY . /usr/src/app
# Start app
CMD [ "python", "MatchServer.py" ]