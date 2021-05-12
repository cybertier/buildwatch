FROM ubuntu:focal
ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get update && apt-get install -y g++ gcc wget libgdbm6 libreadline8 libsqlite3-0 libtcl8.6 libtk8.6 tk8.6-blt2.5 git && rm -rf /var/lib/apt/lists/*

RUN wget --quiet https://github.com/pyston/pyston/releases/download/pyston_2.2/pyston_2.2_20.04.deb
RUN apt install ./pyston_2.2*.deb
RUN rm ./pyston_2.2*.deb

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip-pyston install -r requirements.txt

COPY . /app

ENTRYPOINT [ "pyston" ]

CMD [ "main.py" ]
