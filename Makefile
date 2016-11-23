
install:
	pip install --user -v --upgrade .

dev:
	pip install --user -v -e .

install-copy:
	mkdir -p ~/.local/bin/
	cp dcode/dcode.py ~/.local/bin/

install-linux: install-copy
	mkdir -p ~/.local/share/applications/
	cp dcode/linux/dcode.desktop ~/.local/share/applications/
	update-desktop-database ~/.local/share/applications/

install-mac: install-copy
	# Just opening it will register the handler
	open dcode/macos/DCode.app

test-linux:
	xdg-open 'dcode://dcode/tests/some_file.txt?l=3\\&c=30'

test-mac:
	open 'dcode://dcode/tests/some_file.txt?l=3&c=30'
