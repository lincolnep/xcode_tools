#!/usr/bin/python

'''Programatically agree to the XCode license after XCode is installed.
Based on work done by Tim Sutton: https://macops.ca/deploying-xcode-the-trick-with-accepting-license-agreements/'''

import plistlib
import subprocess

from glob import glob

xcodePrefs = '/Library/Preferences/com.apple.dt.Xcode.plist'
licenseInfo = '/Applications/Xcode.app/Contents/Resources/LicenseInfo.plist'
xcodeInfo = '/Applications/Xcode.app/Contents/Info.plist'
installPkgs = True

# Accept the EULA
try:
    # Empty dict to use to write out the license agreed plist.
    acceptedLicense = {}

    # Read the license info file to get the license type state.
    xcodeLicense = plistlib.readPlist(licenseInfo)

    # Get Xcode version
    cmd = ['/usr/bin/defaults', 'read', xcodeInfo, 'CFBundleShortVersionString']
    (xcode_version, error) = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    xcode_version = xcode_version.strip('\n')

    if xcodeLicense['licenseType'] == 'GM':
        acceptedLicense['IDEXcodeVersionForAgreedToGMLicense'] = xcode_version
        acceptedLicense['IDELastGMLicenseAgreedTo'] = xcodeLicense['licenseID']
    elif xcodeLicense['licenseType'] in ['Seed', 'Beta']:
        acceptedLicense['IDEXcodeVersionForAgreedToBetaLicense'] = xcode_version
        acceptedLicense['IDELastBetaLicenseAgreedTo'] = xcodeLicense['licenseID']

    print 'Writing license file'
    plistlib.writePlist(acceptedLicense, xcodePrefs)
except Exception as e:
    raise e


# Install all the additional packages
if installPkgs:
    packages = glob('/Applications/Xcode.app//Contents/Resources/Packages/*.pkg')

# Loop the packages to install
    for pkg in packages:
        try:
            subprocess.check_call(['/usr/sbin/installer', '-pkg', pkg, '-target', '/'])
        except Exception as e:
            raise e
