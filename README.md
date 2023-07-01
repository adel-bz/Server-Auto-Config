


# Requirements

### Ansible
You only have one Requirement. Install Ansible, You can use the below link to install Ansible on different os. 

https://adamtheautomator.com/install-ansible/

# Usage

### Step 1:
- Clone the project
```
$ git clone https://github.com/adel-bz/Ansible-Server-Config.git
```
### Step 2:
- Go to the project directory
```
$ cd Ansible-Server-Config
```

### Step 3:
- Change variables
  
 You can find all variables in the ```all.yml``` file in ```/playbook/group_vars``` directory.

### Step 4:
- Add remote servers to the inventory file.

you can find ```inventory.cnf``` file in ```/playbook``` directory.

#### Note 1: 
This project only works on Ubuntu os (all versions) on a remote server.

#### Note 2:
You have to use a config file for ssh to servers. You can use this link https://linuxize.com/post/using-the-ssh-config-file/

Or use another way to add servers in inventory.cnf file. You can use this link https://www.cherryservers.com/blog/how-to-set-up-ansible-inventory-file
