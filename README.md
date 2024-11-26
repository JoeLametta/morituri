# Whipper

[![license](https://img.shields.io/github/license/whipper-team/whipper.svg)](https://github.com/whipper-team/whipper/blob/develop/LICENSE)
[![Build Status](https://travis-ci.com/whipper-team/whipper.svg?branch=develop)](https://travis-ci.com/whipper-team/whipper)
[![GitHub (pre-)release](https://img.shields.io/github/release/whipper-team/whipper/all.svg)](https://github.com/whipper-team/whipper/releases/latest)
[![IRC](https://img.shields.io/badge/irc-%23whipper%40libera.chat-brightgreen.svg)](https://web.libera.chat/?channels=%23whipper)
[![GitHub Stars](https://img.shields.io/github/stars/whipper-team/whipper.svg)](https://github.com/whipper-team/whipper/stargazers)
[![GitHub Issues](https://img.shields.io/github/issues/whipper-team/whipper.svg)](https://github.com/whipper-team/whipper/issues)
[![GitHub contributors](https://img.shields.io/github/contributors/whipper-team/whipper.svg)](https://github.com/whipper-team/whipper/graphs/contributors)

Whipper is a Python 3 (3.6+) CD-DA ripper based on the [morituri project](https://github.com/thomasvs/morituri) (_CDDA ripper for *nix systems aiming for accuracy over speed_). It started just as a fork of morituri - which development seems to have halted - merging old ignored pull requests, improving it with bugfixes and new features. Nowadays whipper's codebase diverges significantly from morituri's one.

Whipper is currently developed and tested _only_ on Linux distributions but _may_ work fine on other *nix OSes too.

In order to track whipper's latest changes it's advised to check its commit history (README and [CHANGELOG](#changelog) files may not be comprehensive).

## Table of content

- [Rationale](#rationale)
- [Features](#features)
- [Changelog](#changelog)
- [Installation](#installation)
  * [Docker](#docker)
  * [Package](#package)
- [Building](#building)
  1. [Required dependencies](#required-dependencies)
  2. [Optional dependencies](#optional-dependencies)
  3. [Fetching the source code](#fetching-the-source-code)
  4. [Finalizing the build](#finalizing-the-build)
- [Usage](#usage)
- [Getting started](#getting-started)
- [Configuration file documentation](#configuration-file-documentation)
- [Running uninstalled](#running-uninstalled)
- [Logger plugins](#logger-plugins)
  * [Official logger plugins](#official-logger-plugins)
- [License](#license)
- [Contributing](#contributing)
  - [Developer Certificate of Origin (DCO)](#developer-certificate-of-origin-dco)
    - [DCO Sign-Off Methods](#dco-sign-off-methods)
  - [Bug reports & feature requests](#bug-reports--feature-requests)
- [Credits](#credits)
- [Links](#links)

## Rationale

For a detailed description, see morituri's wiki page: [The Art of the Rip](
https://web.archive.org/web/20160528213242/https://thomas.apestaart.org/thomas/trac/wiki/DAD/Rip).

## Features

- Detects correct read offset (in samples)
- Detects whether ripped media is a CD-R
- Has ability to defeat cache of drives
- Performs Test & Copy rips
- Verifies rip accuracy using the [AccurateRip database](http://www.accuraterip.com/)
- Uses [MusicBrainz](https://musicbrainz.org/doc/About) for metadata lookup
- Supports reading the [pre-emphasis](http://wiki.hydrogenaud.io/index.php?title=Pre-emphasis) flag embedded into some CDs (and correctly tags the resulting rip)
  - _Currently whipper only reports the pre-emphasis flag value stored in the TOC_
- Detects and rips _non digitally silent_ [Hidden Track One Audio](http://wiki.hydrogenaud.io/index.php?title=HTOA) (HTOA)
- Provides batch ripping capabilities
- Provides templates for file and directory naming
- Supports lossless encoding of ripped audio tracks (FLAC)
- Allows extensibility through external logger plugins

## Changelog

See [CHANGELOG.md](https://github.com/whipper-team/whipper/blob/develop/CHANGELOG.md).

For detailed information, please check the commit history.

## Installation

Whipper still isn't available as an official package in every Linux distributions so, in order to use it, it may be necessary to [build it from its source code](#building).

### Docker

You can easily install whipper without needing to care about the required dependencies by making use of the automatically built images hosted on [Docker Hub](https://hub.docker.com/r/whipperteam/whipper):

`docker pull whipperteam/whipper`

Please note that, right now, Docker Hub only builds whipper images for the `amd64` architecture: if you intend to use them on a different one, you'll need to build the images locally (as explained below).

Building the Docker image locally is required in order to make it work on Arch Linux (and its derivatives) because of a group permission issue (for more details see [issue #499](https://github.com/whipper-team/whipper/issues/499)).

To build the Docker image locally just issue the following command (it relies on the [Dockerfile](https://github.com/whipper-team/whipper/blob/develop/Dockerfile) included in whipper's repository):

`optical_gid=$(getent group optical | cut -d: -f3) uid=$(id -u) docker build --build-arg optical_gid --build-arg uid -t whipperteam/whipper .`

It's recommended to create an alias for a convenient usage:

```bash
alias whipper="docker run -ti --rm --device=/dev/cdrom \
    --mount type=bind,source=${HOME}/.config/whipper,target=/home/worker/.config/whipper \
    --mount type=bind,source=${PWD}/output,target=/output \
    whipperteam/whipper"
```

You should put this e.g. into your `.bash_aliases`. Also keep in mind to replace the path definitions to something that fits to your needs (e.g. replace `… -v ${PWD}/output:/output …` with `… -v ${HOME}/ripped:/output \ …`).

Essentially, what this does is to map the /home/worker/.config/whipper and ${PWD}/output (or whatever other directory you specified) on your host system to locations inside the Docker container where the files can be written and read. These directories need to exist on your system before you can run the container:

`mkdir -p "${HOME}/.config/whipper" "${PWD}/output"`

Please note that the example alias written above only provides access to a single disc drive: if you've got many you will need to customise it in order to use all of them in whipper's Docker container.

Finally, you can test the correct installation as such:

```
whipper -v
whipper drive list
```

### Package

This is a noncomprehensive summary which shows whipper's packaging status (unofficial repositories are probably not included):

[![Packaging status](https://repology.org/badge/vertical-allrepos/whipper.svg)](https://repology.org/metapackage/whipper)

**NOTE:** if installing whipper from an unofficial repository please keep in mind it is your responsibility to verify that the provided content is safe to use.

## Building

If you are building from a source tarball or checkout, you can choose to use whipper installed or uninstalled _but first install all the required dependencies_.

### Required dependencies

Whipper relies on the following packages in order to run correctly and provide all the supported features:

- [cd-paranoia](https://github.com/rocky/libcdio-paranoia), for the actual ripping
  - To avoid bugs it's advised to use `cd-paranoia` versions ≥ **10.2+0.94+2**
  - The package named `libcdio-utils`, available on older Debian and Ubuntu versions, is affected by a bug: it doesn't include the `cd-paranoia` binary (needed by whipper). Starting with Debian bullseye (11) and Ubuntu focal (20.04), a separate`cd-paranoia` package is available which provides the aforementioned binary. For more details on this issue, please check the relevant bug reports: [#888053 (Debian)](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=888053), [#889803 (Debian)](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=889803) and [#1750264 (Ubuntu)](https://bugs.launchpad.net/ubuntu/+source/libcdio/+bug/1750264).
- [cdrdao](http://cdrdao.sourceforge.net/), for session, TOC, pre-gap, and ISRC extraction
- [musicbrainzngs](https://pypi.org/project/musicbrainzngs/), for metadata lookup
- [mutagen](https://pypi.python.org/pypi/mutagen), for tagging support
- [setuptools](https://pypi.python.org/pypi/setuptools), for installation, plugins support
- [pycdio](https://pypi.python.org/pypi/pycdio/), for drive identification (required for drive offset and caching behavior to be stored in the configuration file).
  - To avoid bugs it's advised to use the most recent `pycdio` version with the corresponding `libcdio` release or, if stuck on old pycdio versions, **0.20**/**0.21** with `libcdio` ≥ **0.90** ≤ **0.94**. All other combinations won't probably work.
- [discid](https://pypi.org/project/discid/), for calculating Musicbrainz disc id.
- [ruamel.yaml](https://pypi.org/project/ruamel.yaml/), for generating well formed YAML report logfiles
- [libsndfile](http://www.mega-nerd.com/libsndfile/), for reading wav files
- [flac](https://xiph.org/flac/), for reading flac files
- [sox](http://sox.sourceforge.net/), for track peak detection
- [git](https://git-scm.com/) or [mercurial](https://www.mercurial-scm.org/)
  - Required either when running whipper without installing it or when building it from its source code (code cloned from a git/mercurial repository).

Some dependencies aren't available in the PyPI. They can be probably installed using your distribution's package manager:

- [cd-paranoia](https://github.com/rocky/libcdio-paranoia)
- [cdrdao](http://cdrdao.sourceforge.net/)
- [libsndfile](http://www.mega-nerd.com/libsndfile/)
- [flac](https://xiph.org/flac/)
- [sox](http://sox.sourceforge.net/)
- [git](https://git-scm.com/) or [mercurial](https://www.mercurial-scm.org/)
- [libdiscid](https://musicbrainz.org/doc/libdiscid)

PyPI installable dependencies are listed in the [requirements.txt](https://github.com/whipper-team/whipper/blob/develop/requirements.txt) file and can be installed issuing the following command:

`pip3 install -r requirements.txt`

### Optional dependencies
- [Pillow](https://pypi.org/project/Pillow/), for completely supporting the cover art feature (`embed` and `complete` option values won't work otherwise).
- [docutils](https://pypi.org/project/docutils/), to build the man pages.

These dependencies are not listed in the `requirements.txt`. To install them, just issue the following command:

`pip3 install Pillow docutils`

### Fetching the source code

Change to a directory where you want to put whipper source code (for example, `$HOME/dev/ext` or `$HOME/prefix/src`)

```bash
git clone https://github.com/whipper-team/whipper.git
cd whipper
```

### Finalizing the build

Install whipper: `python3 setup.py install`

Note that, depending on the chosen installation path, this command may require elevated rights.

To build the man pages, follow the instructions in the relevant [README](https://github.com/whipper-team/whipper/blob/develop/man/README.md) which is located in the `man` subfolder.

## Usage

Whipper currently only has a command-line interface called `whipper` which is self-documenting: `whipper -h` gives you the basic instructions.

Whipper implements a tree of commands: for example, the top-level `whipper` command has a number of sub-commands.

Positioning of arguments is important:

`whipper cd -d (device) rip`

is correct, while

`whipper cd rip -d (device)`

is not, because the `-d` argument applies to the `cd` command.

A more complete set of usage instructions can be found in the `whipper` [man pages](https://github.com/whipper-team/whipper/blob/develop/man/README.md).

## Getting started

The simplest way to get started making accurate rips is:

1. Pick a relatively popular CD that has a good chance of being in the AccurateRip database
2. Analyze the drive's caching behavior

   `whipper drive analyze`

3. Find the drive's offset.

   Consult the [AccurateRip's CD Drive Offset database](http://www.accuraterip.com/driveoffsets.htm) for your drive. Drive information can be retrieved with `whipper drive list`.

   `whipper offset find -o insert-numeric-value-here`

   If you omit the `-o` argument, whipper will try a long, popularity-sorted list of drive offsets.

   Please note that whipper's offset find feature is quite primitive so it may not always achieve its task: in this case using the value listed in [AccurateRip's CD Drive Offset database](http://www.accuraterip.com/driveoffsets.htm) should be enough.

   If you can not confirm your drive offset value but wish to set a default regardless, set `read_offset = insert-numeric-value-here` in `whipper.conf`.

   Offsets confirmed with `whipper offset find` are automatically written to the configuration file.

   If specifying the offset manually, please note that: if positive it must be written as a number without sign (ex: `+102` -> `102`), if negative it must include the sign too (ex: `-102` -> `-102`).

4. Rip the disc by running

   `whipper cd rip`

## Configuration file documentation

The configuration file is stored in `$XDG_CONFIG_HOME/whipper/whipper.conf`, or `$HOME/.config/whipper/whipper.conf` if `$XDG_CONFIG_HOME` is undefined.

See [XDG Base Directory
Specification](http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html)
and [ConfigParser](https://docs.python.org/3/library/configparser.html) with `inline_comment_prefixes=(';')`.

The configuration file consists of newline-delineated `[sections]`
containing `key = value` pairs. The sections `[main]` and
`[musicbrainz]` are special config sections for options not accessible
from the command line interface.  Sections beginning with `drive` are
written by whipper; certain values should not be edited. Inline comments can be added using `;`.

Example configuration demonstrating all `[main]` and `[musicbrainz]`
options:

```INI
[main]
path_filter_dot = True			; replace leading dot with _
path_filter_posix = True		; replace illegal chars in *nix OSes with _
path_filter_vfat = False		; replace illegal chars in VFAT filesystems with _
path_filter_whitespace = False		; replace all whitespace chars with _
path_filter_printable = False		; replace all non printable ASCII chars with _

[musicbrainz]
server = https://musicbrainz.org	; use MusicBrainz server at host[:port]
# use http as scheme if connecting to a plain http server. Example below:
# server = http://example.com:8080

[drive:HL-20]
defeats_cache = True			; whether the drive is capable of defeating the audio cache
read_offset = 6				; drive read offset in positive/negative frames (no leading +)
# do not edit the values 'vendor', 'model', and 'release'; they are used by whipper to match the drive

[drive:PIONEER%20%3ABD-RW%20%20%20BDR-209D%3A1.10]
defeats_cache = True
read_offset = 667
cdparanoia = cdparanoia			; cdparanoia executable to use.  Default is cd-paranoia
					; cd-paranoia has a bug that makes drives with large read_offset
					; unusable, see https://github.com/whipper-team/whipper/issues/234


# command line defaults for `whipper cd rip`
[whipper.cd.rip]
unknown = True
output_directory = ~/My Music
# Note: the format char '%' must be represented '%%'.
# Do not add inline comments with an unescaped '%' character (else an 'InterpolationSyntaxError' will occur).
track_template = new/%%A/%%y - %%d/%%t - %%n
disc_template =  new/%%A/%%y - %%d/%%A - %%d
# ...
```

## Running uninstalled

To make it easier for developers, you can run whipper straight from the
source checkout:

```bash
python3 -m whipper -h
```

## Logger plugins

Whipper allows using external logger plugins to customize the template of `.log` files.

The available plugins can be listed with `whipper cd rip -h`. Specify a logger to rip with by passing `-L loggername`:

```bash
whipper cd rip -L eac
```

Whipper searches for logger plugins in the following paths:

- `$XDG_DATA_HOME/whipper/plugins`
- Paths returned by the following Python instruction:

  `[x + '/whipper/plugins' for x in site.getsitepackages()]`

- If whipper is run in a `virtualenv`, it will use these alternative instructions (from `distutils.sysconfig`):
  - `get_python_lib(plat_specific=False, standard_lib=False, prefix='/usr/local') + '/whipper/plugins'`
  - `get_python_lib(plat_specific=False, standard_lib=False) + '/whipper/plugins'`

On a default Debian/Ubuntu installation, the following paths are searched by whipper:

- `$HOME/.local/share/whipper/plugins`
- `/usr/local/lib/python3.X/dist-packages/whipper/plugins`
- `/usr/lib/python3.X/dist-packages/whipper/plugins`

Where `X` stands for the minor version of the Python 3 release available on the system.

Please note that locally installed logger plugins won't be recognized when whipper has been installed through the official Docker image.

### Official logger plugins

I suggest using whipper's default logger unless you've got particular requirements.

- [whipper-plugin-eaclogger](https://github.com/whipper-team/whipper-plugin-eaclogger) - a plugin for whipper which provides EAC style log reports

## License

Licensed under the [GNU GPLv3 license](http://www.gnu.org/licenses/gpl-3.0).

```Text
Copyright (C) 2009 Thomas Vander Stichele
Copyright (C) 2016-2021 The Whipper Team: JoeLametta, Samantha Baldwin,
                        Merlijn Wajer, Frederik “Freso” S. Olesen, et al.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software Foundation,
Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
```

## Contributing

Make sure you have the latest copy from our [git
repository](https://github.com/whipper-team/whipper). Where possible,
please include tests for new or changed functionality. You can run tests
with `python3 -m unittest discover` from your source checkout.

### Developer Certificate of Origin (DCO)

To make a good faith effort to ensure licensing criteria are met, this project requires the Developer Certificate of Origin (DCO) process to be followed.

The Developer Certificate of Origin (DCO) is a document that certifies you own and/or have the right to contribute the work and license it appropriately. The DCO is used instead of a _much more annoying_
[CLA (Contributor License Agreement)](https://en.wikipedia.org/wiki/Contributor_License_Agreement). With the DCO, you retain copyright of your own work :). The DCO originated in the Linux community, and is used by other projects like Git and Docker.

The DCO agreement is shown below, and it's also available online: [HERE](https://developercertificate.org/).

```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.
1 Letterman Drive
Suite D4700
San Francisco, CA, 94129

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

#### DCO Sign-Off Methods

The DCO requires a sign-off message in the following format appear on each commit in the pull request:

```
Signed-off-by: Full Name <email>
```

The DCO text can either be manually added to your commit body, or you can add either `-s` or `--signoff` to your usual Git commit commands. If you forget to add the sign-off you can also amend a previous commit with the sign-off by running `git commit --amend -s`.

### Bug reports & feature requests

Please use the [issue tracker](https://github.com/whipper-team/whipper/issues) to report any bugs or to file feature requests.

When filing bug reports, please run the failing command with the environment variable `WHIPPER_DEBUG` set. For example:

```bash
WHIPPER_DEBUG=DEBUG WHIPPER_LOGFILE=whipper.log whipper offset find
gzip whipper.log
```

Finally, attach the gzipped log file to your bug report.

Without `WHIPPER_LOGFILE` set, logging messages will go to stderr. `WHIPPER_DEBUG` accepts a string of the [default python logging levels](https://docs.python.org/3/library/logging.html#logging-levels).

_If you can, please try to help to solve [THIS issue](https://github.com/rocky/libcdio-paranoia/issues/14) which also has an [open bounty](https://www.bountysource.com/issues/60536098-incorrectly-fetches-track-length-with-certain-offsets) on Bountysource._

## Credits

Thanks to:

- [Thomas Vander Stichele](https://github.com/thomasvs)
- [Joe Lametta](https://github.com/JoeLametta)
- [Samantha Baldwin](https://github.com/RecursiveForest)
- [Frederik “Freso” S. Olesen](https://github.com/Freso)
- [Merlijn Wajer](https://github.com/MerlijnWajer)

And to all the [contributors](https://github.com/whipper-team/whipper/graphs/contributors).

## Links

You can find us and talk about the project on:

- IRC: **`#whipper`** channel on the [Libera.Chat](ircs://irc.libera.chat:6697) network
  - See [Libera.Chat’s guide on how to connect](https://libera.chat/guides/connect)
    - Or just use the [Kiwi IRC web client](https://kiwiirc.com/nextclient/irc.libera.chat/?#whipper)
- Matrix (the room is a portal to Libera Chat's IRC channel)
  - Join to the room named **`#whipper`** (**`libera.chat`** is the homeserver)
  - Use Matrix's invite link for [#whipper:libera.chat](https://matrix.to/#/#whipper:libera.chat)
  - Access Matrix through the [Element web client](https://app.element.io/#/room/#whipper:libera.chat)
- [Redacted thread (official)](https://redacted.ch/forums.php?action=viewthread&threadid=150)

Other relevant links:
- [Whipper - Hydrogenaudio Knowledgebase](https://wiki.hydrogenaud.io/index.php?title=Whipper)
- [Repology: versions for whipper](https://repology.org/metapackage/whipper/versions)
- [Unattended ripping using whipper (by Thomas McWork)](https://github.com/thomas-mc-work/most-possible-unattended-rip)
