#!/usr/bin/env python

'''Downloads the Xcode CLI tools using the Apple Software Update catalog.'''

import argparse  # NOQA
import gzip  # NOQA
import xml.etree.ElementTree as ET  # NOQA
import os  # NOQA
import plistlib  # NOQA
import shutil  # NOQA
import subprocess  # NOQA
import sys  # NOQA

from distutils.version import LooseVersion  # NOQA
from platform import mac_ver  # NOQA
from pprint import pprint  # NOQA


class XcodeCLI():
    def __init__(self, allow_untrusted_pkg_install=False, catalog=False, destination=False, dry_run=False, install=False, install_target=False, mac_os_ver=False, quiet=False):
        '''Initialise class XcodeTools() with various attributes.'''
        '''Attributes:'''
        '''    catalog = override the catalog with your own catalog URL'''
        '''    destination = override the download destination with your own folder path'''
        '''    dry_run = output to stdout what will be downloaded'''
        '''    install = install packages after they are downloaded'''
        '''    mac_os_ver = override the version of macOS you are downloading for'''
        '''    quiet = suppresses stdout output'''
        self.allow_untrusted_pkg_install = allow_untrusted_pkg_install
        self.catalog = catalog
        if destination:
            self.destination = os.path.expandvars(os.path.expanduser(destination))
        else:
            self.destination = '/tmp/xcode'
        self.dry_run = dry_run
        self.install = install
        if install_target:
            self.install_target = install_target
        else:
            self.install_target = '/'
        self.system_mac_os_ver = '.'.join(mac_ver()[0].split('.')[:2])  # Use this for install checks to avoid installing incorrect versions when overriding mac_os_ver
        if not mac_os_ver:
            # Only need the major OS release version to form the url - example: '10.13'
            self.mac_os_ver = '.'.join(mac_ver()[0].split('.')[:2])
        else:
            # Only need the major OS release version to form the url - example: '10.13'
            self.mac_os_ver = '.'.join(mac_os_ver.split('.')[:2])
        self.quiet = quiet

        # Messages to use in dry run
        if self.dry_run:
            self.download_msg, self.install_msg, self.cleanup_msg = 'Download', 'Install', 'Remove'
        else:
            self.download_msg, self.install_msg, self.cleanup_msg = 'Downloading', 'Installing', 'Removing'

        # Construct a dictionary of known software update catalogs
        # Thanks to Pike: https://pikeralpha.wordpress.com/2017/06/06/catalogurl-for-macos-10-13-high-sierra/
        # Hopefully this URL format doesn't change for each release, as at 2018-08-05 it hasn't for OS releases 10.11+
        # Note - these beta/customerseed/seed URL's don't seem to actually be of any benefit unless you're using the full
        # https://swscan.apple.com/content/catalogs/others/index-10.13seed-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog.gz
        # style address, in which case it gets annoying to work out what version of macOS the tools/sdk are actually for.
        # Leaving this capability in on the off chance it does work one day, but for the time being, the -c, --catalog argument is basically useless.
        self.swscan_url = 'https://swscan.apple.com/content/catalogs/others/index-'
        self.catalogs = {
            'beta': 'beta',
            'customerseed': 'customerseed',
            'developerseed': 'seed',
        }

        # Range of OS releases this tool supports
        self.supported_os_versions = ['10.9', '10.10', '10.11', '10.12', '10.13', '10.14']

        # Xcode package names to check
        self.pkg_names = ['CLTools', 'DevSDK']

        # SU Catalog URL to use
        self.sucatalog_url = self.swscanURL(self.mac_os_ver, self.catalog)

        # Empty dictionary to store found packages
        self.packages_to_process = {}

    def swscanURL(self, mac_os_ver, catalog=None):
        '''Returns a string containing the sucatalog URL path to be used to check for Xcode Tools. Do not call directly.'''
        try:
            if catalog:
                return '{}{}{}.merged-1.sucatalog.gz'.format(self.swscan_url, mac_os_ver, self.catalogs[catalog])
            else:
                return '{}{}.merged-1.sucatalog.gz'.format(self.swscan_url, mac_os_ver)
        except Exception:
            raise

    def processSUCatalog(self):
        try:
            if not self.quiet:
                print 'Retrieving software catalog: {}'.format(self.sucatalog_url)
            destination_file = os.path.join(self.destination, os.path.basename(self.sucatalog_url))

            # Try and remove any existing sucatalog file
            try:
                os.remove(destination_file)
            except:
                pass

            # Download the sucatalog
            self.curl(self.sucatalog_url, destination_file, quiet=True)

            # Read in the GZ file with gzip
            with gzip.open(destination_file, 'rb') as sucatalog_file:
                catalog = sucatalog_file.read()

            # Process the catalog file into a dictionary
            catalog = plistlib.readPlistFromString(catalog)

            # Iterate, yo.
            for product in catalog['Products']:
                packages = catalog['Products'][product]['Packages']
                post_date = catalog['Products'][product]['PostDate']
                for item in packages:
                    for pkg_name in self.pkg_names:
                        if pkg_name in item['URL']:
                            basename = os.path.basename(item['URL'])
                            product_id = product
                            metadataSMDurl = catalog['Products'][product]['ServerMetadataURL']
                            metadataPKMurl = item['MetadataURL']
                            metadata = self.processMetadata(smd_url=metadataSMDurl, pkm_url=metadataPKMurl)
                            pkg_ver = metadata['pkg_version']
                            long_pkg_ver = metadata['long_pkg_version']
                            pkg_id = metadata['pkg_identifier']
                            pkg_title = metadata['pkg_title']
                            # Change the destination filename so it's clear what version of macOS and what version of CL tools.
                            pkg_download_name = os.path.join(self.destination, basename.replace('.pkg', '_macOS_{}-{}.pkg'.format(self.mac_os_ver, '.'.join(long_pkg_ver.split('.')[:3]))))

                            # Test if combo already exists in dictionary and if so, version comparison test to make sure only latest version gets added
                            if basename not in self.packages_to_process.keys():
                                self.packages_to_process[basename] = {'product_id': product_id, 'pkg_title': pkg_title, 'pkg': basename, 'url': item['URL'], 'post_date': post_date, 'version': pkg_ver, 'long_version': long_pkg_ver, 'pkg_identifier': pkg_id, 'download_name': pkg_download_name}
                            elif basename in self.packages_to_process.keys() and LooseVersion(long_pkg_ver) > LooseVersion(self.packages_to_process[basename]['long_version']):
                                self.packages_to_process[basename] = {'product_id': product_id, 'pkg_title': pkg_title, 'pkg': basename, 'url': item['URL'], 'post_date': post_date, 'version': pkg_ver, 'long_version': long_pkg_ver, 'pkg_identifier': pkg_id, 'download_name': pkg_download_name}

            # Remove the file now we're finished with it
            try:
                os.remove(destination_file)
            except Exception:
                pass
        except Exception:
            raise

    def processMetadata(self, smd_url, pkm_url):
        smd_destination_file = os.path.join(self.destination, os.path.basename(smd_url))
        pkm_destination_file = os.path.join(self.destination, os.path.basename(pkm_url))
        try:
            os.remove(smd_destination_file)
            os.remove(pkm_destination_file)
        except Exception:
            pass
        try:
            self.curl(smd_url, smd_destination_file, quiet=True)
            self.curl(pkm_url, pkm_destination_file, quiet=True)
            meta_tree = ET.parse(pkm_destination_file)
            meta_root = meta_tree.getroot()
            long_pkg_version = meta_root.attrib['version']
            pkg_identifier = meta_root.attrib['identifier']
            metadata = plistlib.readPlist(smd_destination_file)
            pkg_version = metadata['CFBundleShortVersionString']
            pkg_title = metadata['localization']['English']['title']

            # Remove the file now we're finished with it
            try:
                os.remove(smd_destination_file)
                os.remove(pkm_destination_file)
            except Exception:
                pass

            return {'long_pkg_version': long_pkg_version, 'pkg_version': pkg_version, 'pkg_identifier': pkg_identifier, 'pkg_title': pkg_title}
        except Exception:
            raise

    def curl(self, input_file, output_file, quiet=False):
        cmd = ['/usr/bin/curl']

        # quiet or progress bar depending on XcodeTools() attributes
        if self.quiet or quiet:
            cmd.extend(['--silent'])
        else:
            cmd.extend(['--progress-bar'])

        # Try and auto resume from offset if file exists and server supports it, also create destination directory if it doesn't exist
        if not os.path.exists(output_file):  # Rudimentary block on downloading a file if it already exists. SU servers don't seem to support resuming downloads from an offset.
            cmd.extend(['-L', '-C', '-', input_file, '--create-dirs', '-o', output_file])
            subprocess.check_call(cmd)

    def installPkg(self, package):
        cmd = ['/usr/sbin/installer', '-pkg', package]
        if self.allow_untrusted_pkg_install:
            cmd.extend(['--allowUntrusted'])
        cmd.extend(['-target', self.install_target])

        if not self.dry_run:
            if LooseVersion(self.system_mac_os_ver) == LooseVersion(self.mac_os_ver):
                print '{} {}'.format(self.install_msg, package)
                (result, error) = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

                if 'successful' in result:
                    result_msg = 'install successful'
                if 'upgrade' in result:
                    result_msg = 'upgrade successful'
                if error or any(x in result.lower() for x in ['fail', 'failed']):
                    result_msg = 'install/upgrade failed, see /var/log/install.log'

                print '{} {}'.format(package, result_msg)
            else:
                print 'Not a good idea to try and install macOS {} CL tools on macOS {}'.format(self.mac_os_ver, self.system_mac_os_ver)
                print 'Downloaded files can be found in {}'.format(self.destination)
                sys.exit(1)

    def mainProcessor(self):
        if self.install and os.getuid() is not 0:
            print 'Must be root to install packages.'
            sys.exit(1)

        self.processSUCatalog()

        # Note, not all catalogs contain the downloads once GM's are released
        if not self.packages_to_process:
            print 'No Command Line Tool downloads found'
            sys.exit(0)

        # There are packages that remove older SDK's, these may need to be installed first
        remove_pkgs = [pkg for pkg in self.packages_to_process.keys() if 'Remove' in pkg]
        if remove_pkgs:
            remove_pkgs.sort()
        for pkg in self.packages_to_process:
            product_id = self.packages_to_process[pkg]['product_id']
            title = self.packages_to_process[pkg]['pkg_title']
            pkg_url = self.packages_to_process[pkg]['url']
            download_file = self.packages_to_process[pkg]['download_name']
            version = self.packages_to_process[pkg]['version']
            date = self.packages_to_process[pkg]['post_date']
            if not self.quiet and not os.path.exists(download_file):
                print '{} {} - {} (version {} released {}) to {}'.format(self.download_msg, product_id, title, version, date, download_file)
            if not self.dry_run:
                self.curl(input_file=pkg_url, output_file=download_file)

        if self.install:
            for pkg in remove_pkgs:
                try:
                    if not self.dry_run:
                        self.installPkg(self.packages_to_process[pkg]['download_name'])
                except Exception:
                    raise

            for pkg in self.packages_to_process:
                # Only install if pkg is not in remove_pkgs
                if pkg not in remove_pkgs:
                    print '{} {}'.format(self.install_msg, self.packages_to_process[pkg]['download_name'])
                    if not self.dry_run:
                        try:
                            self.installPkg(self.packages_to_process[pkg]['download_name'])
                        except Exception:
                            raise
            try:
                if not self.quiet:
                    print '{} {}'.format(self.cleanup_msg, self.destination)
                shutil.rmtree(self.destination)
            except Exception:
                raise


