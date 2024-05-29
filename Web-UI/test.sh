#!/usr/bin/env bash

echo RUNNING TESTS. This script should usually only be started from within run.sh.

function test_curl() {
	STATUS=$(curl -s -o /dev/null -w "$1" localhost:12345"${@:4}")

	if ! [[ $STATUS =~ ^$2$ ]]; then
		echo ========================================
		echo TEST FAILED:
		echo $STATUS
		echo DOES NOT MATCH
		echo $2
		echo ON TEST:
		echo $3

		pkill uwsgi
		exit 1
	fi
}

function test_curl_output() {
	curl -s localhost:12345"${@:3}" > last-output
	if ! bash -c "$1" < last-output; then
		echo ========================================
		echo TEST FAILED:
		echo "${@:3}"
		echo DOES NOT MATCH
		echo "$1"
		echo ON TEST:
		echo $2

		pkill uwsgi
		exit 1
	fi
}

function test_command() {
	if ! bash -c "$2"; then
		echo ========================================
		echo TEST FAILED:
		echo "$1"

		pkill uwsgi
		exit 1
	fi
}

export PATH="$(pwd)/admin-cli:$PATH"
export GOGROSS_KEY="$(cat admin_key)"
export GOGROSS_BASE="localhost:12345"

# TODO sicherheits-kram: wir gucken im backend bisher nur selten auf dinge wie
# landzugehörigkeit/Planspiel, deshalb testen wir hier auch _nicht_, ob man mit tools
# zusätzlich zur Weboberfläche Sachen aus anderen Länder/vendors zugreifen kann,

# teacher registration
test_curl '%{http_code}' '[345]..' "Invalid teacher registration link" /register/blah
test_curl '%{http_code}' '2..'     "Valid teacher registration link"   /register/insecure-test-link
test_curl '%{http_code}' '[345]..' "Invalid teacher registration data" /register/insecure-test-link -X POST -d "blah"
# TODO hier könnte man feinere tests einführen, die auch aktuell fehlschlagen, aber
# imo ist serverseitiges gucken nach valid emails & ähnlichem nicht so super wichtig
test_curl '%{http_code}' '[23]..'  "Valid teacher registration data"   /register/insecure-test-link -X POST -d "name=a&email=b@c.de&country=DE&password=blubbel123"

# teacher login. The tests using url_effective could be more elegant/generic using
# urle.path, but that's only supported in curl >=8.1, which we don't have access to
# within our docker container :(
test_curl '%{http_code}' '200'              "Teacher login without cookies"     / -L
test_curl '%{url_effective}' 'http://localhost:12345/'          "Invalid teacher login (form)"            / -L -X POST -d "Blah"
test_curl '%{url_effective}' 'http://localhost:12345/'          "Invalid teacher login (content)"         / -L -X POST -d "email=invalid@a.de&password=invalid"
test_curl '%{url_effective}' 'http://localhost:12345/dashboard' "Valid teacher login"                     / -L -X POST -d "email=b@c.de&password=blubbel123" --cookie-jar lehrer_de.cookie-jar
test_curl '%{url_effective}' 'http://localhost:12345/dashboard' "Teacher login with cookies"              / -L --cookie lehrer_de.cookie-jar
test_curl '%{url_effective}' 'http://localhost:12345/products'  "Teacher login with cookies & return-url" /?return=/products -L --cookie lehrer_de.cookie-jar

# teacher dashboard. NOTE: wir gucken nicht so genau ob die sachen auch wirklich paid/unpaid sind.
test_curl '%{http_code}' '[345]..'          "Teacher dashboard without cookies"      /dashboard
test_curl '%{http_code}' '200'              "Teacher dashboard with cookies"         /dashboard                                  --cookie lehrer_de.cookie-jar 
UNPAID_ORIG="$(curl localhost:12345/dashboard --cookie lehrer_de.cookie-jar | awk '/Unpaid orders:/{print $3}')"
UNPAID_ORIG=${UNPAID_ORIG%</h4>}
test_curl '%{http_code}' '[23]..'           "Teacher dashboard mark as paid"         /dashboard -X POST -d 'id=1&paid=on'        --cookie lehrer_de.cookie-jar 
UNPAID_LESS="$(curl localhost:12345/dashboard --cookie lehrer_de.cookie-jar | awk '/Unpaid orders:/{print $3}')"
UNPAID_LESS=${UNPAID_LESS%</h4>}
test_curl '%{http_code}' '[345]..'          "Teacher dashboard invalid mark as paid" /dashboard -X POST -d 'id=12312312&paid=on' --cookie lehrer_de.cookie-jar 
test_curl '%{http_code}' '[345]..'          "Teacher dashboard mark as unpaid"       /dashboard -X POST -d 'id=1'                --cookie lehrer_de.cookie-jar 
UNPAID_MORE="$(curl localhost:12345/dashboard --cookie lehrer_de.cookie-jar | awk '/Unpaid orders:/{print $3}')"
UNPAID_MORE=${UNPAID_MORE%</h4>}
if ! [ $UNPAID_ORIG == $(( $UNPAID_LESS + 1 )) ]; then
	echo TEST FAILED:
	echo "Teacher mark as paid (unpaid count)"
	echo $UNPAID_ORIG != $UNPAID_LESS + 1
	pkill uwsgi
	exit 1
