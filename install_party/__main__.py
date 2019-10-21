import sys
import os
import yaml

from install_party.creator.create import create
from install_party.eraser.delete import delete
from install_party.lister.list import get_and_print_list
from install_party.util import errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: install_party.py [mode] [options]\n")
        sys.exit(1)

    config_location = os.getenv("INSTALL_PARTY_CONFIG", "config.yaml")
    config_content = open(config_location).read()
    config = yaml.safe_load(config_content)

    mode = sys.argv[1]

    # Remove the mode from argv so that it doesn't interfere with the parsing of
    # arguments in the mode's code.
    if len(sys.argv) > 2:
        sys.argv = [sys.argv[0]] + sys.argv[2:]
    else:
        sys.argv = [sys.argv[0]]

    if mode == "create":
        try:
            create(config)
        except errors.InstanceCreationError:
            sys.stderr.write("An error occurred while building the instance. Aborting.\n")
            sys.exit(2)
    elif mode == "list":
        get_and_print_list(config)
    elif mode == "delete":
        delete(config)
    else:
        sys.stderr.write("Unknown mode %s. Available modes: create, list\n" % mode)

