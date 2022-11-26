FROM python:3.11-bullseye

RUN apt-get update && apt-get upgrade -y && apt-get autoremove -y
RUN python3 -m pip install --upgrade pip

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY . .

RUN pip3 install -r requirements.txt
RUN pip3 install uvloop

CMD ["python3", "-OO", "-m", "bot"]
