FROM python:3

WORKDIR /usr/src

RUN curl -L -o /bin/jq 'https://github.com/jqlang/jq/releases/download/jq-1.7.1/jq-linux-amd64'
RUN chmod +x /bin/jq

RUN pip install flask uwsgi sqlalchemy bcrypt python-magic reportlab

COPY . .

RUN mv admin-cli/* /bin/

# run in production mode
CMD ./run.sh
