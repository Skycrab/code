# spark集群使用定制Python环境


## 1.制作基础Python环境
```
下载 wget https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tgz
tar -zxvf Python-2.7.9.tgz
cd Python-2.7.9
指定打包路径
./configure --prefix=/tmp/python-2.7.9
make && make install
```
## 2.安装第三方包
```
/tmp/python-2.7.9/bin/python -m pip install pymongo
```
## 3.校验是否安装成功
```
/tmp/python-2.7.9/bin/python -c "import pymongo"
```
## 4.打包放到hdfs上,并将压缩包放到集群上
```
tar -zcf /tmp/python-2.7.9.tgz *
hadoop fs -put python-2.7.9.tgz /user/xxx/xxx
```
## 5.spark-submit 提交代码
  cluster模式提交
```
指定集群上python包的地址，#后为后续引用这个包所用的名称
spark.yarn.dist.archives hdfs://.../python-2.7.9.tgz#python-2.7.9
spark.yarn.appMasterEnv.PYSPARK_PYTHON=./python-2.7.9/bin/python
```
```
spark-submit  --master yarn --deploy-mode cluster --queue <yarn queue> --conf spark.yarn.dist.archives=hdfs:///user/xxx/xxx/python-2.7.9.tgz#python-2.7.9 --conf spark.pyspark.python=./python-2.7.9/python-2.7.9/bin/python --conf spark.yarn.dist.files=$SPARK_HOME/conf/hive-site.xml --py-files xxxx-dependency.py main.py
```
 client模式提交
```
指定集群上python包的地址，#后为后续引用这个包所用的名称
--conf spark.yarn.dist.archives=hdfs:///user/xxx/xxx/python-2.7.9.tgz#python-2.7.9
设置driver端本地python路径
export PYSPARK_DRIVER_PYTHON=/tmp/python-2.7.9/bin/python
设置executor端python路径，这里的python-2.7.9即为上一条中#后的内容
export PYSPARK_PYTHON=./python-2.7.9/bin/python
```