fi
if ! [ $UNPAID_LESS == $(( $UNPAID_MORE - 1 )) ]; then
	echo TEST FAILED:
	echo "Teacher mark as unpaid (unpaid count)"
	echo $UNPAID_LESS != $UNPAID_MORE - 1
	pkill uwsgi
	exit 1
fi

# sus vendor list (must be before teacher tests, as those add a random vendor)
test_curl '%{http_code}' '[345]..' "SuS vendor list (bad deeplink)"  /blah/list
test_curl '%{http_code}' '200'     "SuS vendor list (good deeplink)" /insecure-test-link/list
test_curl_output $'awk \'f&&s==1{gsub(/^ */, "", $0);gsub(/ *$/, "", $0);print $0}{s++}/class="vendor_info"/{s=0;f=1}\' | jq -Rs | grep -qF \'"Test Vendor\\nTest Vendor 2\\n"\'' "SuS vendor list (vendor content)" /insecure-test-link/list

# teacher product image
test_curl '%{http_code}' '[345]..' "Teacher product image without cookies" /products/img?product=1
test_curl '%{http_code}' '[345]..' "Teacher product image, bad ID"         /products/img?product=123456 --cookie lehrer_de.cookie-jar
test_curl '%{http_code}' '200'     "Teacher product image with cookies"    /products/img?product=1      --cookie lehrer_de.cookie-jar

# teacher product add
test_curl '%{http_code}' '[345]..' "Teacher product add form without cookies" /products/add?shop=1
test_curl '%{http_code}' '200'     "Teacher product add form"                 /products/add?shop=1 --cookie lehrer_de.cookie-jar
PRODUCT_ID_BAD="$RANDOM$RANDOM$RANDOM"
PRODUCT_ID="$RANDOM$RANDOM$RANDOM"
test_curl '%{http_code}' '[45]..'     "Teacher product add w/ invalid price (null)"   /products/add?shop=1 -X POST -H 'Content-Type: application/json' -d \
	'{"name":"asd","category":"1","itemNumber":"'"$PRODUCT_ID_BAD"'","description":"qwewqe","price":null,"manufacturer":"asdwqeasd"}' --cookie lehrer_de.cookie-jar
test_curl '%{http_code}' '[45]..'     "Teacher product add w/ invalid price (string)" /products/add?shop=1 -X POST -H 'Content-Type: application/json' -d \
	'{"name":"asd","category":"1","itemNumber":"'"$PRODUCT_ID_BAD"'","description":"qwewqe","price":"abc","manufacturer":"asdwqeasd"}' --cookie lehrer_de.cookie-jar
test_curl '%{http_code}' '200'     "Teacher product add"                              /products/add?shop=1 -X POST -H 'Content-Type: application/json' -d \
	'{"name":"asd","category":"1","itemNumber":"'"$PRODUCT_ID"'","description":"qwewqe","price":123,"manufacturer":"asdwqeasd"}' --cookie lehrer_de.cookie-jar
# NOTE hier könnte man das auch noch per db-dump testen, aber wir gucken schon später
# in produktlisten; dass muss aus zeitgründen erstmal reichen.

VENDOR_NAME_BAD="$RANDOM$RANDOM$RANDOM"
VENDOR_NAME="$RANDOM$RANDOM$RANDOM"
# teacher vendor add
test_curl '%{http_code}' '[345]..' "Add vendor w/o cookies"                 /administration/add-vendor -X POST -H 'Content-Type: application/json' -d \
	'{"name": "'$VENDOR_NAME_BAD'", "iban": "DE12345", "skonto": 5, "invoice_notes": "Blah", "skonto_period": 2}'
test_curl '%{http_code}' '[345]..' "Add vendor with invalid data (types)"   /administration/add-vendor -X POST -H 'Content-Type: application/json' -d \
	'{"name": "'$VENDOR_NAME_BAD'", "iban": "DE12345", "skonto": "blub", "invoice_notes": "Blah", "skonto_period": 2}' --cookie lehrer_de.cookie-jar
