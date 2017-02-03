#coding=utf8

import os

tables = """ \
fatman_promotion_click             |         1
fatman_policy_order_kpi            |         3
fatman_tmc_policy_daily            |         7
fatman_pay_order_daily             |         9
fatman_policy_order_daily          |        13
fatman_promotion_transform_analyze |        15
fatman_product_process_funnel      |        37
fatman_policy_monitor              |        39
fatman_policy_installment          |        59
fatman_policy_transform_analyze    |        61
littleboy_claim_order_kpi        |        65
littleboy_claim_order            |        71
littleboy_claim_rate             |        83
drip_loan_kpi                      |        67
drip_loan_kpi                      |        69
finance_fee_kpi                    |        73
finance_account_kpi                |        77
drip_loan_promotion_click          |        79
insurance_tracker_analysis         |        81
littleboy_product_process_funnel   |        85
littleboy_promotion_click          |        87
strategy_sale_push                 |        89
littleboy_weather_analysis         |       111
littleboy_wechat_notice            |       113
"""

def hadoop_get():
    """
    get run_jms.sh
    append
    java -jar ../tools/load-data-tools.jar $V_YESTERDAY $report_id
    except fatman_promotion_click
    """

    base_dir = "/user/fbi/online/hive"
    for line in tables.splitlines():
        rows = line.replace(' ','').split('|')
        if len(rows) != 2:
            print(rows)
            break
        t, report_id = rows[0], int(rows[1])
        cmd = "hadoop fs -cat {base_dir}/{t}/run_jms.sh > {t}/run_jms.sh".format(**locals())
        print(cmd)
        os.system(cmd)
        load_data_cmd =  'echo -e "\n\njava -jar ./load-data-tools.jar \\$V_YESTERDAY {report_id}" >> {t}/run_jms.sh'.format(**locals())
        print(load_data_cmd)
        os.system(load_data_cmd)

        #上传
        #rm_cmd = "hadoop fs -rm /user/fbi/online/hive/{t}/run_jms.sh".format(**locals())
        #print(rm_cmd)
        #put_cmd = "hadoop fs -put {t}/run_jms.sh /user/fbi/online/hive/{t}/".format(**locals())
        #print(put_cmd)


hadoop_get()
