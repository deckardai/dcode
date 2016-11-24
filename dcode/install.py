import os
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
    if os.geteuid() == 0:
        destination = "/usr/share/applications/"
    else:
        destination = "~/.local/share/applications/"
    print("Installing from {} into {}".format(path, destination))

    check_call("""
        mkdir -p {destination}
        cp {path} {destination}
        update-desktop-database {destination}
    """.format(path=path, destination=destination),
        shell=True)


def install():
    if sys.platform == "darwin":
        installMac()
    elif sys.platform.startswith("linux"):
        installLinux()
    else:
        print("Platform not supported.")
        return
    print("URL handler installed")


if __name__ == "__main__":
    install()
