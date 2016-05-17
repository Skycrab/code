#!/bin/bash

BASE_DIR="/root"
BIWEB_DIR="/data/biweb"
GULP_DIR="/root/nodegulp"
ADMIN_MEDIA="/root/media"
PROJECT_NAME="python"
RESTART_SCRIPT_NAME="restart.sh"
TEST_SCRIPT_NAME="test.sh"
PROJECT_ADDR="git@*****:bi/python.git"
GULP_SRC="src"
GULP_DIST="dist"
GULP_SRC_DATAEYE="$GULP_DIR/$GULP_SRC/dataeye"
GULP_DIST_DATAEYE="$GULP_DIR/$GULP_DIST/dataeye"
GULP_CLEAN_DATAEYE="$GULP_DIR/clean/dataeye"
PROJECT_DATAEYE="$BASE_DIR/$PROJECT_NAME/dataeye"

LIVE_PRODUCTION_DIR_NAME="live_production"
LIVE_PRODUCTION="$BIWEB_DIR/$LIVE_PRODUCTION_DIR_NAME"
LIVE_NGINX_CONF="/etc/nginx/conf.d/live_production.conf"
LIVE_NGINX_SERVER_NAME="www.longtubas.com longtubas.com localhost"
LIVE_SERVER_PORT=80
LIVE_FASTCGI_PORT=(3033 3034 3035)
LIVE_BIWEB="live_biweb"
LIVE_OUT_LOG="/var/log/bi_out.log"
LIVE_ERR_LOG="/var/log/bi_err.log"

TEST_PRODUCTION_DIR_NAME="test_production"
TEST_PRODUCTION="$BIWEB_DIR/$TEST_PRODUCTION_DIR_NAME"
TEST_NGINX_CONF="/etc/nginx/conf.d/test_production.conf"
TEST_NGINX_SERVER_NAME="test.longtubas.com"
TEST_SERVER_PORT=80
TEST_FASTCGI_PORT=(6000)
TEST_BIWEB="test_biweb"
TEST_OUT_LOG="/var/log/bi_out_test.log"
TEST_ERR_LOG="/var/log/bi_err_test.log"

DEBUG_PRODUCTION_DIR_NAME="debug_production"
DEBUG_PRODUCTION="$BIWEB_DIR/$DEBUG_PRODUCTION_DIR_NAME"
DEBUG_NGINX_CONF="/etc/nginx/conf.d/debug_production.conf"
DEBUG_NGINX_SERVER_NAME="debug.longtubas.com"
DEBUG_SERVER_PORT=80
DEBUG_FASTCGI_PORT=(7000)
DEBUG_BIWEB="debug_biweb"
DEBUG_OUT_LOG="/var/log/bi_out_debug.log"
DEBUG_ERR_LOG="/var/log/bi_err_debug.log"


# 检查是否是 root 权限运行此脚本
if [ $UID -ne 0 ]; then
    echo "运行此脚本需要管理员权限！"
    echo "示例："
    echo "sudo $0"
    exit -1
fi


function usage() {
cat << EOF

Usage: $0 live|test|debug [gitbranch]
    live|test|debug     live 对应 www.longtubas.com ；test 对应 test.longtubas.com ；debug 对应 debug.longtubas.com
    gitbranch           参数可选，git 分支，默认为 master

Example: $0 test develop

EOF
    exit 0
}

