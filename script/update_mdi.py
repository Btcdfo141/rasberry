#!/usr/bin/env python3
"""Download the latest Polymer v1 iconset for materialdesignicons.com."""
import hashlib
import gzip
import os
import re
import requests
import sys

GETTING_STARTED_URL = ('https://raw.githubusercontent.com/Templarian/'
                       'MaterialDesign/master/site/getting-started.savvy')
DOWNLOAD_LINK = re.compile(r'(/api/download/polymer/v1/([A-Z0-9-]{36}))')
START_ICONSET = '<iron-iconset-svg'

CUR_VERSION = re.compile(r'VERSION = "([A-Za-z0-9]{32})"')

OUTPUT_BASE = os.path.join('homeassistant', 'components', 'frontend')
VERSION_OUTPUT = os.path.join(OUTPUT_BASE, 'mdi_version.py')
ICONSET_OUTPUT = os.path.join(OUTPUT_BASE, 'www_static', 'mdi.html')
ICONSET_OUTPUT_GZ = os.path.join(OUTPUT_BASE, 'www_static', 'mdi.html.gz')


def get_local_version():
    """Parse the local version."""
    try:
        with open(VERSION_OUTPUT) as inp:
            for line in inp:
                match = CUR_VERSION.search(line)
                if match:
                    return match.group(1)
    except FileNotFoundError:
        return False
    return False


def get_remote_version():
    """Get current version and download link."""
    gs_page = requests.get(GETTING_STARTED_URL).text

    mdi_download = re.search(DOWNLOAD_LINK, gs_page)

    if not mdi_download:
        print("Unable to find download link")
        sys.exit()

    url = 'https://materialdesignicons.com' + mdi_download.group(1)
    version = mdi_download.group(2).replace('-', '')

    return version, url


def clean_component(source):
    """Clean component."""
    return source[source.index(START_ICONSET):]


def write_component(version, source):
    """Write component."""
    with open(ICONSET_OUTPUT, 'w') as outp:
        print('Writing icons to', ICONSET_OUTPUT)
        outp.write(source)

    with gzip.open(ICONSET_OUTPUT_GZ, 'wb') as outp:
        print('Writing icons gz to', ICONSET_OUTPUT_GZ)
        outp.write(source.encode('utf-8'))

    with open(VERSION_OUTPUT, 'w') as outp:
        print('Generating version file', VERSION_OUTPUT)
        outp.write(
            '"""DO NOT MODIFY. Auto-generated by update_mdi script."""\n')
        outp.write('VERSION = "{}"\n'.format(version))


def main():
    """Main section of the script."""
    # All scripts should have their current work dir set to project root
    if os.path.basename(os.getcwd()) == 'script':
        os.chdir('..')

    print("materialdesignicons.com icon updater")

    local_version = get_local_version()

    # The remote version is not reliable.
    _, remote_url = get_remote_version()

    source = clean_component(requests.get(remote_url).text)
    new_version = hashlib.md5(source.encode('utf-8')).hexdigest()

    if local_version == new_version:
        print('Already on the latest version.')
        sys.exit()

    write_component(new_version, source)
    print('Updated to latest version')

if __name__ == '__main__':
    main()
