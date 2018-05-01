# 程序原理：
# 1.遍历每个像素，检测像素颜色是否为肤色
# 2.将相邻的肤色像素归为一个皮肤区域，得到若干个皮肤区域
# 3.剔除像素数量极少的皮肤区域


# 非色情图片判断标准
# 1.皮肤区域的个数小于3个
# 2.皮肤区域的像素与图像所有像素的比值小于15%
# 3.最大皮肤区域小于总皮肤面积的45%
# 4.皮肤区域数量超过60个


# 一副图像有多个皮肤区域，为它们编号，从第一个发现的区域编号为0到第n个发现的区域编号为n-1
# 同时，对于像素，定义一种类型 Skin 来表示，类型中信息包括：编号 id ;是否肤色 skin ；皮肤区域号 region；
# 横坐标 x ；纵坐标 y
# 对于 region 属性，表示像素所在皮肤区域编号，创建对象时定义为无意义的 None


# 对于像素遍历过程中，若当前像素为肤色，且其相邻像素有肤色时，则将这些肤色像素归到一个皮肤区域
# 相邻像素的定义：通常需要考虑到周围的8个像素，但是由于其右方，左下方，下方，右下方的像素还未创建 Skin 对象
# 所以只需要考虑左方，左上方，上方，右上方的像素即可


# ######################实现脚本#######################

# 导入所需要的模块
import sys
import os
from collections import namedtuple
from PIL import Image


