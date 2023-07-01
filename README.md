


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
- Go to the project directory.
```
$ cd Ansible-Server-Config
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
