先写函数再调用函数


项目一：呼吸灯（最简单，验证配置）
接线：PA6（TIM3_CH1）→ LED（串 220Ω 电阻）→ GND
这两行叫钳位（clamp）——把 duty_percent 的值限制在 0~100 的合法范围内，防止越界。
/***************************************************************************************/
逐行解释
if (x < 合法最小值) x = 合法最小值;
if (x > 合法最大值) x = 合法最大值;
判断钳位写什么 = 搞清楚这个参数**"允许取多大的值"**。

占空比 → 0~100
角度 → 0~180
颜色 → 0~255
频率 → 大于 0（具体上限看时钟和寄存器位数）

if (duty_percent < 0.0f)   duty_percent = 0.0f;   // 如果比 0 小，就改成 0
if (duty_percent > 100.0f) duty_percent = 100.0f; // 如果比 100 大，就改成 100
第一行：下限保护。传入负数（比如 -20），强行变成 0。
第二行：上限保护。传入超过 100（比如 150），强行变成 100。
为什么要加这个
因为下一行要用它算 CCR
uint32_t ccr = (uint32_t)((duty_percent / 100.0f) * (arr + 1));
如果 duty_percent = 150，算出来 ccr = 1.5 × (arr+1)，超过了 CCR 寄存器能装的最大值，写进去就是垃圾值，PWM 行为会乱套。
所以这两行是**"把好门"**：不管你调用时传了什么乱七八糟的值，进了函数先修正成合法值，后面的计算就永远安全。
、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、
CubeMX 参数：

参数	值
PSC	71（F103）/ 83（F407）→ 计数频率 1MHz
ARR	999 → PWM 频率 1kHz
Pulse	0（初始熄灭）
代码：
/* 通用占空比函数，放 main() 后 */
void PWM_SetDuty(TIM_HandleTypeDef *htim, uint32_t channel, float duty_percent)
{
    if (duty_percent < 0.0f)   duty_percent = 0.0f;
    if (duty_percent > 100.0f) duty_percent = 100.0f;
    uint32_t arr = __HAL_TIM_GET_AUTORELOAD(htim);
//第一行：读周期
uint32_t arr = __HAL_TIM_GET_AUTORELOAD(htim);
__HAL_TIM_GET_AUTORELOAD 是 HAL 的宏，作用就是读出定时器的 ARR 寄存器（自动重装载值）；
ARR 决定了 PWM 的周期（也就是频率），在 CubeMX 初始化时已经设好；
把它存进局部变量 arr，供下一行计算用。
    __HAL_TIM_SET_COMPARE(htim, channel, (uint32_t)(duty_percent / 100.0f * (arr + 1)));
}
//第二行：算占空比并写入

__HAL_TIM_SET_COMPARE(htim, channel, (uint32_t)(duty_percent / 100.0f * (arr + 1)));
它其实干了两件事：
① 计算：(uint32_t)(duty_percent / 100.0f * (arr + 1))
duty_percent / 100.0f → 把百分比变成 0~1 的小数比例
* (arr + 1) → 放大到 CCR 的取值范围
(uint32_t) → 转成整数
例：arr = 999，duty_percent = 50：
50 / 100.0f = 0.5
0.5 * (999 + 1) = 0.5 * 1000 = 500


② 写入：__HAL_TIM_SET_COMPARE(htim, channel, ...)

这个宏把算好的值写进 CCR 寄存器（捕获/比较寄存器）；
定时器硬件立刻用这个新值去比较，引脚输出马上变成对应的占空比
/* main 里 */
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);   // 启动

while (1)
{
    for (int i = 0; i <= 100; i++) { PWM_SetDuty(&htim3, TIM_CHANNEL_1, i); HAL_Delay(10); }
    for (int i = 100; i >= 0; i--) { PWM_SetDuty(&htim3, TIM_CHANNEL_1, i); HAL_Delay(10); }
}
效果：LED 从灭到亮、从亮到灭循环。线性变化看起来"呼吸"不够自然，想更平滑就把占空比换成正弦曲线（见文末）。


。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。。

项目二：舵机控制（PWM 最经典应用）
接线：PA6（TIM3_CH1）→ 舵机信号线（黄），舵机红线→5V，棕线→GND
CubeMX 参数：
参数	值
PSC	71（F103）/ 83（F407）→ 1MHz，1 个计数 = 1μs
ARR	19999 → 20ms = 50Hz（舵机标准频率）
Pulse	1500（初始 90°）
代码：
/* 角度函数：0~180 度 → 0.5~2.5ms 脉宽 */
void Servo_SetAngle(TIM_HandleTypeDef *htim, uint32_t channel, float angle)
{
    if (angle < 0)     angle = 0;
    if (angle > 180)   angle = 180;
    uint32_t ccr = 500 + (uint32_t)(angle / 180.0f * 2000);  // 500~2500 μs
    __HAL_TIM_SET_COMPARE(htim, channel, ccr);
}

