
install:
	mkdir -p ~/.local/bin/
	cp dcode.py ~/.local/bin/

install-linux: install
	mkdir -p ~/.local/share/applications/
	cp linux/dcode.desktop ~/.local/share/applications/
	update-desktop-database ~/.local/share/applications/

install-mac: install
	cp dcode.py macos/DCode.app/Contents/Resources/
	# Just opening it will register the handler
	open macos/DCode.app

test-linux:
	xdg-open 'dcode://dcode/tests/some_file.txt?l=3\\&c=30'

test-mac:
	open 'dcode://dcode/tests/some_file.txt?l=3\\&c=30'
