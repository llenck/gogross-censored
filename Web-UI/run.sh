#!/usr/bin/env bash

if ! [ "$1" = "test" ]; then
	# production mode
	uwsgi \
		--socket /run/gogross-uwsgi.sock \
		--chmod-socket=666 \
		--plugin python \
		--wsgi-file main.py \
		--callable app \
		--processes 4 \
		--threads 2 \
		--stats 127.0.0.1:9191 || exit 1
else
	# test mode
	TEST_DATA=1 uwsgi \
		--http localhost:12345 \
		--plugin python \
		--wsgi-file main.py \
		--callable app || exit 1 &
	UWSGI_PID=$!

	# wait for uwsgi to start processing requests
	while kill -0 $UWSGI_PID; do
		curl -s localhost:12345 > /dev/null && break
		sleep 1
	done

	./test.sh
fi
