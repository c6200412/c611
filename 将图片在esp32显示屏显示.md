完整操作手册（含所有命令）
下面每一步都写清楚「做什么、在哪做、输入什么命令」。已经完成的步骤标 ✅，剩下的标 ⏳。

第 0 步：确认环境（✅ 已装好，不用再动）
装 Pillow 和 numpy 到你的 Python 里（已经装好了，这里只是让你知道命令长这样）：
python -m pip install pillow numpy
验证：
python -c "import PIL, numpy; print('OK')"
# 输出 OK 就说明环境没问

/*********************************************/
第 1 步：转换照片（✅ 已完成）
在 VSCode 底部终端、项目目录下运行：
cd C:\Users\王任卓\Documents\PlatformIO\Projects\esp8266
python convert.py C:\Users\王任卓\Desktop\23.png
成功后输出：
OK: C:\Users\王任卓\Desktop\23.png -> data/photo.raw  (240x320, 153600 bytes)
结果：项目里多了 data/photo.raw（150KB），这就是屏幕要的数据。

换照片就换命令后面的路径；换分辨率就加两个数字：python convert.py 照片.png 320 240



/***********************************************************/
第 2 步：改 platformio.ini（⏳ 待做）
用 VSCode 打开项目里的 platformio.ini，整个文件替换成：
[env:nodemcuv2]
platform = espressif8266
board = nodemcuv2
framework = arduino
文件系统开关（让板子能存照片）：
board_build.filesystem = littlefs
lib_deps =
    knolleary/PubSubClient@^2.8
    dfrobot/DFRobot_DHT11@^1.0.0
    adafruit/DHT sensor library@^1.4.7
    bodmer/TFT_eSPI@^2.5.43//屏幕驱动库（TFT_eSPI），加进 lib_deps 列表里：

屏幕参数（驱动型号、分辨率、引脚），在文件末尾加：
build_flags =
    -D USER_SETUP_LOADED=1
    -D ST7789_DRIVER=1
    -D TFT_WIDTH=240
    -D TFT_HEIGHT=320
    -D TFT_MISO=-1
    -D TFT_MOSI=13
    -D TFT_SCLK=14
    -D TFT_CS=4
    -D TFT_DC=5
    -D TFT_RST=2
    -D SPI_FREQUENCY=40000000
    -D LOAD_GLCD=1
    -D LOAD_FONT2=1
换屏只改 3 处：ST7789_DRIVER（芯片名）、TFT_WIDTH/HEIGHT（分辨率）、TFT_MOSI~RST
（接线引脚）。


/********************************************************/
第 3 步：写显示代码（⏳ 待做）
在 src/ 里新建 photo_test.cpp，内容：
Copy code to clipboard
/**
 * 照片显示测试程序
 * 功能：从板子文件系统(LittleFS)里读出 photo.raw，按行刷到屏幕上
 * 思路：板子不负责"解码"，只负责"读数据 + 刷屏"
 */
#include <Arduino.h>
#include <LittleFS.h>   // 文件系统库：能访问烧进去的 photo.raw 文件
#include <TFT_eSPI.h>   // 屏幕驱动库：提供 pushImage 等刷屏函数

TFT_eSPI tft = TFT_eSPI();  // 创建屏幕对象，后面所有操作都通过 tft 调用

void setup() {
  Serial.begin(115200);      // 打开串口，方便电脑上看调试信息

  // ---- 1. 初始化屏幕 ----
  tft.init();                // 初始化屏幕硬件（配引脚、开电源等）
  tft.setRotation(0);        // 设显示方向，0~3 对应四个方向，反了改这里
  tft.fillScreen(TFT_BLACK); // 先清屏为黑色，避免显示残留

  // ---- 2. 挂载文件系统 ----
  // LittleFS 是板子 flash 上的一块"存储区"，photo.raw 就烧在这里面
  if (!LittleFS.begin()) {
    tft.drawString("LittleFS failed", 0, 0, 2);  // 挂载失败，屏幕上提示
    return;                                      // 直接退出，不再往下跑
  }

  // ---- 3. 打开照片数据文件 ----
  File f = LittleFS.open("/photo.raw", "r");  // 以"只读"方式打开文件
  if (!f) {                                   // 打开失败 = 文件没烧进去
    tft.drawString("no photo.raw", 0, 0, 2);  // 屏幕上提示
    return;
  }

  // ---- 4. 按行读数据、按行刷屏（核心！省内存的关键）----
  const int W = 240, H = 320;  // 屏幕宽高，必须和 convert.py 生成时一致
  uint16_t row[W];             // 一行像素的缓冲区：240 个像素 × 2字节 = 480字节
                               // 为什么"按行"？ESP8266 内存小，装不下整张图(150KB)，
                               // 一次只读一行(480字节)就不会爆内存

  for (int y = 0; y < H; y++) {          // 从上到下一行一行刷
    f.read((uint8_t*)row, W * 2);        // 从文件读一行数据到缓冲区（240×2=480字节）
    tft.pushImage(0, y, W, 1, row);      // 把这行画到屏幕第 y 行
  }
  // pushImage 参数含义：(起始x, 起始y, 宽, 高, 数据指针)
  // 这里 (0, y, 240, 1, row) = 在(0,y)画一行，宽240、高1

  f.close();                // 用完关闭文件，释放资源
  Serial.println("done");   // 串口打印"done"，表示刷完了
}

