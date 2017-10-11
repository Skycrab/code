##1.善用explain

##2.少用distinct,拆为group by,减少数据倾斜

##3.map端join优化
```
set hive.auto.convert.join=true;
set hive.mapjoin.smalltable.filesize=1000000;
```
验证是否是map join,可通过log查看
```
Execution log at: /data/hadoop/hadoop_temp/hadoop/fbi_20171011172459_84b398d1-f84a-4776-9c49-5c3e454a6568.log
2017-10-11 17:48:47 Starting to launch local task to process map join;  maximum memory = 2058354688
2017-10-11 17:48:48 Dump the side-table for tag: 1 with group count: 39 into file: file:/data/hive/hadoop/scratchdir/174ae53e-e18a-4142-87cd-4733a5001916/hive_2017-10-11_17-24-59_590_1710250291738622328-1/-local-10011/HashTable-Stage-26/MapJoin-mapfile01--.hashtable
2017-10-11 17:48:48 Uploaded 1 File to: file:/data/hive/hadoop/scratchdir/174ae53e-e18a-4142-87cd-4733a5001916/hive_2017-10-11_17-24-59_590_1710250291738622328-1/-local-10011/HashTable-Stage-26/MapJoin-mapfile01--.hashtable (2767 bytes)
2017-10-11 17:48:48 End of local task; Time Taken: 1.474 sec.
Execution completed successfully
MapredLocal task succeeded
```

##4.开启并行,任务相互依赖要少,可通过union优化
```
set hive.exec.parallel=true;
```
explain stage最好不要向下面这样:

TAGE DEPENDENCIES:
Stage-1 is a root stage
Stage-2 depends on stages: Stage-1
Stage-3 depends on stages: Stage-2
Stage-4 depends on stages: Stage-3
Stage-5 depends on stages: Stage-4
Stage-6 depends on stages: Stage-5
Stage-7 depends on stages: Stage-6
Stage-8 depends on stages: Stage-7
Stage-9 depends on stages: Stage-8
Stage-0 depends on stages: Stage-9



