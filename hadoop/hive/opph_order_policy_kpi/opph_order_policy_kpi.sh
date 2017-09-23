#!/bin/sh`
if [ $# -eq 1 ];then
   V_DATE=$1
else
  V_DATE=`date +%Y-%m-%d`
fi
 echo $V_DATE
 predate=`date --date "${V_DATE} -1 day" "+%Y/%m/%d"`
 echo $predate
V_PARYEAR=`date --date="$V_DATE-1 day" +%Y`
V_PARMONTH=`date --date="$V_DATE-1 day" +%m`
V_PARDAY=`date --date="$V_DATE-1 day" +%d`
V_YESTERDAY=`date --date="$V_DATE-1 day" +%Y%m%d`
V_YESTERDAY_0=`date --date="$V_DATE-1 day" +%Y-%m-%d`
V_MONTH_FIRST_DAY_0="${V_PARYEAR}-${V_PARMONTH}-01"


hive -e "
use manhattan_dm;
set hive.exec.parallel=true;
set hive.new.job.grouping.set.cardinality=100;

alter table opph_order_policy_kpi add if not exists partition(year='$V_PARYEAR',month='$V_PARMONTH',day='$V_PARDAY') location '$V_PARYEAR/$V_PARMONTH/$V_PARDAY';
insert overwrite table opph_order_policy_kpi partition(year='$V_PARYEAR',month='$V_PARMONTH',day='$V_PARDAY')

select
    '0' as id,
    '${V_YESTERDAY_0}' stat_date, --日期
    channel_id,
    case when channel_id=-10000 then '全部' else channel_name end channel_name,
    inscompany_id,
    case when inscompany_id=-10000 then '全部' else inscompany_name end inscompany_name,
    product_id,
    case when product_id=-10000 then '全部' else product_name end product_name,
    sales_method,
    case when sales_method=-10000 then '全部'
        when sales_method=1 then '赠险'
        when sales_method=2 then '直购'
        when sales_method=3 then '转赠'
        else '未知'
    end sales_method_name,
    -10000 pay_type, --支付类型
    '全部' pay_type_name,
    buy_policy_num, --当日保单数
    buy_user_num, --当日保单人数
    premium_fee, --当日保单保费金额
    insurant_user_num, --当日被投保人数
    total_policy_num, --累计保单数
    total_premium_fee, --累计保单保费金额
    total_user_num, --累计保单人数
    total_insurant_user_num, --累计被投保人数
    0 real_premium_fee, --当日实付保费金额
    0 channel_premium_fee, --当日渠道收入
    0 total_real_premium_fee, --累计实付保费金额
    0 total_channel_premium_fee, --累计渠道收入
    spu_id, --'产品编号'
    case when spu_id='-10000' then '全部'
        else coalesce(spu_name, spu_id)
    end spu_name,
    offer_fee, --当日OFFER收入
    coupon_amount, --当日券使用金额
    month_buy_policy_num, --当月累计保单数
    month_premium_fee --当月累计保费金额
from
(
    select
        channel_id,
        max(channel_name) channel_name,
        inscompany_id,
        max(inscompany_name) inscompany_name,
        product_id,
        max(product_name) product_name,
        sales_method,
        spu_id,
        max(spu_name) spu_name,
        sum(buy_policy_num) buy_policy_num,  --当日保单数
        sum(total_policy_num) total_policy_num,  --累计保单数
        sum(month_buy_policy_num) month_buy_policy_num,  --当月累计保单数
        sum(premium_fee) premium_fee,  --当日保单保费金额
        sum(total_premium_fee) total_premium_fee,  --累计保单保费金额
        sum(month_premium_fee) month_premium_fee,  --当月累计保费金额
        sum(offer_fee) offer_fee,  --当日OFFER收入
        sum(coupon_amount) coupon_amount,  --当日券使用金额
        sum(buy_user_num) buy_user_num,  --当日保单人数
        sum(total_user_num) total_user_num,  --累计保单人数
        sum(insurant_user_num) insurant_user_num,  --当日被投保人数
        sum(total_insurant_user_num) total_insurant_user_num  --累计被投保人数
    from
    (
        --计算保单数

        select
            coalesce(channel_id, -10000) channel_id,
            max(channel_name) channel_name,
            coalesce(inscompany_id, -10000) inscompany_id,
            max(inscompany_name) inscompany_name,
            coalesce(product_id, -10000) product_id,
            max(product_name) product_name,
            coalesce(sales_method, -10000) sales_method,
            coalesce(spu_id, '-10000') spu_id,
            max(spu_name) spu_name,
            sum(case when policy_time like '${V_YESTERDAY_0}%' then 1 else 0 end) buy_policy_num, --当日保单数
            sum(1) total_policy_num, --累计保单数
            sum(case when to_date(policy_time) between '${V_MONTH_FIRST_DAY_0}' and '${V_YESTERDAY_0}' then 1 else 0 end) month_buy_policy_num, --当月累计保单数
            0 premium_fee, --当日保单保费金额
            0 total_premium_fee, --累计保单保费金额
            0 month_premium_fee, --当月累计保费金额
            0 offer_fee, --当日OFFER收入
            0 coupon_amount, --当日券使用金额
            0 buy_user_num, --当日保单人数
            0 total_user_num, --累计保单人数
            0 insurant_user_num, --当日被投保人数
            0 total_insurant_user_num --累计被投保人数
        from
        (
            select
                max(coalesce(channel_id,-1)) channel_id,
                max(coalesce(channel_name, '未知')) channel_name,
                max(coalesce(inscompany_id,-1)) inscompany_id,
                max(coalesce(inscompany_name,'未知')) inscompany_name,
                max(coalesce(product_id, -1)) product_id,
                max(coalesce(product_name, '未知')) product_name,
                max(coalesce(sales_method,-1)) sales_method,
                max(coalesce(spu_id,-1)) spu_id, --spu编码
                max(spu_name) spu_name,
                max(policy_time) policy_time
            from manhattan_dw.dw_v_opph_order_policy_base
            where concat(year,month,day)='${V_YESTERDAY}'
            and policy_status in (3,4,5)
            and policy_time <= '${V_YESTERDAY_0} 23:59:59'
            group by product_order_id
        )t1
        group by channel_id,inscompany_id,product_id,sales_method,spu_id with cube


        --计算保费

        union all

        select
            coalesce(channel_id, -10000) channel_id,
            max(channel_name) channel_name,
            coalesce(inscompany_id, -10000) inscompany_id,
            max(inscompany_name) inscompany_name,
            coalesce(product_id, -10000) product_id,
            max(product_name) product_name,
            coalesce(sales_method, -10000) sales_method,
            coalesce(spu_id, '-10000') spu_id,
            max(spu_name) spu_name,
            0  buy_policy_num, --当日保单数
            0 total_policy_num, --累计保单数
            0 month_buy_policy_num, --当月累计保单数
            sum(case when policy_time like '${V_YESTERDAY_0}%' then premium else 0 end) premium_fee, --当日保单保费金额
            sum(premium) total_premium_fee, --累计保单保费金额
            sum(case when to_date(policy_time) between '${V_MONTH_FIRST_DAY_0}' and '${V_YESTERDAY_0}' then premium else 0 end) month_premium_fee, --当月累计保费金额
            sum(case when policy_time like '${V_YESTERDAY_0}%' then offer_fee else 0 end) offer_fee, --当日OFFER收入
            sum(case when policy_time like '${V_YESTERDAY_0}%' then coupon_amount else 0 end) coupon_amount, --当日券使用金额
            0 buy_user_num, --当日保单人数
            0 total_user_num, --累计保单人数
            0 insurant_user_num, --当日被投保人数
            0 total_insurant_user_num --累计被投保人数
        from
        (
            select
                coalesce(channel_id,-1) channel_id,
                coalesce(channel_name, '未知') channel_name,
                coalesce(inscompany_id,-1) inscompany_id,
                coalesce(inscompany_name,'未知') inscompany_name,
                coalesce(product_id, -1) product_id,
                coalesce(product_name, '未知') product_name,
                coalesce(sales_method,-1) sales_method,
                coalesce(spu_id,-1) spu_id,
                spu_name,
                policy_time,
                premium,
                offer_fee, --offer收入
                coupon_amount --券使用金额
            from manhattan_dw.dw_v_opph_order_policy_base
            where concat(year,month,day)='${V_YESTERDAY}'
            and policy_status in (3,4,5)
            and policy_time <= '${V_YESTERDAY_0} 23:59:59'
        )t1
        group by channel_id,inscompany_id,product_id,sales_method,spu_id with cube

        --计算保单人数

        union all

        select
            coalesce(channel_id, -10000) channel_id,
            max(channel_name) channel_name,
            coalesce(inscompany_id, -10000) inscompany_id,
            max(inscompany_name) inscompany_name,
            coalesce(product_id, -10000) product_id,
            max(product_name) product_name,
            coalesce(sales_method, -10000) sales_method,
            coalesce(spu_id, '-10000') spu_id,
            max(spu_name) spu_name,
            0  buy_policy_num, --当日保单数
            0 total_policy_num, --累计保单数
            0 month_buy_policy_num, --当月累计保单数
            0 premium_fee, --当日保单保费金额
            0 total_premium_fee, --累计保单保费金额
            0 month_premium_fee, --当月累计保费金额
            0 offer_fee, --当日OFFER收入
            0 coupon_amount, --当日券使用金额
            count(distinct case when policy_time like '${V_YESTERDAY_0}%' then user_mid else null end) buy_user_num, --当日保单人数
            count(distinct user_mid) total_user_num, --累计保单人数
            0 insurant_user_num, --当日被投保人数
            0 total_insurant_user_num --累计被投保人数
        from
        (
            select
                coalesce(channel_id,-1) channel_id,
                max(channel_name) channel_name,
                coalesce(inscompany_id,-1) inscompany_id,
                max(inscompany_name) inscompany_name,
                coalesce(product_id, -1) product_id,
                max(product_name) product_name,
                coalesce(sales_method,-1) sales_method,
                coalesce(spu_id,-1) spu_id,
                max(spu_name) spu_name,
                user_mid,
                max(policy_time) policy_time
            from manhattan_dw.dw_v_opph_order_policy_base
            where concat(year,month,day)='${V_YESTERDAY}'
            and policy_status in (3,4,5)
            and policy_time <= '${V_YESTERDAY_0} 23:59:59'
            group by user_mid,coalesce(channel_id,-1),coalesce(inscompany_id,-1),coalesce(product_id, -1),coalesce(sales_method,-1),coalesce(spu_id,-1)
        )t1
        group by channel_id,inscompany_id,product_id,sales_method,spu_id with cube

        union all

        --计算被投保人数

        select
            coalesce(channel_id, -10000) channel_id,
            max(channel_name) channel_name,
            coalesce(inscompany_id, -10000) inscompany_id,
            max(inscompany_name) inscompany_name,
            coalesce(product_id, -10000) product_id,
            max(product_name) product_name,
            coalesce(sales_method, -10000) sales_method,
            coalesce(spu_id, '-10000') spu_id,
            max(spu_name) spu_name,
            0  buy_policy_num, --当日保单数
            0 total_policy_num, --累计保单数
            0 month_buy_policy_num, --当月累计保单数
            0 premium_fee, --当日保单保费金额
            0 total_premium_fee, --累计保单保费金额
            0 month_premium_fee, --当月累计保费金额
            0 offer_fee, --当日OFFER收入
            0 coupon_amount, --当日券使用金额
            0 buy_user_num, --当日保单人数
            0 total_user_num, --累计保单人数
            count(distinct case when policy_time like '${V_YESTERDAY_0}%' then insurant_cert_no else null end) insurant_user_num, --当日被投保人数
            count(distinct insurant_cert_no) total_insurant_user_num --累计被投保人数
        from
        (
            select
                coalesce(channel_id,-1) channel_id,
                max(channel_name) channel_name,
                coalesce(inscompany_id,-1) inscompany_id,
                max(inscompany_name) inscompany_name,
                coalesce(product_id, -1) product_id,
                max(product_name) product_name,
                coalesce(sales_method,-1) sales_method,
                coalesce(spu_id,-1) spu_id,
                max(spu_name) spu_name,
                insurant_cert_no,
                max(policy_time) policy_time
            from manhattan_dw.dw_v_opph_order_policy_base
            where concat(year,month,day)='${V_YESTERDAY}'
            and policy_status in (3,4,5)
            and policy_time <= '${V_YESTERDAY_0} 23:59:59'
            group by insurant_cert_no,coalesce(channel_id,-1),coalesce(inscompany_id,-1),coalesce(product_id, -1),coalesce(sales_method,-1),coalesce(spu_id,-1)
        )t1
        group by channel_id,inscompany_id,product_id,sales_method,spu_id with cube

    )t1
    group by channel_id,inscompany_id,product_id,sales_method,spu_id
)t1
"
