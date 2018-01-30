# Simple_resa_YARN_App

This is a modified version of the original project: https://github.com/gpiskas/Simple_YARN_App_Skeleton

1. Download the project
2. Mvn clean package
3. Change the generated .jar file to YARNAPP.jar 
4. Copy YARNAPP.jar to HDFS 
```
# Puts the jar in HDFS under /apps/
hadoop fs -rm -r -f /apps
hadoop fs -mkdir -p /apps
hadoop fs -copyFromLocal YARNAPP.jar /apps/YARNAPP.jar
```

5. launch 
```
# Executes the Client.
hadoop jar YARNAPP.jar com.resa.yarn.Client
```
