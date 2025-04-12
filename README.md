# Telegram-AList bot

[![Readme Card](https://github-readme-stats.vercel.app/api/pin/?username=alist-org&repo=alist)](https://github.com/alist-org/alist)

**Main Features:**

- [x] Search
    - [x] Basic file information
    - [x] Custom result quantity
    - [x] Direct file link
- [x] Storage
    - [x] Enable/Disable storage
    - [x] Delete storage
    - [x] Copy storage
    - [x] Create new storage
    - [x] Auto sorting
    - [x] Batch create storage
- [x] Cloudflare Node Management
    - [x] Node monitoring
    - [x] Notifications
        - [x] Node status
        - [x] Daily traffic statistics
    - [x] Automatic storage management
    - [x] Automatic node switching
    - [x] Cloudflare account management
    - [x] Proxy load balancing
    - [x] Random storage node
    - [x] Unified storage node
- [x] Alist configuration backup & scheduled backup
- [x] Alist image hosting
- [x] Random recommendation
- [x] Offline download

### Features Preview & Description:

<details>
<summary><b>Click to Expand</b></summary>


<details>
<summary><b>Search</b></summary>

![Search Preview](https://img.155155155.xyz/2023/12/1703834393546.png)

</details>

<details>
<summary><b>Configuration Backup</b></summary>

You can reply to messages to add notes, and modify them repeatedly.

![Configuration Backup](https://img.155155155.xyz/2023/12/1703835568828.gif)

</details>


<details>
<summary><b>Storage Management Menu</b></summary>

![Manage Storage](https://img.155155155.xyz/2023/12/1703835610320.png)

</details>


<details>
<summary><b>Enable/Disable Storage</b></summary>

![Manage Storage](https://img.155155155.xyz/2023/12/1703835984793.png)

</details>


<details>
<summary><b>Copy Storage</b></summary>

Automatically copies storage for load balancing, and storage sorting will automatically increment by 1.  
![Copy Storage](https://img.155155155.xyz/2023/12/1703836021621.png)

</details>


<details>
<summary><b>Delete Storage</b></summary>

![Delete Storage](https://img.155155155.xyz/2023/12/1703836083261.png)

</details>


<details>
<summary><b>Create & Batch Create & Default Configuration</b></summary>

<details>
<summary><b> - Create & Batch Create</b></summary>

Supports adding all storage types supported by AList.

![Create & Batch Create](https://img.155155155.xyz/2023/12/1703836646184.png)

![Create & Batch Create](https://img.155155155.xyz/2023/12/1703836713207.png)

**Add Single**

![Create & Batch Create](https://img.155155155.xyz/2023/12/1703836862502.png)

**Batch Add**

![Create & Batch Create](https://img.155155155.xyz/2023/12/1703836915002.png)

![Create & Batch Create](https://img.155155155.xyz/2023/12/1703836982303.png)

![Create & Batch Create](https://img.155155155.xyz/2023/12/1703837216466.png)


</details>


<details>
<summary><b> - Default Configuration</b></summary>

You can set default configurations, and new storage will prioritize using the default configuration. All parameters can have default values.

For example, if you set the `username` and `password` for PikPak, you won't need to input them when creating new storage, only the `mount path` and `share ID`.

![Default Configuration](https://img.155155155.xyz/2023/12/1703837264493.png)

</details>

</details>

<details>
<summary><b> Image Hosting</b></summary>

![Image Hosting](https://img.155155155.xyz/2023/12/1703837391936.png)
![Image Hosting](https://img.155155155.xyz/2023/12/1703837424640.png)


</details>

<details>
<summary><b> Cloudflare Node Management</b></summary>

**Node Status Monitoring**: Checks node status every 60 seconds. If a node goes `offline` or `fails`, a notification will be sent.  
**Daily Traffic Statistics**: Sends daily traffic usage statistics at a scheduled time.  
**Automatic Storage Management**: Automatically disables storage when a node goes offline and re-enables it when the node recovers.  
**Automatic Node Switching**: Automatically switches to other available nodes when a node goes offline. Restores the original node at 8 AM daily.  
**Node Load Balancing (Recommended)**: Redirects users to available download nodes automatically during downloads.

If both `Automatic Storage Management` and `Automatic Node Switching` are enabled, the system will prioritize switching nodes when a node fails. If all nodes are unavailable, storage will be disabled.

Note: Adding a Cloudflare account defaults to using the first domain's first Workers route.

<details>
<summary><b> Manually Add Account</b></summary>

Open the `cloudflare_cfg.yaml` configuration file and add the account to the `node` list in the following format:

``` yaml
node:
- account_id: 
  email: 
  global_api_key: 
  url: 
  zone_id: 
- account_id: 
  email: 
  global_api_key: 
  url: 
  zone_id: 
```

**account_id**: `CF Homepage` --> `Domain` --> `Bottom Right` --> `Account ID`  
**zone_id**: `CF Homepage` --> `Domain` --> `Bottom Right` --> `Zone ID`

**email**: Email of the CF account  
**global_api_key**: `CF Homepage` --> `Top Right Avatar` --> `My Profile` --> `API Tokens` --> `Global API Key`  
**url**: Fill in the domain used for proxying in the Workers route. Only fill in the domain, do not add https or /*, e.g., a.ziling.cf.

</details>

![Cloudflare Node Management](https://img.155155155.xyz/2023/12/1703837685120.png)

![Cloudflare Node Management](https://img.155155155.xyz/2023/12/1703837748426.png)

</details>

<details>
<summary><b> Random Recommendation</b></summary>

This feature randomly sends a resource and supports custom paths and keywords.

**Supported Commands**  
**/sr**  
Random recommendation settings menu  
**/roll**  
Use the /roll command to randomly select a resource from all paths and send it.  
**/roll keyword**  
Use the /roll command followed by a keyword to randomly select a resource from the corresponding path and send it.

You can customize paths and keywords to send different resources based on your needs. Each keyword can correspond to multiple paths, as shown below:

``` yaml
path:
  keyword: path # Add a slash before the path
  act: /,【ACT-Action Games】
  adv: /,【ADV-Adventure Games】
  rpg: /,【RPG-Role Playing Games】
  slg: /,【SLG-Strategy Games】
  gd:
    - /%60【Archive】/【KRKR Collection】/1
    - /%60【Archive】/【KRKR Collection】/2
    - /%60【Archive】/【ONS Collection】
```

![Random Recommendation](https://img.155155155.xyz/2023/12/1703837814405.png)


</details>

</details>

---

## Installation

### 1. Docker Installation

**1. Create a bot configuration file directory**

```shell
mkdir -p /root/alist-bot
```

**2. Write `config.yaml` and place it in the path you created `/root/alist-bot`**

```yaml
alist:
  alist_host: http://127.0.0.1:5244 # alist ip:port or alist domain, usually just fill in the domain
  alist_web: http://127.0.0.1:5244 # your alist domain
  alist_token: "" # alist token
user:
  admin:  # Administrator user ID, can be obtained via https://t.me/getletbot
  member: [ ]  # Users, groups, and channels allowed to use the bot (group and channel IDs need to add -100). Can be obtained via https://t.me/getletbot. Leave blank to allow everyone to use.
  bot_token:  # Bot API token, obtained from @BotFather
  api_id:  # api_id and api_hash can be obtained from https://my.telegram.org/apps
  api_hash:
proxy:
  scheme: http
  hostname: 127.0.0.1
  port: 7890
backup_time: '0'
```

**3. Pull the image and run**

```shell
docker run -d \
  --name alist-bot \
  --restart=always \
  -v /root/alist-bot/config.yaml:/usr/src/app/config.yaml \
  -p 3214:3214 \
  ghcr.io/akashicoin/alist-bot:main
```

### 2. Normal Installation

**1. Install python3-pip**

```
apt install python3-pip
```

**2. Clone the project locally**

``` 
git clone https://github.com/AkashiCoin/Alist-bot.git && cd Alist-bot && pip3 install -r requirements.txt
```

**3. Modify the configuration information in config.yaml**

```yaml
alist:
  alist_host: http://127.0.0.1:5244 # alist ip:port or alist domain, usually just fill in the domain
  alist_web: http://127.0.0.1:5244 # your alist domain
  alist_token: "" # alist token
user:
  admin:  # Administrator user ID, can be obtained via https://t.me/getletbot
  member: [ ]  # Users, groups, and channels allowed to use the bot (group and channel IDs need to add -100). Can be obtained via https://t.me/getletbot. Leave blank to allow everyone to use.
  bot_token:  # Bot API token, obtained from @BotFather
  api_id:  # api_id and api_hash can be obtained from https://my.telegram.org/apps
  api_hash:
proxy:
  scheme: http
  hostname: 127.0.0.1
  port: 7890
backup_time: '0'
```

**4. Start the bot**

**Start the bot in the foreground**

``` 
python3 bot.py
```

**Set up auto-start on boot**

The following is a single command. Copy it all at once into the SSH client to run.

``` 
cat > /etc/systemd/system/alist-bot.service <<EOF
[Unit]
Description=Alist-bot Service
After=network.target

[Service]
User=root
WorkingDirectory=/root/Alist-bot
ExecStart=/usr/bin/python3 bot.py > /dev/null 2>&1 &
Restart=always

[Install]
WantedBy=multi-user.target

EOF
```

Then, execute `systemctl daemon-reload` to reload the configuration. Now you can use these commands to manage the program:

Start: `systemctl start alist-bot`  
Stop: `systemctl stop alist-bot`    
Enable auto-start on boot: `systemctl enable alist-bot`  
Disable auto-start on boot: `systemctl disable alist-bot`  
Restart: `systemctl restart alist-bot`  
Status: `systemctl status alist-bot`

## Getting Started

Send commands in private chat or group chat.  
For first-time use, send `/menu` to automatically set up the bot menu.

**Command List:**

```
/start Start
/s + filename Search
/roll Random recommendation
/vb View download node information

Admin Commands:
/sl - Set search result quantity
/zl - Enable/Disable direct link
/st - Storage management 
/sf - Cloudflare node management
/cf - View current configuration
/bc - Backup Alist configuration
/sbt - Set scheduled backup
/sr - Random recommendation settings
/od - Offline download
/dt - Set search result auto-delete timer
/help - View help
```



