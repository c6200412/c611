pwm
下面按 STM32 的 PWM 用法给你一份尽量完整的讲解，以 HAL 库为主（最常用），最后补充寄存器级操作和高级定时器特性。所有代码假设你用 STM32F1/F4 系列，用 CubeMX 生成工程。

一、PWM 是怎么产生的
STM32 的 PWM 本质是定时器 + 比较寄存器配合产生的方波：

定时器从 0 向上计数到 ARR（自动重装载值），然后回 0，形成一个周期；
计数器 CNT 每走一个时钟周期都和 CCRx（捕获/比较寄存器）比一次；
根据比较结果控制输出引脚的电平，就得到了 PWM。
核心三个寄存器：

寄存器	作用
PSC（预分频）	把定时器时钟降频
ARR（自动重装载）	决定周期（频率）
CCRx（比较值）	决定占空比
二、频率和占空比的计算公式

定时器计数频率   = TimerClock / (PSC + 1)
PWM 频率        = 计数频率 / (ARR + 1)
               = TimerClock / ((PSC + 1) × (ARR + 1))

占空比 = CCRx / (ARR + 1)   （PWM 模式 1，向上计数时）
注意都是 +1：因为寄存器的值是"减 1"编码的，PSC=0 表示不分频，ARR=999 表示计 1000 个数。这是新手最容易算错的地方。

举例：STM32F4 定时器时钟 84 MHz，想要 1 kHz PWM、占空比 50%：

取 PSC = 84 - 1 = 83 → 计数频率 = 84 MHz / 84 = 1 MHz
取 ARR = 1000 - 1 = 999 → PWM 频率 = 1 MHz / 1000 = 1 kHz
占空比 50% → CCRx = (ARR+1) × 50% = 500
三、PWM 模式 1 和模式 2 的区别
在向上计数（默认）下：

模式	输出有效电平的条件	占空比
PWM 模式 1	CNT < CCRx 时输出有效	CCRx / (ARR+1)
PWM 模式 2	CNT > CCRx 时输出有效	(ARR+1 - CCRx) / (ARR+1)
绝大多数情况用 模式 1（TIM_OCMODE_PWM1），CCRx 越大占空比越大，直观。


/***********************cubmx  配置*****************************/
以 TIM3 的 CH1（PA6） 输出 PWM 为例：

RCC：选好时钟源，记下你要用的定时器时钟（F103 的 APB1 定时器是 72 MHz，F407 的 APB1 是 84 MHz）。
选择定时器：左侧 Timers → TIM3，把 Clock Source 设为 Internal Clock，Channel1 设为 PWM Generation CH1。
设置参数（在 Configuration 里）：
Prescaler (PSC)：按上面公式算；
Counter Period (ARR)：按上面公式算；
Pulse (CCR)：初始占空比对应的值；
CH Polarity：High（高电平有效）；
PWM Mode：PWM Mode 1。
引脚：确认 PA6 自动配置成了 TIM3_CH1 复用功能。
生成工程（记得勾选"生成 .c/.h"）。


/*******************************用法***************************/
五、HAL 库完整代码
1. 启动 PWM/* 放在 MX_TIM3_Init() 之后、主循环之前 */
/* 放在 MX_TIM3_Init() 之后、主循环之前 */
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);   // 启动 TIM3_CH1 的 PWM
启动后 PA6 立刻输出你在 CCR 里设的固定占空比方波。

2. 动态改变占空比
两种方式，推荐第一种（只改 CCR，不动其它配置，最安全）
/* 方式 A：直接设比较值（推荐，高效） */
__HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, 250);   // CCR = 250

/***************************************************************************/

/* 方式 B：重新配置通道（会顺带重置一些标志，稍慢） */
TIM_OC_InitTypeDef sConfigOC = {0};
sConfigOC.OCMode     = TIM_OCMODE_PWM1;
sConfigOC.Pulse      = 250;                 // 新的 CCR
sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
HAL_TIM_PWM_ConfigChannel(&htim3, &sConfigOC, TIM_CHANNEL_1);
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);   // 改完需要重新 Start

/***********************************************************************/


重中之中
3. 用函数封装占空比（0~100%）

void PWM_SetDuty(TIM_HandleTypeDef *htim, uint32_t channel, float duty_percent)
{
    // duty_percent: 0.0 ~ 100.0
    uint32_t arr = __HAL_TIM_GET_AUTORELOAD(htim);        // 读 ARR
    uint32_t ccr = (uint32_t)((duty_percent / 100.0f) * (arr + 1));
    __HAL_TIM_SET_COMPARE(htim, channel, ccr);
}

调用之前要先启动 PWM
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);   // 先启动
PWM_SetDuty(&htim3, TIM_CHANNEL_1, 50);     // 再调占空比才有意义

