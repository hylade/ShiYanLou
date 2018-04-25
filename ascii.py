#创建文件进行编辑
#导入必要的库，PIL.Image及argparse，argparse用于管理命令行参数输入的

from PIL import Image
import argparse

#下面是字符画中所使用的字符集，一共有70个字符，字符的种类和数量可以根据字符画的效果反复调试,可以随意更改
ascii_char = list("$@B%8&WM#*9oahkbd7pqwm6ZO0QL4eCJUY3Xzcvu6nxr。j5ft/\|(2)1{}[]?g-_+~<>i!lI;:,\"^`'. ")

#####################################################################################################
##python argparse宏包学习
##使用argparse第一步是创建一个解析器对象，并告诉其参数；解析器类为ArgumentParser，如：
##parser = argparse.ArgumentParse(description = "This is a example program") %description用途描述函数
##add_argument()方法，用于接受程序需要接受的命令参数
##一般语法：parser.add_argument('-shorname', '--fullname', type = ?, default = ?) %参数数量可选
##注意：shortname前只需'-',对于fullname需要'--'
##parser.add_argument('para') %这种格式是最简单的，且para这个参数是必须的
##parser.add_argument()方法具有
##dest：如果提供dest，例如dest="a"，那么可以通过args.a访问该参数
##default：设置参数的默认值
##action：参数出发的动作
##store：保存参数，默认
##store_const：保存一个被定义为参数规格一部分的值（常量），而不是一个来自参数解析而来的值
##store_ture/store_false：保存相应的布尔值
##append：将值保存在一个列表中
##append_const：将一个定义在参数规格中的值（常量）保存在一个列表中
##count：参数出现的次数:parser.add_argument("-v", "--verbosity", action="count",
# default=0, help="increase output verbosity")
##version：打印程序版本信息
##type：把从命令行输入的结果转成设置的类型
##choice：允许的参数值:parser.add_argument("-v", "--verbosity", type=int,
# choices=[0, 1, 2], help="increase output verbosity")
##help：参数命令的介绍
##parse_args()返回值是一个命名空间，用于获取参数值
##################################################################################################
parser = argparse.ArgumentParser()

parser.add_argument('file') #输入文件
parser.add_argument('-o', '--output') #输出文件
parser.add_argument('--width', type = int, default = 80) #输出字符画宽
parser.add_argument('--height', type = int, default = 80) #输出字符画高

args = parser.parse_args() #用于获取参数

IMG = args.file
WIDTH = args.width
HEIGHT = args.height
OUTPUT = args.output

#定义get_char方法，将256灰度映射到70个字符上
def get_char(r, g, b, alpha = 256):
    if alpha == 0:   #当'alpha = 0'时，判断图片完结
        return ' '
    length = len(ascii_char)
    gray = int(0.2116 * r + 0.7152 * g + 0.0711 * b)
    unit = (256.0 + 1) / length
    return ascii_char[int(gray / unit)]

if __name__ == '__main__': #__name__ 是当前模块名，当模块被直接运行时模块名为 __main__
                           # 这句话的意思就是，当模块被直接运行时，以下代码块将被运行，当模块是被导入时，代码块不被运行
    im = Image.open(IMG)
    im = im.resize((WIDTH, HEIGHT), Image.NEAREST)  #resize(seze, filter)，size具有（width，height两个参数）；filter
                                                    #具有四个参数，NEAREST指此时选择最近的对象
    txt = ''
    for i in range(HEIGHT):
        for j in range(WIDTH):
            txt += get_char(*im.getpixel((j,i))) #im.getpixel()返回的是一个元组，这个元组有三个元素，分别对应三个颜色通道(RGB)的值
                                                 #'*'是一个运算符，对元组使用'*'运算符即为对元组拆封操作，元组拆封会返回元组所有元素
                                                 #'*im.getpixel()'返回的三个值，正好对应get_char()函数的前三个参数
                                                 #'getpixel()'函数返回值由图片颜色模式决定，RGB:3元素组；RGBA:4元素组；Gray：int值
                                                 #此处是4元素组，当图片处于空白区域时，alpha=0
        txt += '\n'
    print(txt)

#字符画输出到文件
if OUTPUT:
    with open(OUTPUT, 'w') as f:
        f.write(txt)    #你可以反复调用write()来写入文件，但是务必要调用f.close()来关闭文件。当我们写文件时，
                        # 操作系统往往不会立刻把数据写入磁盘，而是放到内存缓存起来，空闲的时候再慢慢写入。只有调用close()方法时，
                        # 操作系统才保证把没有写入的数据全部写入磁盘。忘记调用close()的后果是数据可能只写了一部分到磁盘，
                        #剩下的丢失了。所以，还是用with语句来得保险
else:
    with open("output.txt", 'w') as f:
        f.write(txt)