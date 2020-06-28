HTML_DIR = /var/www/html
CGI_DIR = /var/www/cgi-bin

all: $(HTML_DIR)/twixt.html $(HTML_DIR)/jquery-3.3.1.min.js $(CGI_DIR)/bot

$(HTML_DIR)/twixt.html: twixt.html
	install -c -m 0555 $< $(HTML_DIR)

$(HTML_DIR)/jquery-3.3.1.min.js: jquery-3.3.1.min.js
	install -c -m 0555 $< $(HTML_DIR)

$(CGI_DIR)/bot: bot.cgi
	install -c -m 0555 $< $(CGI_DIR)/bot