# 设计 Nude 类
class Nude(object):
    # 定义 Skin 类，这里使用nanmetuple()方法，即命名元组：
    # collections.namedtuple(typename, field_names)：typename：此元组的名称；field_names: 元祖中元素的名称
    Skin = namedtuple("Skin", "id skin region x y")

    # 初始化 Nude 类
    def __init__(self, path_or_image):
        # 当path_or_image为Image.Image类型时，直接可以赋值
        if isinstance(path_or_image, Image.Image):
            self.image = path_or_image
        # 若path_or_image为str类型的实例（指路径），打开图片
        elif isinstance(path_or_image, str):
            self.image = Image.open(path_or_image)

        # 获取图片所有颜色通道
        # getbands()函数能够返回一个元组，包含每一个band的名字，比如在在一副RGB图像上使用，返回('R','G', 'B')
        bands = self.image.getbands()
        # 判断是否为灰度图，若是，则将灰度图转换为RGB图
        if len(bands) == 1:
            # 新建大小相同的RGB图像
            new_img = Image.new("RGB", self.image.size)
            # 拷贝灰度图 self.image 到 RGB 图的 new_img.paste （PIL将自动完成颜色通道转换）
            # image.paste(image, box)将一张图粘贴到另一张图上。box变量可以是给定左上角的2元组，或者是定义了左，
            # 上，右和下像素坐标的4元组，或者为空（与（0， 0）效果一样）。注意：当使用4元组时，被粘贴的图像尺寸
            # 必须与区域尺寸一样；两者模式不一致时，被粘贴的图像将被转换为当前图像的模式
            new_img.paste(self.image)
            f = self.image.filename
            # 替换 self.image
            self.image = new_img
            self.image.filename = f

        # 创建list用于存储对应图像所有像素的全部 Skin 对象
        self.skin_map = []
        # 对于检测到的皮肤区域，元素的索引即为皮肤区域号，元素都是包含一些 Skin 对象的列表
        self.detected_regions = []
        # 对于待合并区域的元素
        self.merge_regions = []
        # 对于合并整合后的皮肤区域，元素的索引即为皮肤区域号，元素都是包含一些 Skin 对象的列表
        self.skin_regions = []
        # 将最近合并的两个皮肤区域的区域号初始化为-1
        self.last_from, self.last_to = -1, -1
        # 色情图片判断结果
        self.result = None
        # 处理得到的信息
        self.message = None
        # 图像宽高
        self.width, self.height = self.image.size
        # 图像总像素
        self.total_pixels = self.width * self.height

    # 由于图片越大，耗费的资源越大，所以有时候需要对图片进行缩小
    def resize(self, maxwidth=1000, maxheight=1000):
        """
        基于最大宽高按比例重新设置图片大小
        如果没有变化 返回 0
        原宽度大于 maxwidth 返回 1
        原高度大于 maxheight 返回 2
        原宽高各大于 maxwidth maxheight 返回 3
        """
        # 存储返回值
        ret = 0
        if maxwidth:
            if self.width > maxwidth:
                wpercent = (maxwidth / self.width)
                hsize = int((self.height * wpercent))
                fname = self.image.filename
                # Image.LANCZOS 是重采样滤波器，用于抗锯齿
                self.image = self.image.resize((maxwidth, hsize), Image.LANCZOS)
                self.image.filename = fname
                self.width, self.height = self.image.size
                self.total_pixels = self.width * self.height
                ret += 1
        if maxheight:
            if self.height > maxheight:
                hpercent = (maxheight / float(self.height))
                wsize = int((float(self.width) * float(hpercent)))
                fname = self.image.filename
                self.image = self.image.resize((wsize, maxheight), Image.LANCZOS)
                self.filename = fname
                self.width, self.height = self.image.size
                self.total_pixels = self.width * self.height
                ret += 2
        return ret

    # 关键解析方法
    def parse(self):
        # 如果已有结果，则返回本对象
        if self.result is not None:
            return self
        # 不然获得图像所有像素数据
        # load（）方法能为图像分配内存并从文件中加载它，能返回一个用于读取和修改像素的像素访问对象，这个对象
        # 是一个二维队列
        pixels = self.image.load()

        # 接下来，遍历所有像素，为每个像素创建 Skin 对象
        for y in range(self.height):
            for x in range(self.width):
                # 得到像素的RGB三个通道值
                # [x, y] 是[(x, y)]的简便写法
                r = pixels[x, y][0]     # 获取red
                g = pixels[x, y][1]     # 获取green
                b = pixels[x, y][2]     # 获取blue

                # 判断当前像素是否为肤色像素
                isSkin = True if self._classify_skin(r, g, b) else False
                # 给每个像素分配唯一的 id 值，（1， 2, 3， height * width）
                # 注意x， y的值从零开始的
                _id = x + y * self.width + 1
                # 为每个像素创建 Skin 对象，并添加到 self.skin_map 中
                self.skin_map.append(self.Skin(_id, isSkin, None, x, y))

                # 若当前像素并不是肤色，则跳过本次循环，继续遍历
                if not isSkin:
                    continue
                # 若当前像素是肤色像素，则需要进行处理，先遍历其相邻元素
                # 需要注意相邻像素的索引值，像素的 id 是从1开始的，但索引是从0开始的。所以当前像素在
                # self.skin_map中的索引值为 _id - 1 ,以此类推，左方像素为 _id - 1 -1
                # 左上方为 _id - 1 - self.width - 1,上方为 _id - 1 - self.width, 右上方为
                # _id - 1 - self.width + 1

                check_indexes = [_id - 2, _id - self.width -2, _id - self.width - 1, _id - self.width]
                # 分别检查四个相邻元素是否为肤色像素

                # 用来记录相邻像素中肤色像素所在的区域号，初始化为 -1
                region = -1
                # 遍历每一个相邻像素的索引
                for index in check_indexes:
                    # 尝试索引相邻像素的 Skin 对象，没有则跳出循环
                    try:
                        self.skin_map[index]
                    except IndexError:
                        break
                    # 相邻元素若为肤色像素
                    if self.skin_map[index].skin:
                        # 若相邻像素与当前像素的 region 均为有效值，且两者不同，且尚未添加相同的合并任务
                        if (self.skin_map[index].region is not None and
                                region is not None and region != -1 and
                                self.skin_map[index].region != region and
                                self.last_from != region and
                                self.last_to != self.skin_map[index].region):
                            # 那么添加这两个区域的合并任务
                            self._add_merge(region, self.skin_map[index].region)
                        region = self.skin_map[index].region
                        # self._add_merge()这个方法接收两个区域号，将其放入到self.merge_regions中
                        # self.merge_regions的每一个元素都是一个列表，这些列表中有多个区域号
                        # 表示这些区域号是相互连通的，需要合并

                # 遍历完所有相邻像素后，分两种情况处理
                # 1.所有相邻像素都不是肤像素：发现了新的皮肤区域
                # 2.存在区域号为有效值的相邻肤色像素：region存储的值把当前像素归到这个相邻像素所在的区域

                # 遍历完所有相邻像素后，若 region 仍等于 -1，说明所有相邻元素都不是肤色像素
                if region == -1:
                    # 更改属性为新的区域号，由于元组是不可变类型的，不能直接更改属性
                    # somenametuple._replace(kwargs)返回一个替换指定字段为参数的实例
                    _skin = self.skin_map[_id - 1]._replace(region=len(self.detected_regions))
                    self.skin_map[_id - 1] = _skin
                    # 将此肤色像素所在区域创建为新区域
                    self.detected_regions.append([self.skin_map[_id - 1]])

                    # region不等于 -1 且不等于 None， 说明有相邻像素为有效肤色像素
                elif region is not None:
                    # 将此像素的区域号改为与相邻像素相同
                    _skin = self.skin_map[_id - 1]._replace(region=region)
                    self.skin_map[_id - 1] = _skin
                    # 向这个区域的像素列表中添加此元素
                    self.detected_regions[region].append(self.skin_map[_id - 1])

        # 此时已经遍历所有元素，图片的皮肤区域初步划分完成，只是在self.merge_regions中还有一些连通的
        # 皮肤区域号，需要合并
        # 将完成合并的区域存储到 self.skin_regions
        self._merge(self.detected_regions, self.merge_regions)
        # 分析皮肤区域，得到判定结果
        self._analyse_regions()
        return self

        # 方法self._merge()是用来合并连通区域
        # 方法self._analyse_regions(),用来对图片进行判定