test_curl '%{http_code}' '[345]..' "Add vendor with invalid data (missing)" /administration/add-vendor -X POST -H 'Content-Type: application/json' -d \
	'{"name": "'$VENDOR_NAME_BAD'", "skonto": 5, "invoice_notes": "Blah", "skonto_period": 2}' --cookie lehrer_de.cookie-jar
test_curl '%{http_code}' '200'     "Add vendor"                             /administration/add-vendor -X POST -H 'Content-Type: application/json' -d \
	'{"name": "'$VENDOR_NAME'", "iban": "DE12345", "skonto": 5, "invoice_notes": "Blah", "skonto_period": 2}' --cookie lehrer_de.cookie-jar
test_command "Dump contains added vendor"       $'gogross-dump | jq \'."Test Game".vendors | map(select(.name == "'$VENDOR_NAME$'") | .categories == {} and .sus_accs == []) | . == [true]\' | grep -q true'
test_command "Dump doesn't contain bad vendor"  $'gogross-dump | jq \'."Test Game".vendors | map(select(.name == "'$VENDOR_NAME_BAD$'")) | . == []\' | grep -q true'

# teacher administration
test_curl '%{http_code}' '[345]..' "Administration without cookies" /administration
test_curl '%{http_code}' '200'     "Administration with cookies"    /administration --cookie lehrer_de.cookie-jar
test_curl_output "! grep -q -- $VENDOR_NAME_BAD" "Teacher administration doesn't contain bad vendor" /administration --cookie lehrer_de.cookie-jar
test_curl_output "grep -q -- $VENDOR_NAME"       "Teacher administration contains added vendor"      /administration --cookie lehrer_de.cookie-jar

# teacher product list
test_curl '%{http_code}' '[345]..' "Teacher product list without cookies"         /products
test_curl '%{http_code}' '200'     "Teacher product list w/o shop"                /products                      --cookie lehrer_de.cookie-jar
test_curl '%{http_code}' '200'     "Teacher product list w/o categories"          /products?shop=1               --cookie lehrer_de.cookie-jar
test_curl '%{http_code}' '[345]..' "Teacher product image with invalid category" '/products?shop=1&category=bad' --cookie lehrer_de.cookie-jar
test_curl '%{http_code}' '200'     "Teacher product image with valid category"   '/products?shop=1&category=1'   --cookie lehrer_de.cookie-jar
test_curl_output "! grep -q -- $PRODUCT_ID_BAD" "Teacher products doesn't contain bad product"           /products?shop=1 --cookie lehrer_de.cookie-jar
test_curl_output "grep -q -- $PRODUCT_ID"       "Teacher products contains added product"                '/products?shop=1' --cookie lehrer_de.cookie-jar
test_curl_output "! grep -q -- $PRODUCT_ID"     "Teacher products doesn't contain product on other shop" '/products?shop=2' --cookie lehrer_de.cookie-jar

# sus registration
test_curl '%{http_code}' '[345]..' "SuS registration form without shop"      /insecure-test-link/register
test_curl '%{http_code}' '[345]..' "SuS registration form with invalid shop" /insecure-test-link/register?shop=123123123
test_curl '%{http_code}' '200'     "SuS registration form"                   /insecure-test-link/register?shop=1
test_curl '%{url_effective}' '.*/insecure-test-link/login\?shop=1'    "Valid SuS registration data" /insecure-test-link/register?shop=1 -L -X POST -d "company_name=asd&email=b@c.de&password=blubbel123"
test_curl '%{url_effective}' '.*/insecure-test-link/register\?shop=1' "Duplicate SuS registration"  /insecure-test-link/register?shop=1 -L -X POST -d "company_name=asd&email=b@c.de&password=blubbel123"

# sus login
test_curl '%{http_code}'     '[345]..' "SuS login form without shop"      /insecure-test-link/login
test_curl '%{http_code}'     '200'     "SuS login form with shop"         /insecure-test-link/login?shop=1
test_curl '%{url_effective}' '.*/insecure-test-link/login\?shop=1' "Invalid SuS login (form)"    /insecure-test-link/login?shop=1 -L -X POST -d 'blah'
test_curl '%{url_effective}' '.*/insecure-test-link/login\?shop=1' "Invalid SuS login (data)"    /insecure-test-link/login?shop=1 -L -X POST -d 'email=a@b.c&password=kek'
test_curl '%{url_effective}' '.*/insecure-test-link/home'          "Valid SuS login"             /insecure-test-link/login?shop=1 -L -X POST -d 'email=b@c.de&password=blubbel123' --cookie-jar sus.cookie-jar
test_curl '%{url_effective}' '.*/insecure-test-link/home'          "SuS login form with cookies" /insecure-test-link/login?shop=1 -L --cookie sus.cookie-jar

