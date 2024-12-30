FROM python:3.11

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y python3-distutils
RUN apt-get install -y pkg-config

COPY requirements.txt ./

RUN python3 -m venv venv
RUN . venv/bin/activate

RUN pip install --upgrade setuptools wheel pip
RUN pip install setuptools
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "-u", "./main.py"]