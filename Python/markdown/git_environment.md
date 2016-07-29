# git 环境配置

windows 和 linux 环境均使用命令行方式进行 git 操作。

1. 安装 git
    - windows 中使用 [Git for Windows](https://git-for-windows.github.io/)

2. 生成 ssh key

    可参照 [gitlab](http://42.62.6.139:9000/help/ssh/README) 上的介绍
    - 使用 ssh-keygen 命令生成 ssh key

    ```
    # linux
    ssh-keygen -t rsa -C "shengan@longtugame.com"

    # windows （需先在开始菜单中选择并进入 git bash）
    ssh-keygen.exe -t rsa -C "shengan@longtugame.com"
    ```
    - 拷贝 ssh key

    ```
    cat ~/.ssh/id_rsa.pub
    ```
    - 添加 ssh key 到 gitlab 上

        进入 [http://42.62.6.139:9000/profile/keys](http://42.62.6.139:9000/profile/keys) 页面。点击添加 ssh key，取个名字然后将上述拷贝的 ssh key 粘贴进去。

3. 用户配置

    ```
    git config --global user.name "shengan"
    git config --global user.email "shengan@longtugame.com"
    ```

至此，git 初次运行前的环境配置已经完成，接下来就可以从线上 clone 一份代码进行操作了。

```
git clone git@42.62.6.139:bi/python.git     # 从线上 clone 一份代码
```
