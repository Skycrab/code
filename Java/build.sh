#!/usr/bin/env bash
export JAVA_HOME=/usr/local/jdk1.8.0_65
export PATH=$JAVA_HOME/bin:$PATH

mvn clean package -Dmaven.test.skip=true -Ponline

ret=$?
if [ $ret -ne 0 ];then
    echo "===== maven build failure ====="
    exit $ret
else
    echo "===== maven build successfully! ====="
fi


rm -rf output
mkdir output

cp target/*.jar output/
cp control.sh output/

