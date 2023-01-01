# Open the Geoserver slice folder of the specified level (for example, level 15), then output the slice's information.
# Primarily the amount of surrounding blank pixels, the size of the original image, and other factors; used to replace slices.

from typing import Counter
import cv2 # The format read by opencv is BGR
import collections
from ruamel import yaml
import os
import ruamel.yaml
from PIL import Image

# As the input for reslicing in step 2, record the slice information.
tiles_info_yaml = "./tilesinfo.yaml"

# Creat yaml file
def creatYaml():
    py_object = {
                'num_x': '',
                'num_y': '',
                'left_blank': '',
                'top_blank': '',
                'right_blank': '',
                'bottom_blank': '',
                'real_width': '',
                'real_height': '',
                'new_png': '', 
                'result_png': ''            
                }
    doc = open(tiles_info_yaml, "w", encoding="utf-8")
    yaml.dump(py_object, doc, Dumper=yaml.RoundTripDumper)
    doc.close()

# Rewrite Yaml file
def writeYaml(tag, val):
    doc = open(tiles_info_yaml, "r",encoding="utf-8")
    data = ruamel.yaml.round_trip_load(doc)
    data[tag] = val
    doc = open(tiles_info_yaml, 'w+', encoding='utf-8')
    ruamel.yaml.round_trip_dump(data, doc, default_flow_style=False, allow_unicode=True) 
    doc.close()

# Read Yaml file
def readYaml(key):
    import yaml
    f = open(tiles_info_yaml, "r", encoding="utf-8")
    data = yaml.load(f,Loader=yaml.FullLoader)
    key = data.get(key)
    f.close
    return key

# Traverse all png file names in the folder
def listFilenames(dirpath, ext='.png'):
    filenames = []
    for root,dirs,files in os.walk(dirpath):
        for filename in files:
            # Specify the suffix file name; the actual using lambda expression is more elegant.
            if os.path.splitext(filename)[1] == ext:
                filenames.append(filename)
            break
    return filenames

# 解析所有文件名，根据geoserver命名规则，返回边角的png的路径
# 实际可以和上一个函数合为一个（少一次for循环），但为了逻辑清晰还是分开
# Parse all file names, and return the path of the png in the corner according to the geoserver naming rules
# Actually, it can be integrated with the previous function (one fewer for loop), but it is separated for clarity.
def parseFilenames(dirpath, filenames, ext='.png'):
    rows,cols = [],[]
    for filename in filenames:
        # just need filename
        filename = os.path.splitext(filename)[0]
        # spearated by "_"
        col,row = filename.split("_")
        rows.append(row)
        cols.append(col)
    # The maximum and minimum values ​​in rows
    max_row = max(rows)
    min_row = min(rows)
    max_col = max(cols)
    min_col = min(cols)
    num_x = int(max_row) - int(min_row) + 1
    num_y = int(max_col) - int(min_col) + 1
    # lefttop and rightbottom
    lefttop = str(min_col) + "_" + str(max_row) + ext
    rightbottom = str(max_col) + "_" + str(min_row) + ext
    lefttop = os.path.join(dirpath, lefttop)
    rightbottom = os.path.join(dirpath, rightbottom)
    # Write into yaml
    writeYaml('num_x', str(num_x))
    writeYaml('num_y', str(num_y))
    return [lefttop, rightbottom,num_x,num_y,min_col,max_row]

# 读取空白像素等信息，并记录为相应的yaml文件
# Read information such as blank pixels and record them as corresponding yaml files
def computeBlanks(lefttop, rightbottom, num_x, num_y):
    # Read blank pixels
    lt_img = cv2.imread(lefttop) # Pic at lefttop
    rb_img = cv2.imread(rightbottom) # Pic at rightbottom
    l,r,t,b = 0,0,0,0
    for i in range(256):
        # lefttop
        li = lt_img[255,i]
        ti = lt_img[i,255]
        # rifhtbottom
        # 注意：这里感觉不太对吧？对于右边的图片应该从255递减读取？
        # Note: doesn't feel right here? For the picture on the right it should be read decrementally from 255?
        ri = rb_img[0,i]
        bi = rb_img[i,0]
        if all(li == [255,255,255]):
            l = l + 1
        if all(ti == [255,255,255]):
            t = t + 1
        if all(ri == [255,255,255]):
            r = r + 1
        if all(bi == [255,255,255]):
            b = b + 1	    
    # Left-right-top-bootom
    print(l,'\t\t',r,'\t\t',t,'\t\t',b)
    # Write into yaml
    writeYaml('left_blank', str(l))
    writeYaml('right_blank', str(r))
    writeYaml('top_blank', str(t))
    writeYaml('bottom_blank', str(b))
    # Calculate the original image size
    real_width = 256*num_y - l - r
    real_height = 256*num_x - t - b
    print(real_width,'\t\t',real_height)
    # Write into yaml
    writeYaml('real_width', str(real_width))
    writeYaml('real_height', str(real_height))

