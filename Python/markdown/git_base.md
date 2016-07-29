# git 基本操作

以一次新功能的开发涉及到的 git 操作为例：

1. 更新本地 develop 分支
    - 查看分支

        ```
        git branch      # 查看本地分支
        git branch -a   # 查看远程分支
        ```
    - 切换到本地 develop 分支

        ```
        git checkout develop
        ```
    - 更新本地 develop 分支代码，使之与线上最新代码一致

        ```
        git pull origin develop
        ```

2. 在 develop 分支上新建一个本地工作分支，比如 workspace（在实际工作中分支的名字以能够通过它看出将要开发的功能为佳）
    - 新建本地工作分支，并切换到该分支

        ```
        git checkout -b workspace

        # 或者使用下述两条命令，两者效果相同
        git branch workspace    # 新建 workspace 分支
        git checkout workspace  # 切换到 workspace 分支
        ```
    - 编写代码中...
    - 查看当前工作分支状态，可查看文件修改状态

        ```
        git status
        ```
    - 更新某一个文件至线上版本

        ```
        git checkout file   # 常用于撤销 file 文件的本地修改
        ```
    - 查看文件修改细节

        ```
        git diff
        ```

3. 开发完成，提交
    - 查看本地版本的所有变动

        ```
        git status
        ```
    - 添加修改的文件

        ```
        git add file    # 同时添加当前目录下的所有改动的文件，可使用 git add . （"." 代表当前目录）
        ```
    - 查看状态，检查是否需要修改的文件均已添加

        ```
        git status
        ```
    - 提交，书写日志

        ```
        git commit -m "commit log"
        ```
    - 查看提交日志

        ```
        git log
        ```
    - 推送版本到线上

        ```
        git push origin workspace
        ```