# 获取参数
current="TEST"
gitbranch="master"
if [ $# -lt 1 -o $# -gt 2 ]; then
    echo "参数个数错误！"
    usage
else
    if [ "$1" = "live" ]; then
        current="LIVE"
    elif [ "$1" = "test" ]; then
        current="TEST"
    elif [ "$1" = "debug" ]; then
        current="DEBUG"
    else
        echo "参数错误！"
        usage
    fi
    if [ $# -eq 2 ]; then
        gitbranch="$2"
    fi
fi

CURRENT=$current
eval DEPLOY_PRODUCTION=\$${CURRENT}_PRODUCTION
eval DEPLOY_NGINX_CONF=\$${CURRENT}_NGINX_CONF
eval DEPLOY_NGINX_SERVER_NAME=\$${CURRENT}_NGINX_SERVER_NAME
eval DEPLOY_SERVER_PORT=\$${CURRENT}_SERVER_PORT
eval DEPLOY_FASTCGI_PORT=(\${${CURRENT}_FASTCGI_PORT[@]})
eval DEPLOY_BIWEB=\$${CURRENT}_BIWEB
eval DEPLOY_OUT_LOG=\$${CURRENT}_OUT_LOG
eval DEPLOY_ERR_LOG=\$${CURRENT}_ERR_LOG
DEPLOY_UNIQUE_NGINX_SERVER_NAME=`echo $DEPLOY_NGINX_SERVER_NAME|awk '{print $1}'`


# 更新代码
cd $BASE_DIR
if [ -d $PROJECT_NAME ]; then
    cd $PROJECT_NAME
    git checkout -q master
    git pull
    git reset --hard origin/master
else
    git clone $PROJECT_ADDR $PROJECT_NAME
fi
if [ "$gitbranch" != "master" ]; then
    git branch -D $gitbranch 2>/dev/null
    git checkout -q -b $gitbranch origin/$gitbranch
    [ $? -ne 0 ] && exit -2
fi


# 压缩 css 和 js 文件
rm -rf $GULP_DIR/$GULP_SRC/*
mkdir $GULP_SRC_DATAEYE
cp -r $PROJECT_DATAEYE/static $GULP_SRC_DATAEYE
cp -r $PROJECT_DATAEYE/templates $GULP_SRC_DATAEYE
cd $GULP_DIR
if [ "$CURRENT" = "DEBUG" ]; then
    gulp debug
else
    gulp
fi

cp -r $GULP_DIST_DATAEYE/*  $GULP_SRC_DATAEYE


# 更换运行代码
[ ! -d $DEPLOY_PRODUCTION ] && mkdir $DEPLOY_PRODUCTION
for f in $PROJECT_DATAEYE/*
do
    if [ $f != "$PROJECT_DATAEYE/static" ]; then
        cp -r $f $DEPLOY_PRODUCTION
    fi
done
cp -r $ADMIN_MEDIA/* $DEPLOY_PRODUCTION/media/

# 静态资源版本比对
STATIC_OUT=$BASE_DIR/out
[ -d $STATIC_OUT ] && rm -r $STATIC_OUT
python $BASE_DIR/asset.py $GULP_SRC_DATAEYE/static $GULP_SRC_DATAEYE/templates $DEPLOY_PRODUCTION/static  $STATIC_OUT
cp -r $STATIC_OUT/static/ $DEPLOY_PRODUCTION
cp -r $STATIC_OUT/templates/ $DEPLOY_PRODUCTION

if [ "$CURRENT" = "DEBUG" ]; then
    sed -i 's/^DEBUG = False/DEBUG = True/' $DEPLOY_PRODUCTION/settings/pro_settings.py
    sed -i 's/^TEMPLATE_DEBUG = False/TEMPLATE_DEBUG = True/' $DEPLOY_PRODUCTION/settings/pro_settings.py
    chown haibo.haibo $DEPLOY_PRODUCTION
    chmod 777 -R $DEPLOY_PRODUCTION
fi


declare -a biweb
for i in "${!DEPLOY_FASTCGI_PORT[@]}"; do
# for((i=0; i<${#DEPLOY_FASTCGI_PORT[@]}; i++)); do
    biweb[$i]="server 127.0.0.1:"${DEPLOY_FASTCGI_PORT[$i]}";"
done
echo ${biweb[@]}


# 创建 nginx 配置文件
cat > $DEPLOY_NGINX_CONF << EOF
upstream $DEPLOY_BIWEB{
    ${biweb[@]}
}

server {
    listen $DEPLOY_SERVER_PORT;
    server_name $DEPLOY_NGINX_SERVER_NAME;
    gzip on;
    gzip_min_length 1k;
    gzip_buffers 4 16k;
    gzip_comp_level 6;
    gzip_types text/plain application/x-javascript text/css application/xml text/javascript application/x-httpd-php image/jpeg image/gif image/png;

    location / {
        # 指定 fastcgi 的主机和端口
        fastcgi_pass $DEPLOY_BIWEB;
        fastcgi_param PATH_INFO \$fastcgi_script_name;
        fastcgi_param REQUEST_METHOD \$request_method;
        fastcgi_param QUERY_STRING \$query_string;
        fastcgi_param CONTENT_TYPE \$content_type;
        fastcgi_param CONTENT_LENGTH \$content_length;
        fastcgi_param SERVER_PROTOCOL \$server_protocol;
        fastcgi_param SERVER_PORT \$server_port;
        fastcgi_param SERVER_NAME \$server_name;
        fastcgi_pass_header Authorization;
        fastcgi_intercept_errors off;
    }

    location /static/admin/{
        alias $DEPLOY_PRODUCTION/media/;
    }

    location /static/oss/{
        alias $DEPLOY_PRODUCTION/static/oss/;
        if (\$request_uri ~ .*\.(js|css)$ ) {
            expires 30d;
        }
    }

    location /static/{
        alias $DEPLOY_PRODUCTION/static/;
        if (\$request_uri ~ .*\.(js|css)$ ) {
            expires 30d;
        }
    }

    location /upload/ {
        alias $DEPLOY_PRODUCTION/upload/;
    }

    location /inter_email/data/ {
        internal;
        alias $BIWEB_DIR/email_data/;
    }

    location /download/ {
        internal;
        alias $BIWEB_DIR/download/;
    }

    location ~*\.html$ {
        root $DEPLOY_PRODUCTION/templates/;
    }
}
EOF


# 创建 restart.sh 脚本
cat > $DEPLOY_PRODUCTION/$RESTART_SCRIPT_NAME << EOF
#!/bin/bash

DEPLOY_FASTCGI_PORT=(${DEPLOY_FASTCGI_PORT[@]})

# 检查是否是 root 权限运行此脚本
if [ \$UID -ne 0 ]; then
    echo "运行此脚本需要管理员权限！"
    echo "示例："
    echo "sudo \$0"
    exit -1
fi

for port in "\${DEPLOY_FASTCGI_PORT[@]}"; do
    ps -ef | grep \$port | grep -v grep | awk -F ' ' '{print \$2}' | xargs kill -9
done

# 合并日志
NOW="\`date +'%Y-%m-%d_%H:%M:%S'\`"
LOG_DIR="${BIWEB_DIR}/logs/${CURRENT}"
mkdir -p \${LOG_DIR} \${LOG_DIR}/back
ls \${LOG_DIR}/bi_*.log  > /dev/null 2>&1
if [ \$? == 0 ];then
    c="\`cat \${LOG_DIR}/bi_*.log\`"
    if [ "\$c" != "" ];then
        cat \${LOG_DIR}/bi_*.log >> \${LOG_DIR}/back/\${NOW}.log
    fi
    rm -rf \${LOG_DIR}/bi_*.log
fi

#环境变量设置
export stage=$CURRENT
export host=$DEPLOY_UNIQUE_NGINX_SERVER_NAME
export port=$DEPLOY_SERVER_PORT

if [ "\$1" = "-f" ]; then
    python manage.py runfcgi daemonize=false host=127.0.0.1 port=\$DEPLOY_FASTCGI_PORT --settings="settings.pro_settings"
else
    for port in "\${DEPLOY_FASTCGI_PORT[@]}"; do
        python manage.py runfcgi host=127.0.0.1 port=\$port outlog=$DEPLOY_OUT_LOG errlog=$DEPLOY_ERR_LOG --settings="settings.pro_settings"
    done
fi
EOF
chmod +x $DEPLOY_PRODUCTION/$RESTART_SCRIPT_NAME

# 创建 test.sh 脚本
cat > $DEPLOY_PRODUCTION/$TEST_SCRIPT_NAME << EOF
export stage=$CURRENT
export host=$DEPLOY_UNIQUE_NGINX_SERVER_NAME
export port=$DEPLOY_SERVER_PORT

python manage.py ft --settings="settings.pro_settings"
EOF
chmod +x $DEPLOY_PRODUCTION/$TEST_SCRIPT_NAME

# 重启服务
cd $DEPLOY_PRODUCTION
./$RESTART_SCRIPT_NAME
/etc/init.d/nginx restart

# 删除之前静态文件
for f in `cat $STATIC_OUT/discard.txt`
do
    echo $f
    rm -r $DEPLOY_PRODUCTION/static/$f
done
