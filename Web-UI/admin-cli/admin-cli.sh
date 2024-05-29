#!/usr/bin/env bash

function set-key() {
	! [ -z "$GOGROSS_KEY" ] && return

	if [ -f /usr/src/admin_key ]; then
		GOGROSS_KEY="$(cat /usr/src/admin_key)"
	elif which docker > /dev/null; then
		GOGROSS_KEY=$(docker exec -it $(docker ps | awk '!found && $2=="gogross/master" {found=1; print $1}') cat admin_key)
	fi

	if [ -z "$GOGROSS_KEY" ]; then
		echo "Couldn't determine the admin key. Please set via the GOGROSS_KEY environment-variable (found in the docker container at /admin_key)"
		exit 1
	fi
}

function set-base() {
	! [ -z "$GOGROSS_BASE" ] && return

	if timeout 2 curl gogross-rev-proxy &>/dev/null; then
		GOGROSS_BASE=http://gogross-rev-proxy
	elif timeout 2 curl localhost &>/dev/null; then
		GOGROSS_BASE=http://localhost
	fi

	if [ -z "$GOGROSS_BASE" ]; then
		echo "Couldn't determine the base url. Please set via the GOGROSS_BASE environment-variable"
		exit 1
	fi
}

function gog-curl() {
	curl -H "admin-key: $GOGROSS_KEY" "$GOGROSS_BASE"/"$@"
}

function create-game() {
	if [ -z "$1" ]; then
		echo Usage: gogross-create "<new game name>"
		exit 1
	fi

	gog-curl create-game -X POST -d "$1"
}

function list-games() {
	gog-curl list-games
}

function pause-game() {
	if [ -z "$1" ]; then
		echo Usage: gogross-pause "<game>"
		exit 1
	fi

	gog-curl pause-game -X POST -d "$1"
}

function resume-game() {
	if [ -z "$1" ]; then
		echo Usage: gogross-resume "<game>"
		exit 1
	fi

	gog-curl resume-game -X POST -d "$1"
}

function export-game() {
	if [ -z "$1" ] || [ -t 1 ]; then
		echo Usage: gogross-export "<game> > <backup-file>"
		exit 1
	fi

	# TODO mangels STDOUT sollten wir hier extra gucken obs schiefging und das über stderr ausgeben
	gog-curl export-game -X POST -d "$1" -f || echo "Something went wrong..." >&2
}

function import-game() {
	if [ -z "$1" ] || [ -z "$2" ]; then
		echo Usage: gogross-import "<new game name> <backup file>"
		exit 1
	fi

	gog-curl import-game -X POST -F "game=$1" -F "content=@$2"
}

function clear-game() {
	if [ -z "$1" ]; then
		echo Usage: gogross-clear "<game>"
		exit 1
	fi

	gog-curl clear-game -X POST -d "$1"
}

function delete-game() {
	if [ -z "$1" ]; then
		echo Usage: gogross-delete "<game>"
		exit 1
	fi

	echo This will the delete the game "$1". To make sure you really mean it, please type in the name again:
	read -p "Game Name> " name

	if ! [ "$name" == "$1" ]; then
		echo Names do not match.
		exit 1
	fi

	gog-curl delete-game -X POST -d "$1"
}

function dump-games() {
	gog-curl dump-db
}

function dump-invoices {
	dump-games | jq '

	# go down to vendor level
	  .[].vendors.[]
	# save vendor iban for later
	| .iban as $iban
	# save item canon_id -> name for later
	| (.categories.[] | map({(.id | tostring): .}) | add) as $cats

	# go down to sus acc level
	| .sus_accs.[]
	# save sus contact info
	| {mail: .mail, name: .name} as $sus

	# go down to invoice level
	| .invoices.[]
	# add some info to the invoices
	| .should_pay_to = $iban
	| .sus_account = $sus
	# only keep relevant infos for invoice items
	| .items |= map({
		price_per_unit,
		count,
		total,
		item_name: $cats.[.item_id | tostring].name
	})
'
}

function email-settings() {
	if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
		echo Usage: gogross-email-settings [sender-address] [smtp-host] [smtp-port]
		echo Leaving any field empty '("")' will keep the old value.
		exit 1
	fi

	SETTINGS=""
	! [ -z "$1" ] && SETTINGS="$SETTINGS&address=$1"
	! [ -z "$2" ] && SETTINGS="$SETTINGS&host=$2"
	! [ -z "$3" ] && SETTINGS="$SETTINGS&port=$3"

	SETTINGS="${SETTINGS#&}"
	gog-curl email-settings -X POST -d "$SETTINGS"
}

function usage {
	echo "The following commands are provided:"
	echo "    gogross-help                                  | Print this message"
	echo "    gogross-create <new game name>                | Creates a new empty game. New games are immediately live"
	echo "    gogross-list                                  | List running games & teacher registration paths"
	echo "    gogross-pause <game>                          | Pause a game, taking it temporarily offline (TODO!)"
	echo "    gogross-resume <game>                         | Resumes a paused game"
	echo "    gogross-export <game> > <backup-file>         | Exports a game, with vendors/items, but not accounts/deeplinks"
	echo "    gogross-import <new game name> <backup-file>  | Create a new game using the content from a previous export"
	echo "    gogross-clear <game>                          | Clear account data & regenerate deeplinks for a given game"
	echo "    gogross-delete <game>                         | Delete a game"
	echo "    gogross-dump                                  | Dump pretty much the whole database in JSON format"
	echo "    gogross-dump-invoices                         | Dump a list of pending/paid transactions"
	echo "    gogross-email-settings [sender] [host] [port] | set/retrieve SMTP settings for password reset requests"
}

set-key
set-base

cmd=$(basename $0)

case $cmd in
	"gogross-create") create-game "$@" ;;
	"gogross-list") list-games "$@" ;;
	"gogross-pause") pause-game "$@" ;;
	"gogross-resume") resume-game "$@" ;;
	"gogross-export") export-game "$@" ;;
	"gogross-import") import-game "$@" ;;
	"gogross-dump") dump-games "$@" ;;
	"gogross-clear") clear-game "$@" ;;
	"gogross-delete") delete-game "$@" ;;
	"gogross-dump-invoices") dump-invoices "$@" ;;
	"gogross-email-settings") email-settings "$@" ;;
	*) usage;;
esac

echo
