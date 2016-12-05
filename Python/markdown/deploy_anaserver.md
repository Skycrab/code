# 分析服务器部署

1. 安装基本软件包

    ```
    yum install gcc
    yum install mysql
    yum install mysql-devel
    yum install libffi libffi-devel
    ```

2. 部署python开发环境
    - 部署

        ```
        # root用户登陆
        cd /root
        scp root@192.168.3.42:/root/Anaconda-2.3.0-Linux-x86_64.sh .
        chmod +x Anaconda-2.3.0-Linux-x86_64.sh
        # 遇到选项选yes
        ./Anaconda-2.3.0-Linux-x86_64.sh
        ```
    - 验证是否安装正确

        ```
        python --version
        Python 2.7.10 :: Anaconda 2.3.0 (64-bit)

        # 如果没有加入到环境变量

        vi /root/.bashrc
        export PATH="/root/anaconda/bin:$PATH"

        source /root/.bashrc
        ```

3. 选用最后一块磁盘(如/data4)
    - 拷贝基础代码

        ```
        cd /data4
        mkdir -p bi/shell bi/games
        scp -r root@192.168.3.42:/root/python/analysis bi/shell/
        cd /bi/shell/analysis
        cp script/* ./
        ```
    - 安装python软件包

        ```
        # 使用douban源
        pip install -i https://pypi.douban.com/simple/ -r bi/shell/analysis/requirements.txt
        #pip install -r bi/shell/analysis/requirements.txt
        ```

4. 用户, 权限
   - 创建用户,密码随意

        ```
        useradd haibo
        passwd haibo
        ```
   - 配置sudo权限

       ```
       vi /etc/sudoers
       haibo   ALL=(ALL)       NOPASSWD: ALL
       ```
   - 配置ssh秘钥

       ```
       su haibo
       cd /home/haibo

       # 不存在创建
       mkdir .ssh
       chmod 700 .ssh

       # 不存在创建
       touch .ssh/authorized_keys
       chmod 600 .ssh/authorized_keys

       # 拷贝秘钥
       scp root@192.168.3.42:/root/.ssh/id_rsa.pub /tmp/id_rsa.pub
       cat /tmp/id_rsa.pub >> .ssh/authorized_keys
       ```

5. web配置
    - manage_device 表增加一台机器(classification为1)
    - web配置全局属性脚本目录(/data4/bi/shell)
    - 增加一个游戏项目





