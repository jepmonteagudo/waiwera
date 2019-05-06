# Geothermal VM Base Setup

This is the base level setup needed to start deploying software to a server

## Machine Setup
This section describes all the ways that waiwera model can be deployed on different operating systems and using different technologies.

### Setup Vagrant

Docker is recommended for **Windows <10 pro**.

Git, Vagrant, and VirtualBox need to be installed for this to work. The repository which sets up the test environment also needs to be cloned. See step below to setup vagrant:

1. Install Git from: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git
2. Install VirtualBox from: https://www.virtualbox.org/wiki/Downloads
3. Install Vagrant from: https://www.vagrantup.com/downloads.html (Make sure version >= 2)
4. Download the  setup from:`git clone https://timharton@bitbucket.org/timharton/geo-deploy.git`

### Setup Docker Build

For Docker on Windows, Windows 10 Pro is recommended.
Docker is compatible with both mac and linux as well.
Docker is the quickest way to deploy Waiwera.

Git and docker need to be installed for this to work. The repository which sets up the test environment also needs to be cloned. See step below to setup docker build:

1. Install Git from: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git
2. Install docker from https://www.docker.com/get-started
3. Download the  setup from:
`git clone https://timharton@bitbucket.org/timharton/geo-deploy.git`

### Setup Packer
Used for packaging docker images locally Similar to vagrant.

1. Install Git from: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git
2. Install docker from https://www.docker.com/get-started
3. Download the  setup from:
`git clone https://timharton@bitbucket.org/timharton/geo-deploy.git`

### Setup for Ansible

This setup can be used directly on linux machines

* Use pip to install ansible
  - i.e. `pip install --user ansible`

## Build Instructions

Used to build the waiwera project within the environment this can take some time.

### Vagrant Virtual Machine setup and Waiwera build

_GIT_USER and GIT_PWD are the passwords for accesing the supermodels git repo_

Open the command line for your operating system and follow these steps:

- Navigate to the he directory geo-deploy   `vagrant init`
- This only has to be done once to tell the system that this is vagrant deployment directory
- `GIT_USER='#########' GIT_PWD='#######' vagrant up` - starts a VM (virtual machine) named `waiwera`
- This could take some time as it builds and installs all the dependencies required
- `vagrant ssh` - connects via ssh to the machine. Within the `ssh` session run:
- should be logged in at `/vagrant` navigate to `/vagrant/waiwera`
- `python unit_tests.py`, all tests should pass
- `exit` will leave the ssh connection
- You are now done you can either destroy or suspend the `waiwera` VM
- `vagrant suspend` - suspends the VM
- `vagrant destroy` - destroys the VM

All commands should be run be run from the deployment directory. Otherwise the name of the machine can be added to the end of the vagrant command i.e. `vagrant suspend waiwera`.


### Packer Build
_For waiwera developers only_

Navigate to packer directory inside the geo-deploy directory

You can use packer to create and test docker images in 1 stop command. Which builds then tests the image locally. It can be extended to also push to the docker repository.

```
packer build -var-file=variables.json -var 'git_user=#####' -var 'git_pwd=##########' docker-packer.json
```

_Get some timeout errors during tests_

### Dockerfile Build

Navigate to the root of the geo-deploy directory

```
docker build -t waiwera . --build-arg "git_user=######" --build-arg "git_pwd=#########" --build-arg "app_dir=/opt/app"
```

Test the image by creating an ephemeral container and running the tests, these may time out given the system they are run on.

```
docker container run --rm -it --user 1000:1000 waiwera:latest python unit_tests.py
```
_Get some timeout errors during tests_

### Bitbucket Pipelines

File used to build and test the docker image using bitbucket continuous integration.

### Ansible Builds

To do an ansible build locally run the following command for the root of the geo-deploy directory

`ansible-playbook -c=local -vv -e "waiwera_user=#####" -e "waiwera_pwd=#####" -e "app_dir=#####" --skip-tags=docker,clean,vagrant /ansible/local.yml`

* `waiwera_user`= git user
* `waiwera_pwd` = git password
* `app_dir` = install location