/* main 里 */
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);

while (1)
{
    Servo_SetAngle(&htim3, TIM_CHANNEL_1, 0);     HAL_Delay(1000);
    Servo_SetAngle(&htim3, TIM_CHANNEL_1, 90);    HAL_Delay(1000);
    Servo_SetAngle(&htim3, TIM_CHANNEL_1, 180);   HAL_Delay(1000);
}
注意：

不同舵机脉宽范围略有差异（有的 1~2ms），实际角度不准就微调 500 和 2000 这两个数校准。
舵机需要 5V 供电且电流较大，别用 STM32 板载 3.3V 供电，会拉低电压导致复位。



、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、


项目三：蜂鸣器发声（改频率）
重要前提：必须用无源蜂鸣器（两脚、没有内置震荡电路）。有源蜂鸣器只要通电就响，PWM 只能控制音量不能控音调。

接线：PA6（TIM3_CH1）→ 三极管驱动 → 无源蜂鸣器（蜂鸣器电流大，别直接接 IO 口）

CubeMX 参数：

参数	值
PSC	71（F103）/ 83（F407）→ 1MHz
ARR	任意（运行时改）
Pulse	0
代码：


/* 播放指定频率：固定 PSC=1MHz，只改 ARR */
void Buzzer_Play(TIM_HandleTypeDef *htim, uint32_t channel, uint32_t freq)
{
    uint32_t arr = 1000000 / freq - 1;              // 1MHz / 频率
    __HAL_TIM_SET_AUTORELOAD(htim, arr);
    __HAL_TIM_SET_COMPARE(htim, channel, arr / 2);  // 50% 占空比
    __HAL_TIM_SET_COUNTER(htim, 0);
}

/* 简单音符频率表（Hz）：中音 do~高音 do */
static const uint16_t notes[] = {262, 294, 330, 349, 392, 440, 494, 523};
/*这些数字是声音的频率（单位 Hz，赫兹），每个数字对应一个音阶（音符）。蜂鸣器按这个频率振动，就发出对应音高的声音。

逐个对应音符
数组下标	数值(Hz)	音符
0	262	中音 do
1	294	re
2	330	mi
3	349	fa
4	392	sol
5	440	la
6	494	si
7	523	高音 do
几个要点
1. 频率越高，音调越高

262Hz（do）声音低，523Hz（高音 do）声音高，正好差一倍（八度）。
2. 440Hz 是"国际标准音"

440Hz 就是标准音 A4（钢琴中央 C 上面的那个 la），全世界乐器调音都以它为基准。所以你看到 440 就知道它是 la。
3. 这是"中音区"的 do re mi fa sol la si do

从 262 到 523，正好一个八度，够播简单儿歌（小星星、两只老虎这类）。
它怎么被用上
看蜂鸣器项目的代码，notes[] 是配合 melody[] 一起用的：


static const uint16_t notes[] = {262, 294, 330, 349, 392, 440, 494, 523};
static const uint8_t  melody[] = {0,0,4,4,5,5,4, 3,3,2,2,1,1,0};  // 存"下标"

// melody 里的 0 → notes[0] = 262 → 发 do 的音
// melody 里的 4 → notes[4] = 392 → 发 sol 的音
Buzzer_Play(&htim3, TIM_CHANNEL_1, notes[melody[i]]);
melody[] 存的是**"第几个音"（下标）**，不是频率本身；
真正播的时候用 notes[melody[i]] 查出实际频率，再交给 Buzzer_Play 去改定时器 ARR。
为什么要分开存
因为一首歌会重复出现很多相同的音，用下标表示更省空间、更好改：

想改整首歌音调高低 → 只改 notes[] 里的数值；
想改旋律顺序 → 只改 melody[] 里的下标。*/
/* 小星星旋律：do do sol sol la la sol ... */
static const uint8_t  melody[] = {0,0,4,4,5,5,4, 3,3,2,2,1,1,0};

int main(void)
{
    /* ... 初始化 ... */
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);

    while (1)
    {
        for (int i = 0; i < sizeof(melody); i++)//for 循环这些数字
        {
            Buzzer_Play(&htim3, TIM_CHANNEL_1, notes[melody[i]]);
            HAL_Delay(300);                          // 每个音持续 300ms
        }
        HAL_Delay(1000);                             // 一段后停 1s
    }
}
效果：循环播放小星星旋律。改 notes 数组就能换曲。


、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、、


