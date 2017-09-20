#!/usr/bin/python

# Downloads the Xcode CLI tools from the Apple Software Update catalog
# Also includes the Xcode CLI SDK and Dev SDK
# Works for CLI Tools version 8.3.x, and 9.0. Just be careful which packages you install, as there are a few now that Xcode 9 is released.
# If you want to use the 10.13 catalog feed, just comment out line 14, and uncomment line 15.

import os
import plistlib
import subprocess
import urllib2

xcode_pkg_names = ['CLTools', 'DevSDK']
su_catalog = 'https://swscan.apple.com/content/catalogs/others/index-10.12.merged-1.sucatalog'  # NOQA
# su_catalog = 'https://swscan.apple.com/content/catalogs/others/index-10.13.merged-1.sucatalog'  # NOQA
output_path = os.path.expanduser('~/Desktop/')
request = urllib2.Request(su_catalog)
request = urllib2.urlopen(request)

catalog = plistlib.readPlistFromString(request.read())
request.close()


def curl(input_file, output_file):
    cmd = ['/usr/bin/curl', '--progress-bar', input_file, '-o', output_file]
    (result, error) = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE).communicate()
    if result:
        return result
    else:
        return error


for product in catalog['Products']:
    packages = catalog['Products'][product]['Packages']
    post_date = catalog['Products'][product]['PostDate']
    for item in packages:
        for pkg_name in xcode_pkg_names:
            if pkg_name in item['URL']:
                basename = os.path.basename(item['URL'])
                print 'Downloading %s (released %s)' % (
                    os.path.basename(item['URL']), post_date
                )
                curl(item['URL'], os.path.join(output_path, basename))
