# coding=utf8

# 静态资源发布

import os
import re
import sys
import shutil
import hashlib


class Asset(object):
    """资源属性"""
    DELIMITER = "__"
    STATIC_SUFFIX = (".css", ".js")

    def __init__(self, base, path):
        self.base = base         # 基目录
        self.path = path         # 文件目录
        self.name = None         # 相对基目录位置
        self.key = None          # self.name去除版本号
        self.fingerprint = None  # 指纹
        self.upath = None        # 唯一标识符路径
        self.set_up()

    def set_up(self):
        relative = self.path.replace(self.base, '')
        if relative.startswith('/'):
            relative = relative[1:]
        self.name = relative

        index = relative.rfind(self.DELIMITER)
        if index != -1:
            end = relative.rfind('.')
            self.key = relative[:index] + relative[end:]
        else:
            self.key = relative

        m = hashlib.sha1()
        with open(self.path) as f:
            m.update(f.read())
        self.fingerprint = m.hexdigest()

    def uid_path(self):
        """唯一标识符
        对于已有的返回旧有标识符
        """
        if not self.name.endswith(self.STATIC_SUFFIX):
            return self.name

        if self.upath is not None:
            return self.upath

        base, name = os.path.split(self.name)
        index = name.rfind(self.DELIMITER)
        end = name.rfind('.')
        if index != -1:
            start = index
            uid = name[index + 2: end]
        else:
            start = end
            mtime = os.stat(self.path).st_mtime
            uid = hex(int(mtime))[2:]

        self.upath = os.path.join(base, "".join([name[:start], self.DELIMITER, uid, name[end:]]))

        return self.upath

    def same(self, dasset):
        """是否相同"""
        return self.fingerprint == dasset.fingerprint


class Collector(object):
    """静态文件收集"""

    def __init__(self, src, template, dst):
        self.src = src
        self.dst = dst
        self.template = template
        self.src_files = self.collect_file(src)
        self.dst_files = self.collect_file(dst)
        self.template_files = self.collect_file(template)

    def collect_file(self, base):
        # {file:asset}
        all_files = {}
        for root, dirs, files in os.walk(base):
            for file in files:
                path = os.path.join(root, file)
                asset = Asset(base, path)
                all_files[asset.key] = asset

        return all_files


class AssetDistribute(object):
    STATIC_RE = re.compile(r"/static/(.+?\.(js|css))")
    TEMPLATE_SUFFIX = (".html", )

    def __init__(self, src, template, dst, out):

        self.src = os.path.abspath(src)
        self.template = os.path.abspath(template)
        self.dst = os.path.abspath(dst)

        self.out = os.path.abspath(out)
        self.old = os.path.abspath("old")
        self.discard = None  # 丢弃的文件(包括不用和已修改文件)
        self.change = {}     # 修改的文件
        self.unchange = {}   # 未修改文件
        self.all_files = {}
        self.set_up()

    def set_up(self):
        print("src: %s, template: %s, dst: %s" % (self.src, self.template, self.dst))
        print("out: %s" % self.out)
        self.collector = Collector(self.src, self.template, self.dst)

    def compare(self):
        """比对"""
        src_files, dst_files = self.collector.src_files, self.collector.dst_files
        self.discard = {dst_files[diff].name for diff in (dst_files.viewkeys() - src_files.viewkeys())}

        for sfile, sasset in src_files.iteritems():
            dasset = dst_files.get(sfile)
            if dasset is None:  # 新文件
                self.change[sfile] = sasset
            elif not sasset.same(dasset):  # 指纹不一样
                self.discard.add(sasset.name)
                self.change[sfile] = sasset
            else:  # 指纹一样
                self.unchange[sfile] = dasset

        self.all_files.update(self.change)
        self.all_files.update(self.unchange)

    def gen_static(self):
        """输出修改的带版本号的静态资源"""
        static = os.path.join(self.out, "static")
        print("static: %s" % static)
        if not os.path.exists(static):
            os.makedirs(static)
        for cf, asset in self.change.iteritems():
            dst = os.path.join(static, asset.uid_path())
            dir_path = os.path.dirname(dst)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            shutil.copy(asset.path, dst)

    def gen_template(self):
        """模板替换静态资源路径"""
        template = os.path.join(self.out, "templates")
        print("template: %s" % template)
        if not os.path.exists(template):
            os.makedirs(template)
        for t, asset in self.collector.template_files.iteritems():
            path = os.path.join(template, asset.name)
            dir_path = os.path.dirname(path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            self.replace_template(asset.path, path)

    def replace_template(self, src, dst):
        static_re = self.STATIC_RE
        with open(dst, 'w') as df:
            rows = []
            with open(src) as sf:
                for line in sf:
                    matchs = static_re.finditer(line)
                    for match in matchs:
                        name = match.group(1)
                        asset = self.all_files.get(name)
                        if asset is not None:
                            line = line.replace(name, asset.uid_path())

                    rows.append(line)

            df.writelines(rows)

    def gen_discard(self):
        """记录没用文件"""
        discard = os.path.join(self.out, "discard.txt")
        rows = "\n".join(self.discard)
        with open(discard, 'w') as f:
            f.write(rows)

    def distribute(self):
        """静态资源分发"""
        self.compare()
        self.gen_static()
        self.gen_template()
        self.gen_discard()


def test():
    static = "/home/skycrab/project/yhb/python/dataeye/static2"
    template = "/home/skycrab/project/yhb/python/dataeye/templates2"
    asset = AssetDistribute(static, template, "./dst", "./out")
    asset.distribute()


def main():
    # 静态资源目录(src)
    src = sys.argv[1]
    # 模板目录
    template = sys.argv[2]
    # 复制位置(比对目录)
    dst = sys.argv[3]
    # 输出目录
    out = sys.argv[4] if len(sys.argv) > 4 else None

    asset = AssetDistribute(src, template, dst, out)
    asset.distribute()


if __name__ == "__main__":
    main()
