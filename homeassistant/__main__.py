""" Starts home assistant. """
from __future__ import print_function

import sys
import os
import argparse
import subprocess
import importlib

DEPENDENCIES = ['requests>=2.0', 'pyyaml>=3.11', 'pytz>=2015.2']
IS_VIRTUAL = (getattr(sys, 'base_prefix', sys.prefix) != sys.prefix or
              hasattr(sys, 'real_prefix'))


def validate_python():
    """ Validate we're running the right Python version. """
    major, minor = sys.version_info[:2]

    if major < 3 or (major == 3 and minor < 4):
        print("Home Assistant requires atleast Python 3.4")
        sys.exit()


def ensure_pip():
    """ Validate pip is installed so we can install packages on demand. """
    if importlib.find_loader('pip') is None:
        print("Your Python installation did not bundle 'pip'")
        print("Home Assistant requires 'pip' to be installed.")
        print("Please install pip: "
              "https://pip.pypa.io/en/latest/installing.html")
        sys.exit()


# Copy of homeassistant.util.package because we can't import yet
def install_package(package):
    """Install a package on PyPi. Accepts pip compatible package strings.
    Return boolean if install successfull."""
    args = [sys.executable, '-m', 'pip', 'install', '--quiet', package]
    if not IS_VIRTUAL:
        args.append('--user')
    try:
        return 0 == subprocess.call(args)
    except subprocess.SubprocessError:
        return False


def validate_dependencies():
    """ Validate all dependencies that HA uses. """
    ensure_pip()

    print("Validating dependencies...")
    import_fail = False

    for requirement in DEPENDENCIES:
        if not install_package(requirement):
            import_fail = True
            print('Fatal Error: Unable to install dependency', requirement)

    if import_fail:
        print(("Install dependencies by running: "
               "python3 -m pip install -r requirements.txt"))
        sys.exit()


def ensure_path_and_load_bootstrap():
    """ Ensure sys load path is correct and load Home Assistant bootstrap. """
    try:
        from homeassistant import bootstrap

    except ImportError:
        # This is to add support to load Home Assistant using
        # `python3 homeassistant` instead of `python3 -m homeassistant`

        # Insert the parent directory of this file into the module search path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

        from homeassistant import bootstrap

    return bootstrap


def validate_git_submodules():
    """ Validate the git submodules are cloned. """
    try:
        # pylint: disable=no-name-in-module, unused-variable
        from homeassistant.external.noop import WORKING  # noqa
    except ImportError:
        print("Repository submodules have not been initialized")
        print("Please run: git submodule update --init --recursive")
        sys.exit()


def ensure_config_path(config_dir):
    """ Gets the path to the configuration file.
        Creates one if it not exists. """

    # Test if configuration directory exists
    if not os.path.isdir(config_dir):
        print(('Fatal Error: Unable to find specified configuration '
               'directory {} ').format(config_dir))
        sys.exit()

    import homeassistant.config as config_util

    config_path = config_util.ensure_config_exists(config_dir)

    if config_path is None:
        print('Error getting configuration path')
        sys.exit()

    return config_path


def get_arguments():
    """ Get parsed passed in arguments. """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--config',
        metavar='path_to_config_dir',
        default="config",
        help="Directory that contains the Home Assistant configuration")
    parser.add_argument(
        '--demo-mode',
        action='store_true',
        help='Start Home Assistant in demo mode')
    parser.add_argument(
        '--open-ui',
        action='store_true',
        help='Open the webinterface in a browser')

    return parser.parse_args()


def main():
    """ Starts Home Assistant. """
    validate_python()
    validate_dependencies()

    # Windows needs this to pick up new modules
    importlib.invalidate_caches()

    bootstrap = ensure_path_and_load_bootstrap()

    validate_git_submodules()

    args = get_arguments()

    config_dir = os.path.join(os.getcwd(), args.config)
    config_path = ensure_config_path(config_dir)

    if args.demo_mode:
        from homeassistant.components import frontend, demo

        hass = bootstrap.from_config_dict({
            frontend.DOMAIN: {},
            demo.DOMAIN: {}
        })
    else:
        hass = bootstrap.from_config_file(config_path)

    if args.open_ui:
        from homeassistant.const import EVENT_HOMEASSISTANT_START

        def open_browser(event):
            """ Open the webinterface in a browser. """
            if hass.config.api is not None:
                import webbrowser
                webbrowser.open(hass.config.api.base_url)

        hass.bus.listen_once(EVENT_HOMEASSISTANT_START, open_browser)

    hass.start()
    hass.block_till_stopped()

if __name__ == "__main__":
    main()
