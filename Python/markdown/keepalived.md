#keepalived主从模式配置

1. 基础知识

   keepalived是主从模式，通过VIP(虚拟ip)漂移来绑定VIP, VIP通过keepalived.conf配置
   状态为Master的机器绑定VIP, 可通过ip addr查看,当Master主机或keepalived进程挂掉, 以及优先级比Backup低,
   此时Backup绑定VIP, 进入Master状态。 当原Master重启后由于优先级高会再次变成Master。

   Keepalived当前状态可通过/var/log/messages查看

   Keepalived根据优先级(priority+weight)确定Master, Backup


2. 环境搭建

    - 安装keepalived

        ```
        yum install keepalived
        ```
    - iptables增加组播放行

        ```
        vi /etc/sysconfig/iptables
        # 增加
        -A INPUT -d 224.0.0.18 -j ACCEPT
        # 重启iptables
        /etc/init.d/iptables restart
        ```

    - 修改keepalived.conf

        Master /etc/keepalived/keepalived.conf

        ```
        ! Configuration File for keepalived

        global_defs {
           router_id nginx_master
        }

        vrrp_script chk_webserver {
            script "/data/biweb/check.sh"
            interval 5
            weight 3
        }

        vrrp_instance VI_1 {
            state  MASTER
            interface eth0
            virtual_router_id 51
            priority 101
            advert_int 1
            authentication {
                auth_type PASS
                auth_pass 1111
            }
            virtual_ipaddress {
                106.3.130.94/27
            }

            track_script {
               chk_webserver
            }
        }

        ```

        Backup /etc/keepalived/keepalived.conf

        ```
        ! Configuration File for keepalived

        global_defs {
           router_id nginx_backup
        }

        vrrp_script chk_webserver {
            script "/data/biweb/check.sh"
            interval 5
            weight 3
        }

        vrrp_instance VI_1 {
            state BACKUP
            interface eth0
            virtual_router_id 51
            priority 99
            advert_int 1
            authentication {
                auth_type PASS
                auth_pass 1111
            }
            virtual_ipaddress {
                106.3.130.94/27
            }
            track_script {
               chk_webserver
            }
        }
        ```

    - 增加检查脚本，根据状态码检测

        ```
        #!/bin/bash

        log="/data/biweb/check.log"
        count=0
        for (( k=0; k<2; k++ ))
        do
            check_code=$( curl --connect-timeout 3 -sL -w "%{http_code}\\n" http://localhost/check.xhtml -o /dev/null )
            if [ "$check_code" != "200" ]; then
                count=$(($count+1))
                continue
            else
                count=0
                break
            fi
        done
        if [ "$count" != "0" ]; then
            echo `date` >> $log
            echo "stop keepalived" >> $log
           /etc/init.d/keepalived stop
            exit 1
        else
            exit 0
        fi
        ```

    - 开机自启

        ```
        vi /etc/rc.local
        /etc/init.d/keepalived start
        ```


