import os
import sys
import pkg_resources
from subprocess import check_call


def installMac():
    # Just opening the mac app will register the handler
    path = pkg_resources.resource_filename("dcode", "macos/DCode.app/Contents/MacOS/applet")
    print("Installing from " + path)
    print("\nYou should see a confirmation dialog.")
    check_call([path])


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
    print(
        "\n"
        "URL handler installed. \n"
        "Try to click the following link using Ctrl or Cmd: \n"
        "\n"
        "    dcode://_demo/demo.txt?l=3&c=30 \n"
        "\n"
    )


if __name__ == "__main__":
    install()