def fillBlank(new_png,num_x,num_y,left_blank,top_blank):
    blank=Image.new("RGBA",(256*num_y,num_x*256),(255,255,255,0))  # new a blank picture
    img=Image.open(new_png)
    path = os.path.dirname(os.path.realpath(new_png)) 
    result_path = os.path.join(path,'result.png')         # open a picture
    blank.paste(img,(int(left_blank),int(top_blank)))     # paste an opened picture to a blank picture # blank.paste(img,(800,0)) 
    blank.save(str(result_path))
    writeYaml('result_png', str(result_path))         # save to a new picture

def cutPicture(min_col,max_row,num_x,num_y,file,NEWPNG):
    qian = int(min_col)
    hou  = int(max_row)
    X_NUM=num_x  # Split into several images vertically
    Y_NUM=num_y  # Split into several images horizontally
    LEN = 256  # Dimensions (length and width) of each image）
    COMMON = 0 # Common part length of adjacent blocks
    OLD_FORMAT = '.png' 
    NEW_FORMAT = '.png' 
    PATH =os.path.dirname(os.path.realpath(file)) # file path of original image
    newdir = os.path.join(PATH, 'clip')
    if (os.path.exists(newdir) == False):
        os.mkdir(newdir)  
    img = cv2.imread(NEWPNG, cv2.IMREAD_UNCHANGED)
    [h, w] = img.shape[:2]
    i=0
    for i in range(1,X_NUM+1):
        for j in range(1,Y_NUM+1):
                    # l1img = img[int((i-1)*h / num):int(i*h / num+1), int((j-1)*w / num):int(j*w / num+1), :]
                    l1img = img[int((i-1)*(LEN-COMMON)): int(i*LEN-(i-1)*COMMON), int((j-1)*(LEN-COMMON)):int(j*LEN-(j-1)*COMMON), :]
                    # path1=os.path.join(newdir, filename) +"_"+str(name) +"_sat.png"
                    path1=os.path.join(newdir,'') +'%06d' % int(qian+j-1)+'_'+'%06d' % int(hou-i+1)+ NEW_FORMAT 
                    # l1img=cv2.cvtColor(l1img, cv2.COLOR_BGR2GRAY)
                    cv2.imwrite(path1, l1img)               

def main(): 
    tiles_dir = r'C:\Users\Administrator.DESKTOP-1AF79L9\Desktop\geo\1\EPSG_900913_18\0202_0150'  #输入的地址
    # 1. 计算出空白像素的值，并将需要的信息输出到yaml
    # 1. Calculate the value of the blank pixel and output the required information to yaml
    creatYaml()
    png_filenames = listFilenames(tiles_dir)
    lefttop, rightbottom,num_x,num_y,min_col , min_row  = parseFilenames(tiles_dir, png_filenames)
    computeBlanks(lefttop, rightbottom,num_x,num_y)
    # writeYaml('new_png', str(r'C:\Users\Administrator.DESKTOP-1AF79L9\Desktop\cdut.png'))
    left_blank, top_blank = readYaml('left_blank'),readYaml('top_blank')
    # 2. 屏幕提示完成第1步，按计算的值重采样png并将其路径添加到"./tilesinfo.yaml"中，输入Y继续
    # 2. The screen prompt is complete Step 1, resample the png according to the calculated value and add its path to "./tilesinfo.yaml", enter Y to continue
    while(True):
        print("完成第1步，按计算的值重采样png并将其路径添加到<tilesinfo.yaml>中，输入Y继续。按Y/N")
        print("Complete step 1, resample the png by the calculated value and add its path to <tilesinfo.yaml>, enter Y to continue. Press Y/N")
        in_content = input("Please input：")
        if in_content == "Y"or"y":
            new_png = readYaml('new_png')
            fillBlank(new_png,num_x,num_y,left_blank,top_blank)
            file = new_png
            NEWPNG  = readYaml('result_png')
            cutPicture(min_col,min_row,num_x,num_y,file,NEWPNG)
            # 如果重采样结果和计算结果不一致（可能会相差1行或1列，因为重采样软件的原因），则需要修改yaml中的值
            # png文件名的信息在 png_filenames 中，可根据此自动重命名重新裁剪后的图片
            # If the resampling result is inconsistent with the calculation result (there may be a difference of 1 row or 1 column, because of the resampling software), 
            # you need to modify the value in yaml
            # The information of the png file name is in png_filenames, and the re-cropped image can be automatically renamed according to this
            print("amazing!!!")
            exit(0)
        elif in_content == "N":
            print("你已退出了该程序！")
            exit(0)
main()