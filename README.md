# Server Auto Config

# Overview
Server-auto-configs is about automatic config Ubuntu servers with Ansible. In this project, it install some requirements like Docker and docker-compose on servers for a DevOps engineer. 
Also, it has some roles for hardening servers.

https://github.com/adel-bz/Ansible-Server-Config/assets/45201934/46729180-8423-464c-b103-7bfbad9174b4
 

## Roles
We have 7 roles for the config Ubuntu servers.

### User Config Role: 
- In this role, we create a new user for servers and give access to the user to run ``` sudo ``` command without a password.
### Update Servers Role: 
- In this role, we update servers with ```apt-get update``` and ```apt-get upgrade``` commands.
### Install Dependencies Role: 
- This role is to install dependencies on servers. Dependencies include Nginx, Docker, docker-compose, Certbot, etc.
### Gitlab-Runner Role:
- Gitlab-Runner Role is to install and register gitlab-runner on servers.
### SSH Role:
- SSH Role is to config SSH service. First of all, we add SSH public key to servers for secure ssh connection and we change the ```sshd_config``` file in ```/etc/ssh/``` location with our sshd_config file. and in the end, we change the SSH port.


> **Note**
> 
> The ```sshd_config``` file has the best practices config for SSH but you can use your ```sshd_config``` file instead of our ```sshd_config``` file.

### Fail2ban Role:
- This role is to install and config fail2ban. fail2ban is a service for controlling SSH connections.

### Firewall Role:
- The firewall Role is the last one and this role is to config the UFW firewall, we open HTTP, HTTPS, and SSH ports on UFW, and also we enable UFW on servers. in the end, we restart the servers.

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


> **Note**
> 
> This project only works on Ubuntu OS (all versions) on a remote server.


> **Note**
> 
> You have to use a config file for ssh to servers. You can use this link https://linuxize.com/post/using-the-ssh-config-file/
>
> Or use another way to add servers to inventory.cnf file. You can see this link https://www.cherryservers.com/blog/how-to-set-up-ansible-inventory-file

> **Note**
> 
> Change ```config.yml``` file in ```/playbook``` directory. if you don't need a role in ```config.yml``` file, you must comment that role.

### Step 5:
- Run the below command on your terminal in the ```/playbook``` directory.

```
ansible-playbook -i inventory.cnf config.yml
``` 
- If a server needs a password for SSH connection, Run the below command to ask password:

```
ansible-playbook -i inventory.cnf config.yml -kK
``` 

# Test Project
If you will get an error like the below image it is mean your config is successful. You will get this error because you changed the SSH port and Ansible can't connect to the server with port 22.
![Screenshot from 2023-07-03 17-32-03](https://github.com/adel-bz/Ansible-Server-Config/assets/45201934/9a9ef4cc-5a39-4c47-9d58-a729da706942)

Or we won't have any errors like the below image.
![Screenshot from 2023-07-03 17-52-07](https://github.com/adel-bz/Ansible-Server-Config/assets/45201934/03e0c500-2a02-460c-a4b7-d200857ca954)
