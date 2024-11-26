# whipper-docker.sh

## Requirements
* whipper
* docker

## Deployment
 1. Copy whipper-docker.sh to accessible location. In a directory where the path is defined is optimal.
 2. Make whipper-docker executable. ie. chmod +x whipper-docker.sh
 3. If default configuration meet your need then you are done, else create a configuration file. 

## Configuration
First, the script reads the default configuration. Then, the whipper-docker.sh script looks for system settings in /etc/whipper-docker.conf. Finally, whipper-docker looks for it's configuration file in the ${HOME}/.config/whipper-docker.conf file. The last defined variable definition wins.

### Configuration Parameters

#### CD_DEVICE
Defines the location of CD device file. Defaults to the /dev/cdrom device file.

#### OUTPUT_DIR
Defiles the root directory where ripped music will be placed. Defaults to the ${HOME}/Music directory.

#### PERSONAL_CONF_DIR
This variable defines where your whipper configuration will be saved outside of the docker image. It defaults to the ${HOME}/.config/whipper directory.



 