在 STM32CubeMX + HAL 里用 FreeRTOS，关键是把**三套“优先级”分清楚**，然后记住“**任务优先级数字大 = 更急，中断优先级数字小 = 更急**”。

## 一、先分清三套优先级

|体系|在哪配|规则|例子|
|---|---|---|---|
|**FreeRTOS 任务优先级**|CubeMX 的 FREERTOS 任务表 / `osThreadNew`|**数字越大越优先**，0 是最低（IDLE）|控制任务 5、通信 3、日志 1|
|**NVIC 中断优先级**|CubeMX 的 NVIC 页 / `HAL_NVIC_SetPriority`|**数字越小越优先**（Cortex-M 硬件规则）|CAN 接收优先级 5（比 6 高）|
|**HAL 时基**|SYS → Timebase Source|默认 SysTick，用 FreeRTOS 时要让出|改成 TIM6|

## 二、CubeMX 配置（5 步）

1. **Middleware → FREERTOS**，Interface 选 **CMSIS_V2**。
2. **Config parameters** 里确认：
    - `configUSE_PREEMPTION = 1`（抢占式调度，**核心开关**）
    - `configUSE_TIME_SLICING = 1`（同优先级轮转，一般开）
    - `configMAX_PRIORITIES = 56`（CMSIS-V2 默认，够 osPriority 用）
    - `configTICK_RATE_HZ = 1000`（1 ms 一个 tick）
    - `configUSE_MUTEXES = 1`（要用互斥量就开）
3. **Tasks and Queues** 页里加任务：名字、入口函数、栈大小（字，不是字节）、优先级。
4. **SYS → Timebase Source** 改成 **TIM6**（或任意空闲定时器）——**这步最容易漏**。
5. 生成代码。

## 三、生成的代码长什么样

`Core/Src/freertos.c` 里：

c

```
void MX_FREERTOS_Init(void)
{
    /* 默认任务 */
    defaultTaskHandle = osThreadNew(StartDefaultTask, NULL, &defaultTask_attributes);

    /* 你加的任务：优先级在 attributes 里 */
    controlTaskHandle = osThreadNew(StartControlTask, NULL, &controlTask_attributes);
}

void StartControlTask(void *argument)
{
    for (;;)
    {
        // 业务代码
        osDelay(10);   // 让出 CPU 10 ms（必须用 osDelay，不是 HAL_Delay）
    }
}
```

任务属性里：

c

```
const osThreadAttr_t controlTask_attributes = {
    .name = "control",
    .priority = (osPriority_t)osPriorityHigh,   // 数字大 = 更急
    .stack_size = 256 * 4,                      // 256 字 = 1 KB
};
```

CMSIS-V2 的优先级枚举（实际映射到数字）：

|枚举|大致数值|用途|
|---|---|---|
|`osPriorityLow`|8|日志、LED|
|`osPriorityNormal`|24|普通业务|
|`osPriorityAboveNormal`|32|通信|
|`osPriorityHigh`|40|控制、安全|
|`osPriorityRealtime`|48+|极少用，别乱给|

## 四、抢占式调度的实际表现

c

```
void StartHighTask(void *arg)   // 优先级 osPriorityHigh
{
    for (;;) {
        LED_HIGH();        // 高优先级一醒就抢
        osDelay(100);
    }
}

void StartLowTask(void *arg)    // 优先级 osPriorityLow
{
    for (;;) {
        LED_LOW();
        osDelay(10);       // 每 10ms 让出一次
    }
}
```

- 高优先级任务 `osDelay` 期间，低优先级任务能跑；
- 高优先级任务的延时一到，**立刻抢占**低优先级任务（不等它 `osDelay`）；
- 两个任务**同优先级**时，按 tick 轮转（各跑 1 ms）。

运行时改优先级：

c

```
osThreadSetPriority(controlTaskHandle, osPriorityRealtime);
```

## 五、中断里怎么和 FreeRTOS 配合（CAN 就用这个）

c

```
// CAN 接收中断回调（HAL 里是 HAL_CAN_RxFifo0MsgPendingCallback）
void HAL_CAN_RxFifo0MsgPendingCallback(CAN_HandleTypeDef *hcan)
{
    BaseType_t hpw = pdFALSE;
    CAN_RxHeaderTypeDef rx;
    uint8_t buf[8];
    HAL_CAN_GetRxMessage(hcan, CAN_RX_FIFO0, &rx, buf);  // 中断里只取帧
    xSemaphoreGiveFromISR(canRxSem, &hpw);               // 通知任务
    portYIELD_FROM_ISR(hpw);                             // 需要时立刻切任务
}

// 处理任务
void StartCanTask(void *arg)
{
    for (;;) {
        if (osSemaphoreAcquire(canRxSem, osWaitForever) == osOK) {
            // 这里再做解析、回帧，耗时的活都放这
        }
    }
}
```

CubeMX 里把 **CAN 中断的 NVIC 优先级设成 ≥ `configMAX_SYSCALL_INTERRUPT_PRIORITY` 对应的数值**（即“逻辑优先级不高于”它），否则 `FromISR` API 会断言失败。

## 六、最容易踩的五个坑

