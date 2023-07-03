# Ansible Servers Config


# Overview
This project is about config servers with Ansible. In this project, we install some dependence services like Docker and docker-compose for DevOps engineers.
Also, we wrote some roles for hardening servers.
We have 7 roles for the config servers:
#### Role 1: 
In this role, we create a new user for servers and give access to the user to run ``` sudo ``` command without a password.
#### Role 2: 
In this role, we update servers with ```apt-get update``` and ```apt-get upgrade``` commands.
#### Role 3: 
This role is to install dependencies on servers. Dependencies include Nginx, Docker, docker-compose, Certbot and etc.
#### Role 4:
Role 4 is to install and register gitlab-runner on servers.
#### Role 5:
Role 5 is to config SSH service. First of all, we add SSH public key to servers for secure ssh connection and we change the ```sshd_config``` file in ```/etc/ssh/``` location with our sshd_config file. and in the end, we change SSH port.
##### Note: The sshd_config file has the best practices config for SSH but you can use your sshd_config file instead of our sshd_config file.

#### Role 6:
This role is to install and config fail2ban. fail2ban is a service for controlling SSH connections.

#### Role 7:
Role 7 is the last role and this role is to config the UFW firewall, we open HTTP, HTTPS, and SSH ports on UFW, also we enable UFW on servers. in the end, we restart the servers.
# Requirements

### Ansible
You only have one Requirement. Install Ansible, You can use the below link to install Ansible on different os. 

https://adamtheautomator.com/install-ansible/

# Usage

### Step 1:
- Clone the project
```
git clone https://github.com/adel-bz/Ansible-Server-Config.git
```
### Step 2:
- Go to the project directory.
```
cd Ansible-Server-Config
```
### Step 3:
- Change variables in the ```all.yml``` file in ```/playbook/group_vars``` directory.
  
### Step 4:
- Add remote servers to the ```inventory.cnf``` file in ```/playbook``` directory.


#### Note 1: 
This project only works on Ubuntu os (all versions) on a remote server.

#### Note 2:
You have to use a config file for ssh to servers. You can use this link https://linuxize.com/post/using-the-ssh-config-file/

Or use another way to add servers in inventory.cnf file. You can use this link https://www.cherryservers.com/blog/how-to-set-up-ansible-inventory-file

- Change ```config.yml``` file in ```/playbook``` directory. if you don't need a role in ```config.yml``` file, you must comment that role.

### Step 5:
- Run the below command on your terminal in the ```/playbook``` directory.

```
ansible-playbook -i inventory.cnf config.yml
``` 