# 接下来，写出在之前程序中调用但没有写过的方法
# 基于像素的肤色检测技术

    def _classify_skin(self, r, g, b):
        # 根据RGB值判定
        rgb_classifier = r > 95 and g > 40 and g < 100 and b > 20 and max([r, g, b])\
                        - min([r, g, b]) > 15 and abs(r - g) > 15 and r > g and r > b
        # 根据处理后的RGB值判定
        nr, ng, nb = self._to_normalized(r, g, b)
        norm_rgb_classifier = nr / ng > 1.185 and float(r * b) / ((r + g + b) ** 2) > 0.107 and\
                             float(r * g) / ((r + g + b) ** 2) > 0.112
        # HSV颜色模式下的判定
        h, s, v = self._to_hsv(r, g, b)
        hsv_classifier = h > 0 and h < 35 and s > 0.23 and s < 0.68
        # YCbCr颜色模式下的判定
        y, cb, cr = self._to_ycbcr(r, g, b)
        ycbcr_classifier = 97.5 <= cb <= 142.5 and 134 <= cr <= 176

        # 此处可以return rgb_classifier or norm_rgb_classifier or hsv_classifier or ycbcr_classifier
        return ycbcr_classifier

    # 颜色模式的转换不是重点，网上有很多，直接荡
    def _to_normalized(self, r, g, b):
        if r == 0:
            r = 0.0001
        if g == 0:
            g = 0.0001
        if b == 0:
            b = 0.0001
        _sum = float(r + g + b)
        return [r / _sum, g / _sum, b / _sum]

    def _to_ycbcr(self, r, g, b):
        y = 0.299 * r + 0.587 * g + 0.114 * b
        cb = 128 - 0.168736 * r - 0.331364 * g + 0.5 * b
        cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
        return y, cb, cr

    # 接下来完成self._add_merge()方法
    # 主要是对self.merge_regions操作，而self.merge_regions的元素都是包含一些int对象的列表
    # 列表中的区域号代表的区域都待合并的区域
    # self._add_merge()接收两个区域号，将之添加到self.merge_regions中

    # 这两个区域号如何处理，分为3种情况
    # 1.传入的两个区域号都在self.merge_regions中
    # 2.传入的两个区域号中一个在self.merge_regions中
    # 3.传入的两个区域号都不在self.merge_regions中

    def _add_merge(self, _from, _to):
        # 两个区域号赋值给类属性
        self.last_from = _from
        self.last_to = _to
        # 记录self.merge_regions的某个索引值，初始化为-1
        from_index = -1
        # 记录self.merge_regions的某个索引值，初始化为-1
        to_index = -1

        # 遍历每个 self.merge_regions的元素
        for index, region in enumerate(self.merge_regions):
            # 遍历元素的每个区域号
            for r_index in region:
                if r_index == _from:
                    from_index = index
                if r_index == _to:
                    to_index = index

        # 若两个区域号都在 self.merge_regions中
        if from_index != -1 and to_index != -1:
            # 那么这两个区域号分别在两个列表中，合并这两个列表
            if from_index != to_index:
                self.merge_regions[from_index].extend(self.merge_regions[to_index])
                del(self.merge_regions[to_index])
            return
            # 若两个区域号都不在 self.merge_regions中
        if from_index == -1 and to_index == -1:
            # 创建新的区域号列表
            self.merge_regions.append([_from, _to])
            return
        # 若两者之间有一个存在于 self.merge_regions中
        # 将不存在self.merge_regions中的区域号添加到另一个区域号所在的列表
        if from_index != -1 and to_index == -1:
            self.merge_regions[from_index].append(_to)
            return
        if from_index == -1 and to_index != -1:
            self.merge_regions[to_index].append(_from)
            return

    def _merge(self, detected_regions, merge_regions):
        # 该方法将self.merge_regions中的元素区域号所代表的区域合并，得到新的皮肤区域列表
        # 新的列表为new_detected_regions
        # 其元素是包含一些代表像素的 Skin 对象的列表
        # new_detected_regions的元素即代表皮肤区域，元素索引为区域号
        new_detected_regions = []

        # 将merge_regions中的元素中的区域号所代表的所有区域合并
        for index, region in enumerate(merge_regions):
            try:
                new_detected_regions[index]
            except IndexError:
                new_detected_regions.append([])
            for r_index in region:
                new_detected_regions[index].extend(detected_regions[r_index])
                detected_regions[r_index] = []

        # 添加剩余的其余皮肤区域到 new_detected_regions
        for region in detected_regions:
            if len(region) > 0:
                new_detected_regions.append(region)

        # 清理new_detected_regions
        self._clear_regions(new_detected_regions)

    # self._clear_regions()方法是将像素数大于指定数量的皮肤区域保留到self.skin_regions
    # 皮肤区域清理函数
    # 只保存像素数大于指定数量的皮肤区域
    def _clear_regions(self, detected_regions):
        for region in detected_regions:
            if len(region) > 30:
                self.skin_regions.append(region)

    # 分析函数
    def _analyse_regions(self):
        # 如果皮肤区域小于3个，不是色情
        if len(self.skin_regions) < 3:
            self.message = "Less than 3 skin regions ({_skin_regions_size})".format(
                            _skin_regions_size=len(self.skin_regions))
            self.result = False
            return self.result

        # 为皮肤区域排序
        self.skin_regions = sorted(self.skin_regions, key=lambda s: len(s), reverse=True)

        # 计算皮肤总像素数
        total_skin = float(sum([len(skin_region) for skin_region in self.skin_regions]))

        # 如果皮肤区域与整个图像的比值小于15%,不是色情图片
        if total_skin / self.total_pixels * 100 < 15:
            self.message = "Total skin percentage lower than 15({:.2f})".format(
                total_skin / self.total_pixels * 100
            )
            self.result = False
            return self.result

        # 如果最大皮肤区域小于总皮肤面积的45%，不是色情图片
        if len(self.skin_regions[0]) / total_skin * 100 < 45:
            self.message = "The biggest region contains less than 45 ({:.2f})".format(
                len(self.skin_regions[0]) / total_skin * 100
            )
            self.result = False
            return self.result

        # 如果皮肤区域数量超过60个，不是色情图片
        if len(self.skin_regions) > 60:
            self.message = "More than 60 skin regions ({})".format(
                len(self.skin_regions)
            )
            self.result = False
            return self.result

        # 其他情况为色情图片
        self.message = "Nude!!"
        self.result = True
        return self.result

    # 组织分析得出的信息
    def inspect(self):
        _image = '{}{}{}*{}'.format(self.image.filename, self.image.format,
                                    self.width, self.height)
        return "{_image}: result = {_result} message = '{_message}'".format(
            _image=_image, _result=self.result, _message=self.message
        )

    # 若此时停止，只能得到文本信息，可以通过下述程序获得黑白图片，直观感受
    def showSkinRegions(self):
        # 未得出结果时方法返回
        if self.result is None:
            return
        # 皮肤像素 ID 的集合
        skinIdSet = set()
        # 将原图做一份拷贝
        simage = self.image
        # 加载数据
        simageData = simage.load()

        # 将皮肤像素的id存入 skinIdSet
        for sr in self.skin_regions:
            for pixel in sr:
                skinIdSet.add(pixel.id)
        # 将图像中的皮肤像素设置为白色，其余为黑色
        for pixel in self.skin_map:
            if pixel.id not in skinIdSet:
                simageData[pixel.x, pixel.y] = 0, 0, 0
            else:
                simageData[pixel.x, pixel.y] = 255, 255, 255
        # 源文件绝对路径
        filePath = os.path.abspath(self.image.filename)
        # 源文件所在目录
        fileDirectory = os.path.dirname(filePath) + '/'
        # 源文件完整文件名
        fileFullNmae = os.path.basename(filePath)
        # 分离源文件的完整文件名得到文件名和拓展名
        fileName, fileExtName = os.path.split(fileFullNmae)
        # 保持图片
        simage.save('{}{}_{}{}'.format(fileDirectory, fileName, 'Nude'
                                       if self.result else 'Normal', fileExtName))

    def _to_hsv(self, r, g, b):
        h = 0
        _sum = float(r + g + b)
        _max = float(max([r, g, b]))
        _min = float(min([r, g, b]))
        diff = float(_max - _min)
        if _sum == 0:
            _sum = 0.0001

        if _max == r:
            if diff == 0:
                h = sys.maxsize
            else:
                h = (g - b) / diff

        elif _max == g:
            h = 2 + ((g - r) / diff)
        else:
            h = 4 + ((r - g) / diff)

        h *= 60
        if h < 0:
            h += 360
        return [h, 1.0 - (3.0 * (_min / _sum)), (1.0 / 3.0) * _max]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Detect nudity in images/')
    parser.add_argument('files', metavar='image', nargs='+', help='Images you wish to test')
    parser.add_argument('-r', '--resize', action='store_true', help='Reduce image'
                        'size to increase speed of scanning')
    parser.add_argument('-v', '--visualization', action='store_true', help='Generating'
                        'areas of image')
    args = parser.parse_args()

    for fname in args.files:
        if os.path.isfile(fname):
            n = Nude(fname)
            if args.resize:
                n.resize(maxheight=800, maxwidth=600)
            n.parse()
            if args.visualization:
                n.showSkinRegions()
            print(n.result, n.inspect())
        else:
            print(fname, "is not a file")
