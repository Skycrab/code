2.1 Hive常用设置
2.1.1 Hive设置队列
1. 在Hive客户端或者beeline中设置：set mapreduce.job.queuename={队列名称};
2. 在环境变量中统一设置：新建用户工作目录下的.hiverc（ $HOME/.hiverc ）文件，在其中设置一些默认参数，例如 set hiveconf:mapred.job.queue.name= 队列名称;
2.1.2 Hive设置内存
默认mapper，reducer 任务内存设置都是1GB，默认的Hive客户端内存设置是512MB。在某些极端情况下可能不够用，需要用户自定义设置更加合适的内存。
以设置内存为4096MB为例，
1. 设置Mapper内存：set mapreduce.map.memory.mb=4096; set mapreduce.map.java.opts=-Xmx3276m;（设置为第一个参数的0.75倍）
2. 设置Reducer内存：set mapreduce.reduce.memory.mb=4096; set mapreduce.reduce.java.opts=-Xmx3276m;（设置为第一个参数的0.75倍）
3. 设置Hive客户端使用内存：export HADOOP_HEAPSIZE=2048; export HADOOP_CLIENT_OPTS=" -Xmx2048m $HADOOP_CLIENT_OPTS";（执行hive命令之前执行这两句）
2.1.3 Hive客户端设置控制台打印详细执行日志
# 设置控制台显示日志级别为INFO；如果需要显示更详细的日志，可以设置为DEBUG
hive -hiveconf hive.root.logger=INFO,console
2.1.4 Hive设置合并小文件
Hive设置合并小文件相关选项
# 在Map-Reduce的任务结束时，启动一个Map-only任务合并小文件默认为false
set hive.merge.mapredfiles=true;
# 单个task处理的最大数据量是240M
set mapred.max.split.size=240000000;
set mapred.min.split.size.per.node=240000000;
set mapred.min.split.size.per.rack=240000000;
目前默认开启。
更多配置选择，请参考官方介绍 。
