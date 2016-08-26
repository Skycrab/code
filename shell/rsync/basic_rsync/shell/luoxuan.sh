#!/bin/bash

export LANG="en_US.UTF-8"

day=`date +'%Y-%m-%d'`
hour=`date +'%H%M'`


work_home=/data/bi/basic_rsync
# rsync配置
rsync_dst=long@bi.lxjjx.com
rsync_password=${work_home}/rsyncd.secrets
rsync_log=${work_home}/log/${day}_rsync.log
# rsync失败日志
rsync_status_log=${work_home}/log/${day}_status.log
# rsync失败时文件目录
rsync_field_list=${work_home}/log/${day}_file.list

# 全服零时目录
data_home=${work_home}/data
upload=${work_home}/upload/${day}/${hour}
list=${work_home}/shell/list/${day}
backup=${work_home}/backup/${day}

mkdir -p ${upload} ${backup} ${list}
list_file=${list}/${hour}.list
ls ${data_home}/*.log > ${list_file}
for i in `cat ${list_file}`
do
    mv $i ${upload}
done

echo "now: $day:$hour, file list:${list_file}" >> ${rsync_status_log}

/usr/bin/rsync -avzP --password-file=${rsync_password} ${upload}/ $rsync_dst::luoxuanjingjiexian >> $rsync_log 2>&1
if [[ $? -eq 0  ]]
then
    echo -e "rsync success\n" >> ${rsync_status_log}
else
    echo -e "rsync failed\n" >> ${rsync_status_log}
    echo "#${list_file}" >> ${rsync_field_list}
    cat ${list_file} >> ${rsync_field_list}
fi

mv ${upload}/* ${backup}
#for i in `cat ${list_file}`
#do
#    mv ${upload}/$i ${backup}
#done