void loop() {
  // 照片显示完就完事了，不需要循环做什么，所以空着
}

重要：测试期间把你原来的 src/main.cpp 改名成 main.cpp.bak（不然两套 setup/loop 会编译冲突）。测试完再恢复。
￼/***********************************************/
第 4 步：烧录（⏳ 待做）
在项目目录的终端里，两条命令都要跑：
Copy code to clipboard
pio run -t uploadfs    # ① 把 photo.raw 烧进板子文件系统
pio run -t upload      # ② 把代码烧进板子（第一次会下载 TFT_eSPI，联网稍慢）
或者鼠标操作：VSCode 左侧 PlatformIO 图标 → env:nodemcuv2 → Platform → Upload Filesystem Image，再点 General → Upload。
烧完按一下板子复位键，屏幕应该就出照片了。
￼/*************************************************************/
第 5 步：出问题看这张表
屏幕显示
原因
解决
no photo.raw
没烧文件系统
重跑 pio run -t uploadfs
LittleFS failed
文件系统没配好
检查 platformio.ini 有 board_build.filesystem = littlefs
颜色红蓝颠倒
字节序错
检查 convert.py 有 astype('<u2')
花屏/偏移
分辨率或旋转不对
改 TFT_WIDTH/HEIGHT 或 setRotation(0~3)
编译报错
TFT_eSPI 没下下来
联网重试 pio run -t upload
板子反复重启
内存不够
确认是「按行刷」没整帧 malloc
思路完全不变，只改「跟板子绑定」的 3 个地方。给你一张对照表 + 具体改法。

换板子只改这 3 处
要改的	ESP8266	ESP32	STM32
platformio.ini 的 platform/board	espressif8266 / nodemcuv2	espressif32 / esp32dev	ststm32 / 具体型号
引脚（build_flags 里的数字）	13/14/4/5/2	换 ESP32 的 GPIO	换 STM32 的引脚
文件系统头文件	<LittleFS.h>	<LittleFS.h>（新）或 <SPIFFS.h>（旧）	没有，改用 SD 卡 + FatFS
不变的部分：convert.py、显示代码的按行刷屏逻辑、烧录流程，全一样。

举例：换成 ESP32（最常见）
1. platformio.ini 改两行

[env:esp32dev]
platform = espressif32      ; 原来是 espressif8266
board = esp32dev            ; 原来是 nodemcuv2
framework = arduino
board_build.filesystem = littlefs

lib_deps =
    bodmer/TFT_eSPI@^2.5.43

build_flags =
    -D USER_SETUP_LOADED=1
    -D ST7789_DRIVER=1
    -D TFT_WIDTH=240
    -D TFT_HEIGHT=320
    -D TFT_MISO=-1
    -D TFT_MOSI=23          ; ESP32 的 GPIO23
    -D TFT_SCLK=18          ; GPIO18
    -D TFT_CS=5             ; GPIO5
    -D TFT_DC=4             ; GPIO4
    -D TFT_RST=-1           ; 或接复位脚 GPIO
    -D SPI_FREQUENCY=40000000
    -D LOAD_GLCD=1
    -D LOAD_FONT2=1
注意：ESP32 的引脚编号跟 ESP8266 完全不同，必须按你实际的接线填，不能照搬 ESP8266 的 13/14/4/5。
///////////////////////////如果不是esp8266的做法*********************、
2. 显示代码几乎不用改
photo_test.cpp 里只有文件系统头文件可能要换：


#include <LittleFS.h>   // 新版 ESP32 用这个（Arduino-ESP32 core 3.x）
// 或
#include <SPIFFS.h>     // 旧版 ESP32（core 2.x）用这个，同时 LittleFS.begin() 改成 SPIFFS.begin()
其余按行刷的代码原样照用——ESP32 内存大，但按行刷是通用写法，不用改。

3. 烧录命令一样

pio run -t uploadfs
pio run -t upload
总结成一句话
换板子 = 改 platformio.ini 的板子名 + 改引脚 + 换文件系统头文件，共 3 处；convert.py 和刷屏逻辑不动。

不过与其讲假设，不如直接告诉我：你手上实际是哪块板子？ 是 ESP32 吗？具体型号（板子上印的字，比如 ESP32-WROOM-32 / NodeMCU-32S / ESP32 DevKit）？我直接按你的板子给一份完整能用的配置。
//////***************************************************************************/
对，理解正确 ✅。PlatformIO 的项目，命令都在它生成的那个工程目录（就是 esp8266 文件夹，里面有 platformio.ini）里跑。

两类命令都在这个目录里跑
命令	在哪个目录跑	为什么
python convert.py 照片路径	工程目录 esp8266	生成的 photo.raw 才会落进项目的 data/ 里
pio run -t upload / uploadfs	工程目录 esp8266	pio 靠 platformio.ini 识别这是哪个工程
怎么判断「我在不在对的地方」
看终端最前面的路径提示：


PS C:\Users\王任卓\Documents\PlatformIO\Projects\esp8266>   ← 对，就是这里
只要最后是 ...\esp8266，就说明在对的目录，两条命令都能跑。

最省事的方式（不用手动 cd）
用 VSCode 打开文件夹 → 选 esp8266 目录，然后打开底部终端，它会自动就在这个目录，你直接敲命令就行，不用管 cd。

所以总结一句：
