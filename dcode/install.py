import sys
import pkg_resources
from subprocess import check_call


def installMac():
    # Just opening the mac app will register the handler
    path = pkg_resources.resource_filename("dcode", "macos/")
    print("Installing from " + path)
    check_call(["open", path])


def installLinux():
    path = pkg_resources.resource_filename("dcode", "linux/dcode.desktop")
    check_call("""
        mkdir -p ~/.local/share/applications/
        cp %s ~/.local/share/applications/
        update-desktop-database ~/.local/share/applications/
    """ % path, shell=True)


def install():
    if sys.platform == "darwin":
        installMac()
    elif sys.platform == "linux":
        installLinux()
    else:
        print("Platform not supported.")
        return
    print("URL handler installed")
