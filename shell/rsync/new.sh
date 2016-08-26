#!/bin/bash

export LANG="en_US.UTF-8"

if [ $# != 1 ]; then
    echo "please input clientid"
    exit 1
fi

work_home=/data/bi
sclientid=${1}  # 01
#clientid=`printf "%05d" ${sclientid}`       #00001
#easy_clientid=`printf "%d" ${sclientid}`    # 1
clientid=`printf "%05d" "${sclientid#0}"`
easy_clientid="${sclientid#0}"
clientid_home=/data/bi/clientids/${clientid}
clientid_shell=${clientid_home}/shell
clientid_log=${clientid_home}/log
clientid_secure_log=${clientid_home}/log/secure
data_dir=${work_home}/basic_rsync/data
time=`date +%s`

if [ -d ${clientid_home} ];then
    echo "ERROR, client: ${sclientid} exist, quit"
    exit 1
fi

config_ini=${clientid_shell}/config.ini
secure_luo=${clientid_shell}/secure_luo.sh
mkdir -p ${clientid_shell} ${clientid_log} ${clientid_secure_log}
ln -s ${work_home}/shell/luo.py ${clientid_shell}/luo.py

user="long"
password="Long_Connect"

config_tpl=`cat <<!
[game]
host = rr-mysql.rds.aliyuncs.com
user = ${user}
password = ${password}
db_default = helix_login_ios
db_login = helix_login_ios

[server]
host =
user = ${user}
password = ${password}
db_default = helix_game_ios${sclientid}
db_game = helix_game_ios${sclientid}
db_log = helix_log_ios${sclientid}
gameid = 1
clientid = ${easy_clientid}
default_snid = 1002
log = ${clientid_log}/bi_${clientid}.log
data_dir = ${data_dir}
login_start = ${time}
register_start = ${time}
consume_start = ${time}
currency = CNY
payment_start = ${time}
mission_start = ${time}
gold_start = ${time}
other_start = ${time}
props_start = ${time}
!`

echo "${config_tpl}" > ${config_ini}

cat > $secure_luo << EOF
#!/bin/bash

work_home=${work_home}
echo \`date\`

count=\`ps -ef |grep ${clientid_shell}/luo.py |grep -v "grep" |wc -l\`
if [ 0 == \$count ];then
    echo "start"
    /usr/bin/python ${clientid_shell}/luo.py b >> ${clientid_log}/cron_${clientid}.log 2>&1
    echo -n "end "
    echo \`date\`
else
    echo "process already exist"
fi

echo '-------------------------------'
EOF

#cp ${work_home}/shell/config.ini ${config_ini}
#sed -i "s/^clientid.*$/clientid = ${sclientid}/" ${config.ini}
#sed -i "s;^log .*$;log = ${clientid_log}/bi_${clientid}.log;" ${config.ini}
#sed -i "s/^login_start.*$/login_start = ${time}/" ${config.ini}
#sed -i "s/^register_start.*$/register_start = ${time}/" ${config.ini}
#sed -i "s/^consume_start.*$/consume_start = ${time}/" ${config.ini}
#sed -i "s/^payment_start.*$/payment_start = ${time}/" ${config.ini}
#sed -i "s/^mission_start.*$/mission_start = ${time}/" ${config.ini}

# echo "#*/5 * * * * /usr/bin/python ${clientid_shell}/luo.py b >> ${clientid_log}/cron_${clientid}.log 2>&1"  >> /var/spool/cron/root
echo "#*/5 * * * * /bin/bash ${secure_luo} >> ${clientid_secure_log}/cron_${clientid}.log 2>&1"  >> /var/spool/cron/root
