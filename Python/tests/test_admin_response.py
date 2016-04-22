# coding=utf8

import os
import re
import time
from selenium.common.exceptions import NoSuchElementException

from statistics.log import base

from base import FunctionalTest
from const import ADMIN_DEFAULT_UID, DEFAULT_WAIT

MENU_WAIT = 2


class AdminResponseTest(FunctionalTest):

    def setUp(self):
        # login
        super(AdminResponseTest, self).setUp()
        self.create_pre_authenticated_session(ADMIN_DEFAULT_UID)

    def test_admin(self):
        self.admin_login_test()
        self.click_all_menu_test()
        self.daily_data_test()

    def admin_login_test(self):
        """测试admin登陆是否成功"""
        self.browser.get(self.server_url)
        self.wait_loader()
        system = self.browser.find_element_by_xpath("/html/body/div[1]/div[2]/span[1]/a")
        admin_href = system.get_attribute("href")
        self.assertEqual(admin_href, self.server_url + "/system")

    def click_all_menu_test(self):
        """child点击页面链接， 查看日志"""
        self.browser.get(self.server_url)
        self.wait_loader()
        print("click all nav")
        nav = self.browser.find_element_by_class_name("bi-nav")
        items = nav.find_elements_by_class_name("item")
        load_re = re.compile(r"load\(\d+\)")
        for item in items:
            # 一级菜单
            main_list= item.find_element_by_class_name("main-list")
            main_title = item.find_element_by_class_name("main-title")
            print(main_title.text.encode("utf8"))
            is_display = self.check_is_display(main_list)
            if not is_display:
                main_title.click()
                self.browser.implicitly_wait(MENU_WAIT)

            self.browser.implicitly_wait(MENU_WAIT)
            # 二级菜单
            li_tags = item.find_elements_by_tag_name("li")
            valid_litags = [li for li in li_tags if li.get_attribute("class") != "third-title"]
            for li_tag in valid_litags:
                has_sub = False
                try:
                    sub_list = li_tag.find_element_by_class_name("sub-list")
                except NoSuchElementException:
                    # 有些没有下级菜单
                    sub_list = li_tag.find_element_by_class_name("sub-title")
                else:
                    has_sub = True
                    sub_title = li_tag.find_element_by_class_name("sub-title")
                    print("\t{0}".format(sub_title.text.encode("utf8")))
                    is_display = self.check_is_display(sub_list)
                    if not is_display:
                        sub_title_a = sub_title.find_element_by_tag_name("a")
                        sub_title_a.click()
                        self.browser.implicitly_wait(MENU_WAIT)

                # 点击子菜单
                childs = sub_list.find_elements_by_tag_name("a")
                self.browser.implicitly_wait(MENU_WAIT)
                # print(len(childs))
                for child in childs:
                    time.sleep(3)
                    indent = "\t\t" if has_sub else "\t"
                    func = load_re.search(child.get_attribute("onclick"))
                    print("{0}{1} {2}".format(indent, child.text.encode("utf8"), func.group()))
                    child.click()
                    self.wait_loader()
        # 查看日志
        files = [f for f in os.listdir(base) if os.stat(os.path.join(base, f)).st_size > 0]
        if files:
            cmd = """grep "ERROR" %s/*.log""" % base
            print(cmd)
            # self.assertEqual(os.system(cmd), 0)

    def daily_data_test(self):
        """自动邮件相关测试"""
        keys = ["kpi", "internal", "outer"]
        trade_re = re.compile("(\d|,)+")
        for key in keys:
            url = self.server_url + '/daily_data/' + key + '/'
            self.browser.get(url)
            time.sleep(3)
            self.wait_for_element_with_id("complete")
            title = self.browser.find_element_by_id("title_table")
            ptags = title.find_elements_by_tag_name("p")
            # 至少有一款游戏
            self.assertGreater(len(ptags), 3)
            all_trade = trade_re.search(ptags[1].text).group()
            self.assertGreater(int(all_trade.replace(',', '')), 0)

    def check_is_display(self, element):
        """根据style判断是否显示还是隐藏"""
        style = element.get_attribute("style")
        return "block" in style

    def wait_loader(self):
        """等待加载"""
        try:
            init_loader = self.browser.find_element_by_class_name("init-loader")
        except TypeError:
            # 没有加载框
            self.browser.implicitly_wait(DEFAULT_WAIT)
        else:
            self.wait_for(lambda: self.assertIn("item-hide", init_loader.get_attribute("class")))