1. **用了 `HAL_Delay()`**：它靠 SysTick，而 SysTick 被 FreeRTOS 接管后，`HAL_Delay` 会一直等不到 tick 或行为异常。**任务里一律用 `osDelay()`**；且 SYS Timebase 改 TIM6 后 `HAL_Delay` 才恢复正常（基于 TIM6）。
2. **中断里调阻塞 API**：`osDelay`、`osMutexAcquire(osWaitForever)` 在 ISR 里会死锁。中断里只能用 `...FromISR` 版本。
3. **栈太小**：CubeMX 默认 128 字，函数里开大数组/printf 直接 HardFault。先用 512~1024 字，再按需调。
4. **优先级反转**：低优先级任务拿着 mutex 不放，高优先级干等。用 `osMutexNew()`（带优先级继承），别用二值信号量当锁。
5. **`taskENTER_CRITICAL()` 关太久**：会把所有中断（包括 CAN 接收）堵住，丢帧。临界区只放几条指令。

## 七、一句话总结用法

**CubeMX 里开 `configUSE_PREEMPTION=1`，任务表里按“越急数字越大”给优先级，时基换成 TIM6，任务里用 `osDelay`，中断里用 `...FromISR` + 信号量唤醒任务**——这就是 HAL + FreeRTOS 抢占式调度的标准套路，CAN 收发任务也照这个模式写。

需要的话，我可以直接在工作区生成一份 `freertos_can_demo.c`（含任务创建、信号量、CAN 中断回调、优先级配置注释），你贴进 CubeMX 工程就能编译。

是不是自己就说他的优先级是事先固定好的

已完成已完成，用时 5秒

对，本质上是“**事先定好**”的，但要分清是哪种“定”：

## 你这份代码：创建时写死（静态）

c

```
const osThreadAttr_t defaultTask_attributes = {
  .priority = (osPriority_t) osPriorityNormal,   // 编译期常量
};
```

- `const` 表示这个属性结构体放在只读区，**编译时就固定了**；
- `osThreadNew()` 创建任务时，把 `.priority` **拷进任务的 TCB**，从此这个任务就按这个值参与调度；
- 调度器**不会自动帮你调**——FreeRTOS 没有“按负载动态调优先级”“老化提升”这类策略，优先级是**设计时决定的策略**，不是运行时算出来的。

## 但它不是“永久不能变”

运行中可以主动改：

c

```
osThreadSetPriority(defaultTaskHandle, osPriorityHigh);   // 立即生效
// 或原生 API：vTaskPrioritySet(defaultTaskHandle, 5);
```

所以准确说法是：**默认值在创建时固定，运行时可以主动修改，但没人会自动改它。**

## 唯一的“自动变化”：优先级继承

只有一种情况 FreeRTOS 会临时动优先级：**mutex 的优先级继承**。低优先级任务持有锁时，会被临时提升到等锁任务的优先级，释放后再降回去——这只是防止优先级反转，不改变你的设计意图。

## 一句话

**优先级是“创建时写死的默认值 + 运行时只能手动改”，调度器自己不会动态调整；所以优先级规划（谁该高、谁该低）必须在写代码/配 CubeMX 时就定好，属于设计决策，不是运行时行为。**

用量 69.9K tok20:22

如果想要更改它的标签级，是不是只能在Co max更改

20:23

已完成已完成，用时 5秒

不，你还有三种改法。CubeMX 只是最正规的一种：

## 三种方式

|方式|怎么改|生效|会不会被覆盖|
|---|---|---|---|
|**① CubeMX（.ioc）**|`FREERTOS → Tasks and Queues` 里改 Priority 列 → 重新 Generate|重新生成后|不会，这是“源头”|
|**② 直接改代码**|改 `main.c` 里 `const osThreadAttr_t` 的 `.priority` 那一行|编译下载即生效|**会被覆盖**——这段在 USER CODE 区外，下次 Generate 就还原|
|**③ 运行时 API**|`osThreadSetPriority(handle, osPriorityHigh);` 或 `vTaskPrioritySet(handle, 5);`|调用瞬间生效|不会（但有条件，见下）|

## 怎么选

- **长期/项目定稿**：用 ①，改在 CubeMX 里，重新生成后代码、注释、任务表都一致，别人接手也看得懂。
- **调试时临时试**：用 ②，改一行编译一次，最快，但记住**别在 Generate 前手改**，否则白改。
- **运行中按条件变**：用 ③，比如“检测到故障就把 CAN 任务提为最高”。注意：
    - 只能改**已创建**的任务，句柄要有效；
    - 不要在中断里调（用 `...FromISR` 没有这个 API，得发消息给任务去改）；
    - 频繁改优先级会打乱调度，别滥用。

## 一个提醒

`main.c` 里那段 `defaultTask_attributes` 是 **CubeMX 生成区**（不在 `USER CODE BEGIN/END` 之间），手改后一旦重新生成就被覆盖——这是最常见的“改了没保存住”的原因。想手改又想保留，就把它挪进 `USER CODE` 区，或者干脆只在 CubeMX 里改。

一句话：**不是只能在 CubeMX 改——可以改代码、也可以运行时用 API 改；但要让改动长期保留、不被重新生成冲掉，最稳妥的是在 CubeMX 里改。**