例子；
int main(void)
{
    /* CubeMX 自动生成的初始化代码 */
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM3_Init();

    /* USER CODE BEGIN 2 */              // ← 这里写"初始化后只执行一次"的代码
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
    /* USER CODE END 2 */

    /* USER CODE BEGIN WHILE */          // ← 这里写循环体
    while (1)
    {
        PWM_SetDuty(&htim3, TIM_CHANNEL_1, 50);
        HAL_Delay(10);
    /* USER CODE END WHILE */
在这里写控制代码
    /* USER CODE BEGIN 3 */
    }
    /* USER CODE END 3 */
}

/************************************************************************/

4. 动态改变频率
改频率要改 PSC 或 ARR，且改完最好重新初始化定时器：
void PWM_SetFreq(TIM_HandleTypeDef *htim, uint32_t freq)
{
    // 先算：这里假设 PSC 保持不变，只调 ARR
    uint32_t timer_clk = HAL_RCC_GetPCLK1Freq() * 2;      // APB1 定时器×2，注意见下节
    uint32_t psc = __HAL_TIM_GET_PRESCALER(htim);
    uint32_t arr = timer_clk / ((psc + 1) * freq) - 1;
    __HAL_TIM_SET_AUTORELOAD(htim, arr);
    // CCR 也要按比例缩小，否则占空比会跑偏
}
这个问题问到点子上了——实际上大多数 PWM 场景你根本用不到这个函数。




/***************************两个函数的用法***************************/
先记住一句话
PWM 应用里，频率通常一次定死（CubeMX 里配好），运行中只改占空比。改频率是少数场景才需要。

什么时候不用 PWM_SetFreq（占绝大多数）
这些场景频率固定，你只需要 PWM_SetDuty：

应用	频率	运行中改什么
LED 呼吸灯	固定 1kHz	只改占空比（亮度）
舵机控制	固定 50Hz	只改占空比（角度）
电机调速	固定 10~20kHz	只改占空比（转速）
PWM 调压/调光	固定	只改占空比
这些里，频率一旦在 CubeMX 设好就不再动，所以 PWM_SetFreq 一行都不用写。
/*****************************************************Yong***************/
什么时候才需要 PWM_SetFreq（少数）
1. 蜂鸣器/喇叭发声（最常见）
不同频率 = 不同音调。播音乐、报警音，就是不断调 PWM_SetFreq 改变音高：


PWM_SetFreq(&htim3, 440);   // 发 A4 音（440Hz）
PWM_SetFreq(&htim3, 880);   // 发高八度 A5
2. 步进电机调速
某些方案里 PWM 频率直接对应步进速度，改变频率就是变速。

3. 扫频测试 / 仪器
需要输出一个频率范围连续变化的信号，测系统响应。

4. 调试时临时试不同频率
想看看某个电机/灯在多大频率下不啸叫、不闪烁，临时改频率找最佳值。

结论
你的项目如果只是调光、舵机、电机调速 → 只需要 PWM_SetDuty，不用管 PWM_SetFreq。
只有蜂鸣器发声、步进调速、扫频这类"频率本身是控制量"的场景 → 才用 PWM_SetFreq

ps;
三类代码，待遇完全不同
① CubeMX 已经生成的 —— 别贴，贴了必报错
MX_TIM3_Init()、HAL_TIM_PWM_MspInit()、GPIO 复用配置这些，CubeMX 生成工程时已经写进 main.c / tim.c / gpio.c 里了。你再贴一份，编译器报 multiple definition / redefinition。

这些你不用写、也不用贴，CubeMX 替你干完了。你要做的只是在 CubeMX 里点几下（选 TIM3 → PWM Generation → 设 PSC/ARR）。

② 要插进 main() 的一行 —— 贴在指定位置
就这一行，而且是插进 main() 函数体里（MX_TIM3_Init() 之后、while(1) 之前），不是贴整个文件：


int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM3_Init();                          // CubeMX 生成的，已存在

    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1); // ← 只贴这一行到这里
    PWM_SetDuty(&htim3, TIM_CHANNEL_1, 50);   // ← 你的函数，也在这里调用

    while (1) { }
}
③ 你自己写的辅助函数 —— 这才是真正要"添加"的
PWM_SetDuty、PWM_SetFreq、TIM_GetClockFreq 这些是你自己的代码，CubeMX 不会生成，需要你加进去。位置有两个选择：

简单：放在 main.c 里 main() 函数后面；
规范：新建 pwm.c / pwm.h，函数放 .c，声明放 .h，在用到的地方 #include "pwm.h"。
一句话总结
代码	谁负责	你的动作
MX_TIM3_Init / GPIO 配置	CubeMX	不贴，点几下就自动生成
HAL_TIM_PWM_Start	你	把这一行插入 main() 指定位置
PWM_SetDuty / PWM_SetFreq	你	添加到 main.c 后面或新建 pwm.c
所以真正的操作是：CubeMX 配好 → 生成工程 → 只往 main() 里插一行 Start + 加你自己的几个函数，而不是把教程代码整体拷进去。

之前我给的那些代码块，是给你"看懂每一段在干什么、放在哪"用的，不是让你整个文件覆盖进工程。要不要我按"在 main.c 里加函数"这个最简单的方式，给你一份直接照着插就能编译的完