# sus home
test_curl '%{http_code}' '[345]..' "SuS home without cookies" /insecure-test-link/home
test_curl '%{http_code}' '200'     "SuS home with cookies"    /insecure-test-link/home --cookie sus.cookie-jar

# sus product image
test_curl '%{http_code}' '[345]..' "SuS product image without cookies" /insecure-test-link/img?product=1
test_curl '%{http_code}' '200'     "SuS product image with cookies"    /insecure-test-link/img?product=1 --cookie sus.cookie-jar

# sus catalog
test_curl '%{http_code}' '[345]..' "SuS catalog without cookies"             /insecure-test-link/catalog
test_curl '%{http_code}' '200'     "SuS catalog with cookies"                /insecure-test-link/catalog            --cookie sus.cookie-jar
test_curl '%{http_code}' '200'     "SuS catalog with cookies and categories" /insecure-test-link/catalog?category=1 --cookie sus.cookie-jar
test_curl_output "grep -q -- $PRODUCT_ID"   "SuS products contain added product"           /insecure-test-link/catalog --cookie sus.cookie-jar
test_curl_output "! grep -q -- $PRODUCT_ID_BAD" "SuS products doesn't contain invalid product" /insecure-test-link/catalog --cookie sus.cookie-jar

# sus shopping cart / checkout
test_curl '%{http_code}' '[23]..' "SuS add to cart" /insecure-test-link/add-to-cart -X POST -d 'product_id=1&quantity=2' --cookie sus.cookie-jar --cookie-jar sus-cart.cookie-jar
test_curl '%{http_code}' '200'    "SuS cart"        /insecure-test-link/cart --cookie sus-cart.cookie-jar
SUS_EMPTY_CART="$(curl localhost:12345/insecure-test-link/cart --cookie sus.cookie-jar      | md5sum | awk '$0=$1')"
SUS_FULL_CART="$( curl localhost:12345/insecure-test-link/cart --cookie sus-cart.cookie-jar | md5sum | awk '$0=$1')"
if [ "$SUS_EMPTY_CART" == "$SUS_FULL_CART" ]; then
	echo TEST FAILED:
	echo "SuS cart without products differs from cart with products"
	echo "$SUS_EMPTY_CART != $SUS_FULL_CART"
	pkill uwsgi
	exit 1
fi
test_curl_output '! file -i - | grep -q application/pdf' "Empty cart checkout results in error" /insecure-test-link/checkout -L -X POST --cookie sus.cookie-jar
test_curl_output 'file -i - | grep -q application/pdf' "Full cart checkout redirects to PDF"    /insecure-test-link/checkout -L -X POST --cookie sus-cart.cookie-jar

# administrator tests
GAME_NAME="$RANDOM$RANDOM$RANDOM"
test_command "Planspiel erstellen"                          "gogross-create $GAME_NAME"
test_command "Erstelltes Planspiel ist sichtbar"            "gogross-list | grep -q -- $GAME_NAME"
# TODO: das testet nur auf gültiges JSON, nicht inhaltlich
test_command "Erstellte invoices sind sichtbar"             "gogross-dump-invoices | jq '.' > /dev/null"
test_command "Planspiel exportieren"                        "gogross-export 'Test Game'   > tmp.json"
test_command "Planspiel importieren"                        "gogross-import 'Test Game 2'   tmp.json"
# NOTE: das nächste ist ein begrenzter test auf die Sinnhaftigkeit des
# exports/imports. Da wir ansonsten nicht gut von hier auf die Planspiel-daten
# zugreifen können, belassen wir es dabei. Wir benutzen das mehr populierte
# 'Test Game'.
test_command "Datenverlust bei export ist idempotent"       $'[ $(gogross-export "Test Game 2" | md5sum | awk \'$0=$1\') == $(md5sum < tmp.json | awk \'$0=$1\') ]'
test_command "Planspiel löschen"                            "echo $GAME_NAME | gogross-delete $GAME_NAME"
test_command "Gelöschtes Planspiel ist nicht mehr sichtbar" "! gogross-list | grep -q -- $GAME_NAME"

# kill uwsgi. just $UWSGI_PID isn't enough due to forks.
pkill uwsgi
# simulate successful exit
exit 0