def main():
    class SaneUsageFormat(argparse.HelpFormatter):
        '''Makes the help output somewhat more sane. Code used was from Matt Wilkie.'''
        '''http://stackoverflow.com/questions/9642692/argparse-help-without-duplicate-allcaps/9643162#9643162'''

        def _format_action_invocation(self, action):
            if not action.option_strings:
                default = self._get_default_metavar_for_positional(action)
                metavar, = self._metavar_formatter(action, default)(1)
                return metavar

            else:
                parts = []

                # if the Optional doesn't take a value, format is:
                #    -s, --long
                if action.nargs == 0:
                    parts.extend(action.option_strings)

                # if the Optional takes a value, format is:
                #    -s ARGS, --long ARGS
                else:
                    default = self._get_default_metavar_for_optional(action)
                    args_string = self._format_args(action, default)
                    for option_string in action.option_strings:
                        parts.append(option_string)

                    return '%s %s' % (', '.join(parts), args_string)

                return ', '.join(parts)

        def _get_default_metavar_for_optional(self, action):
            return action.dest.upper()

    parser = argparse.ArgumentParser(formatter_class=SaneUsageFormat)
    exclude = parser.add_mutually_exclusive_group()

    parser.add_argument(
        '--allowUntrusted',
        action='store_true',
        dest='allow_untrusted',
        help='Runs the install process with the --allowUntrusted argument.',
        required=False
    )

    parser.add_argument(
        '-c', '--catalog',
        type=str,
        nargs=1,
        dest='alternate_catalog',
        metavar='<catalog>',
        choices=['beta', 'customerseed', 'developerseed'],
        help='Specify a non standard softare update catalog (such as beta/customer/developer seed). Note, this is pretty much pointless as the CLTools and SDK packages are pretty much the same files regardless of which program catalog you access.',
    )

    parser.add_argument(
        '-d', '--destination',
        type=str,
        nargs=1,
        dest='download_destination',
        metavar='<destination path>',
        help='Specify alternative folder path for downloaded contents to be stored.',
        required=False
    )

    exclude.add_argument(
        '-n', '--dry-run',
        action='store_true',
        dest='dry_run',
        help='Dry run only, no action taken.',
        required=False,
    )

    parser.add_argument(
        '-i', '--install',
        action='store_true',
        dest='install_packages',
        help='Installs packages after downloading.',
        required=False,
    )

    parser.add_argument(
        '-t', '--target',
        nargs=1,
        dest='install_target',
        metavar='<target>',
        help='Specify alternative target location for installer.',
        required=False
    )

    parser.add_argument(
        '--mac-os-ver',
        nargs=1,
        dest='mac_os_versions',
        metavar='<os version>',
        choices=['10.9', '10.10', '10.11', '10.12', '10.13', '10.14'],
        help='Specify alternative macOS release to download tools for. If not supplied, defaults to version of macOS installed on client.',
        required=False
    )

    exclude.add_argument(
        '-q', '--quiet',
        action='store_true',
        dest='quiet_output',
        help='Suppress all stdout output.',
        required=False
    )

    args = parser.parse_args()

    if args.alternate_catalog and len(args.alternate_catalog) is 1:
        alt_catalog = args.alternate_catalog[0]
    else:
        alt_catalog = False

    if args.download_destination and len(args.download_destination) is 1:
        download_dest = args.download_destination[0]
    else:
        download_dest = False

    if args.install_target and len(args.install_target) is 1:
        target = args.install_target[0]
    else:
        target = False

    if args.mac_os_versions and len(args.mac_os_versions) is 1:
        mac_vers = args.mac_os_versions[0]
    else:
        mac_vers = False

    xcode = XcodeCLI(allow_untrusted_pkg_install=args.allow_untrusted, catalog=alt_catalog, destination=download_dest, dry_run=args.dry_run, install=args.install_packages, install_target=target, mac_os_ver=mac_vers, quiet=args.quiet_output)
    xcode.mainProcessor()


if __name__ == '__main__':
    main()