项目四：RGB 灯调色（三通道 PWM）
接线（共阴 RGB 灯，F103 引脚）：
颜色	引脚
R 红	PA6（TIM3_CH1）
G 绿	PA7（TIM3_CH2）
B 蓝	PB0（TIM3_CH3）
CubeMX 参数：TIM3 的 CH1/CH2/CH3 三个通道都设 PWM Generation：

参数	值
PSC	71 / 83
ARR	255（这样 CCR 直接 = 0~255 亮度，8 位）
Pulse	0
代码：


/* 设置 RGB 颜色，r/g/b 都是 0~255（0=灭，255=最亮） */
void RGB_Set(uint8_t r, uint8_t g, uint8_t b)
{
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, r);
/*__HAL_TIM_SET_COMPARE	HAL 宏：把值写进 CCR 寄存器
&htim3	操作 TIM3 定时器
TIM_CHANNEL_1	通道 1（在 RGB 里对应红色 R）
r	写入的值 = 红色亮度（0~255）*/
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_2, g);
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_3, b);
}

/* HSV 转 RGB（h:0~360, s/v:0~1），用来做彩虹渐变 */
void RGB_SetHSV(float h, float s, float v)
{
    int   i = (int)(h / 60.0f) % 6;
    float f = h / 60.0f - (int)(h / 60.0f);
    float p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
    float r, g, b;
    switch (i) {
        case 0: r=v; g=t; b=p; break;  case 1: r=q; g=v; b=p; break;
        case 2: r=p; g=v; b=t; break;  case 3: r=p; g=q; b=v; break;
        case 4: r=t; g=p; b=v; break;  default:r=v; g=p; b=q; break;
    }
    RGB_Set((uint8_t)(r * 255), (uint8_t)(g * 255), (uint8_t)(b * 255));
}

/* main 里 */
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_2);
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_3);

while (1)
{
    for (float h = 0; h < 360; h += 1)   // 色相转一圈 = 彩虹渐变
    {
        RGB_SetHSV(h, 1.0f, 1.0f);
        HAL_Delay(10);
    }
}
注意：

共阳 RGB 灯是"低电平亮"，要把值反过来：__HAL_TIM_SET_COMPARE(..., 255 - r)。
三路各接 220Ω 限流电阻。

、*******************************************************************
给项目加按键
懂了，你要的是通用的"给项目加按键"的标准流程，不是蜂鸣器那一个例子。给你一套以后任何项目都能套用的方法。

总流程：4 步

① 接线 → ② CubeMX 配置 → ③ 写按键扫描函数 → ④ 主循环里用
① 接线：两种方式选一种
方式 A：上拉（推荐，最简单）

GPIO ── 按键 ── GND
（GPIO 内部上拉）
松开 = 读 1，按下 = 读 0；
不用外接电阻，用 GPIO 内部上拉即可。
方式 B：下拉

VCC ── 按键 ── GPIO
（GPIO 内部下拉）
松开 = 读 0，按下 = 读 1。
两者逻辑相反，选一种记住即可。新手用方式 A（上拉），按下读 0，最常见。

② CubeMX 通用配置
选一个空闲引脚（如 PA0、PB1），设为 GPIO_Input；
GPIO Pull-up/Pull-down 选 Pull-up（对应方式 A）；
生成代码。完事。
③ 通用按键扫描函数（核心，可复用）
这个函数解决两件事：消抖 + 只在上手瞬间触发一次（边沿检测）。

/* 通用按键扫描：检测"按下瞬间"，按下返回 1，否则返回 0 */
uint8_t Key_Scan(GPIO_TypeDef *port, uint16_t pin)
{
    static uint8_t last = GPIO_PIN_SET;   // 记录上次电平，初始为松开

    uint8_t now = HAL_GPIO_ReadPin(port, pin);

    if (now == GPIO_PIN_RESET && last == GPIO_PIN_SET)  // 上次松开、这次按下 = 按下沿
    {
        HAL_Delay(20);                                   // 消抖
        if (HAL_GPIO_ReadPin(port, pin) == GPIO_PIN_RESET)
        {
            last = now;
            return 1;                                    // 确认按下一次
        }
    }
    last = now;
    return 0;
}
关键点：static uint8_t last 记录上次电平，这样按住不动时不会一直返回 1，只在"从松开→按下"的那一瞬间返回一次 1。

④ 主循环里怎么用
/**********************************************************************/
while (1)
{
    if (Key_Scan(GPIOA, GPIO_PIN_0))   // PA0 被按了一下
    {
        // 这里写"按键要触发的事"
        HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);  // 比如翻转一个 LED
    }
}
按一下，触发一次，LED 翻转一次。不会因为按住而疯狂触发。
先写有关按键的函数 再在主函数调用



