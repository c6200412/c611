> 把「FreeRTOS 是什么 / CubeMX 怎么配 / Keil 编译报错怎么修 / 一键脚本怎么用」四段内容重新按**上手顺序**编排。 阅读顺序即操作顺序：先懂概念 → 再配 CubeMX → 再写任务 → 最后解决 AC6 编译。

---

## 目录

- 0. 一页纸速查
- 1. FreeRTOS 是什么
- 2. 八个核心概念
- 3. 调度机制与中断红线
- 4. CubeMX 配置流程（6 步）
- 5. 任务代码怎么写（含 3 个坑）
- 6. Keil 用 AC6 的三个必踩问题
- 7. 一键修复脚本
- 8. 收工检查清单

---

## 0. 一页纸速查

|场景|记住这一句|
|---|---|
|什么是 FreeRTOS|让单核单片机「看起来同时」干多件事的调度系统|
|延时用什么|任务里用 `osDelay()`，**绝不用 `HAL_Delay()`**|
|中断里用什么|只能用带 `FromISR` 后缀的 API|
|CubeMX 加任务在哪|`Middleware → FREERTOS → Tasks and Queues → Add`|
|业务代码写在哪|`Core/Src/freertos.c` 里各任务入口函数的 `for(;;)`|
|Keil 编译报 `__forceinline`|CubeMX 给的是 RVDS(AC5) 移植层 → 换 **GCC** 移植层|
|Keil 报 AC5 不可用|目标编译器被设回 AC5 → 选回 **AC6**（`uAC6=1`）|
|报 `unable to open output file`|路径含全角字符 → 全改纯英文|

**核心一句话：Keil 用 AC6，FreeRTOS 就必须用 GCC 移植层，且工程路径要纯英文。**

---

## 1. FreeRTOS 是什么

实时操作系统（RTOS），跑在单片机上，让一颗单核芯片能「看起来同时」干好几件事。

||没有 RTOS|有 RTOS|
|---|---|---|
|结构|主循环 `while(1)` 里一件件按顺序干|工作拆成多个「任务」，调度器按优先级轮流跑|
|后果|一件事卡住，后面全卡|任务互不拖累|

---

## 2. 八个核心概念

|概念|是什么|一句话理解|
|---|---|---|
|任务 Task|一段独立运行的函数，有自己的栈|一个「工人」|
|调度器 Scheduler|决定哪个任务此刻运行|「工头」|
|优先级 Priority|数字越大越优先|谁重要谁先干|
|阻塞 / 延时|任务暂停，让出 CPU（`osDelay` / `vTaskDelay`）|工人去休息，别人接着干|
|队列 Queue|任务之间传数据的管道|传送带|
|信号量 Semaphore|任务间同步 / 发信号|旗语 / 握手|
|互斥锁 Mutex|保护共享资源，防止多个任务同时改|一把锁，只能一人拿|
|软件定时器 Timer|到点自动回调一个函数|闹钟|

> 名字对应：CMSIS-RTOS2 封装版叫 `osDelay` / `osMessageQueue` / `osSemaphore`…，底层就是 `vTaskDelay` / `xQueueSend` / `xSemaphoreTake`。你工程里是 CMSIS_V2，所以写 `osXxx` 为主。

---

## 3. 调度机制与中断红线

**两个机制**

- **抢占**：高优先级任务就绪，立刻抢走 CPU。
- **时间片**：同优先级任务按 tick 轮流跑。

**两条红线**

1. 中断服务函数里**只能**用带 `FromISR` 后缀的 API（如 `xQueueSendFromISR`），不能用会阻塞的 API。
2. 任务里**不能**用 `HAL_Delay()`（忙等，会把整个任务乃至低优先级任务一起卡死）。

---

## 4. CubeMX 配置流程（6 步）

### 4.1 启用

`Middleware → FREERTOS`，把 **Interface 选成 `CMSIS_V2`**（推荐；即 `cmsis_os2.c`，你工程里就是它）。

### 4.2 常用配置（Config Parameters）

|参数|含义|建议|
|---|---|---|
|`TICK_RATE_HZ`|系统心跳频率，默认 1000（1 ms 一次），决定延时最小单位|先用默认 1000|
|`Total Heap Size`|RTOS 内存池大小，任务/队列/信号量都从这扣|不够会「创建失败」，加任务后记得回头调大|

### 4.3 加任务（最重要）

`Tasks and Queues` 标签 → `Add`：

|参数|含义|
|---|---|
|Task Name|任务名（字符串，调试用）|
|Priority|优先级，`osPriorityNormal` 是普通档|
|Stack Size|任务栈大小（单位是**字**，1 字 = 4 字节；不够就栈溢出）|
|Entry Function|任务入口函数名，CubeMX 自动生成，你的代码写这里|
|Allocation|一般 `Dynamic`（从 Heap 里分）|

### 4.4 加队列 / 信号量 / 定时器

同一个 `Tasks and Queues` 标签里可加 Queue、Semaphore、Timer，CubeMX 会一并生成创建代码（也在 `freertos.c` 的 `MX_FREERTOS_Init()` 里）。

### 4.5 生成代码后你会看到

|文件|内容|
|---|---|
|`Core/Src/freertos.c`|默认任务 `StartDefaultTask` 和所有任务入口函数，**业务代码写这里**|
|`Core/Inc/FreeRTOSConfig.h`|RTOS 配置（心跳、堆大小、功能开关）|
|`MDK-ARM/*.uvprojx`|Keil 工程，FreeRTOS 的 include 路径和 `port.c` 引用都在这里|

> 附带现象：CubeMX 默认把 `SYS → Timebase Source` 换成 **TIM**，因为 SysTick 被 FreeRTOS 拿去当心跳了——这就是你工程里多出 `stm32f1xx_hal_timebase_tim.c` 的原因。**这是正常的，不用改。**

---

## 5. 任务代码怎么写（含 3 个坑）

CubeMX 生成的入口长这样，你在 `for(;;)` 里写业务：

c

```
void StartDefaultTask(void *argument)
{
    for(;;)
    {
        // 你的代码
        osDelay(100);   // RTOS 延时 100 ms，期间让出 CPU
    }
}
```

|坑|说明|正确做法|
|---|---|---|
|用 `HAL_Delay()`|忙等，卡死整个任务|用 `osDelay()`|
|任务栈给小了|局部数组/递归一大就栈溢出，表现为莫名 HardFault|栈按需调大，或把大缓冲区放 `static`|
|忘了让出 CPU|`for(;;)` 里不延时，同优先级任务饿死|每轮至少 `osDelay(1)` 或阻塞在队列/信号量上|

---

## 6. Keil 用 AC6 的三个必踩问题

### 问题 1：工程名/路径有全角字符 → 打不开输出文件

- **现象**：`unable to open output file`，路径里出现乱码 `p1<A1><AA><A1><AA>free/xxx.o`，以及 `unable to convert command-line to UTF-16`。
- **原因**：工程名 `p1——free` 里的 `——` 是**全角破折号**，ARM Compiler 6（ARMCLANG）不支持非 ASCII 路径。
- **修法**：工程名、目标名、**整个路径**全部改成纯英文/数字/下划线（如 `p1_free`）。

### 问题 2：FreeRTOS 用了 AC5 的移植层，但编译器是 AC6

- **现象**：`unknown type name '__forceinline'`、`__asm`、`__dsb/__isb/__clz` 未声明、`ulPortRaiseBASEPRI` undeclared，一堆错误。
- **原因**：CubeMX 给 MDK-ARM 生成的是 **RVDS（AC5）版** FreeRTOS 移植层（用 `__forceinline`、`__asm {}` 等 AC5 专有语法），而你的 Keil 是 **AC6（ARMCLANG）**，两者不匹配。
- **修法**：把移植层换成 **GCC 版**（ARMCLANG 走 GCC/Clang 语法）：
    - 拷入 `portable/GCC/ARM_CM3/{port.c, portmacro.h}`（V10.3.1）
    - `.uvprojx` 里 3 处 `portable/RVDS/ARM_CM3` → `portable/GCC/ARM_CM3`

### 问题 3：编译器版本被设成了 AC5，而 AC5 没装

- **现象**：`Target uses ARM-Compiler 'Default Compiler Version 5' which is not available`。
- **原因**：目标编译器被设回默认 AC5，但机器上只有 **AC6（V6.24）**，AC5 不存在。
- **修法**：`Options for Target → Target → ARM Compiler` 选回 AC6；或在 `.uvprojx` 里把 `<uAC6>0</uAC6>` 改成 `<uAC6>1</uAC6>`。

### 三者关系

代码块

```
CubeMX 生成 (RVDS 移植层) ──→ Keil 用 AC6 编译 ──→ 不匹配 ✗
                                    │
                    换 GCC 移植层 + 选 AC6 + 纯英文路径
                                    │
                                    ▼
                               编译通过 ✓
```

---

## 7. 一键修复脚本

**位置**：`D:\keil_temp\freertos_ac6_fix\fix_freertos_ac6.sh`（同目录下还有 `GCC/ARM_CM3/` 两个待拷贝文件）

**前提**：工程得是 **CubeMX 标准布局**（有 `MDK-ARM/*.uvprojx` 和 `Middlewares/Third_Party/FreeRTOS/`），否则脚本会直接报错退出。

### 7.1 用法

**必须用 Git Bash 跑**（不是 CMD / PowerShell）。

1. 在 `D:\keil_temp\freertos_ac6_fix` 文件夹里右键 → **Git Bash Here**；或开始菜单搜 "Git Bash"。
2. 粘贴运行（把路径换成你的工程路径）：

bash

```
cd /d/keil_temp/freertos_ac6_fix && ./fix_freertos_ac6.sh "/d/keil_temp/myproject"
```

3. 脚本会打印三步结果：

代码块

```
[1/3] 已拷入 GCC 版 port.c + portmacro.h
[2/3] 已把编译器切到 AC6 (uAC6=1)
[3/3] 已替换 portable/RVDS/ARM_CM3 -> portable/GCC/ARM_CM3
```

> 第 2、3 步是**幂等**的：已经是 AC6 或已经没有 RVDS 引用时会打印「跳过」，不会报错。

### 7.2 跑完之后

1. 在 Keil 里**关掉并重新打开**这个工程（重要：Keil 不会自动重读磁盘上改过的 `.uvprojx`）。
2. `Project → Clean Targets` → `Rebuild`。

### 7.3 参数与写法说明

|情况|写法|
|---|---|
|指定工程路径|`./fix_freertos_ac6.sh "/d/keil_temp/myproject"` → Git Bash 风格|
|同上（Windows 风格）|`./fix_freertos_ac6.sh "D:/keil_temp/myproject"` → 也行|
|路径有空格|必须加引号，如 `"/d/keil_temp/my project"`|
|不传参数|直接 `cd` 到工程根目录后 `./fix_freertos_ac6.sh`，它把**当前目录**当工程目录|

### 7.4 脚本内部干了什么（想手工修时照这个来）

1. 校验脚本自带的 `GCC/ARM_CM3/port.c`、`portmacro.h` 存在；
2. 在 `<工程>/MDK-ARM` 下找 `.uvprojx`（找不到就退出，说明路径给错了）；
3. 拷 `port.c` + `portmacro.h` 到 `<工程>/Middlewares/Third_Party/FreeRTOS/Source/portable/GCC/ARM_CM3/`；
4. `.uvprojx` 里 `<uAC6>0</uAC6>` → `<uAC6>1</uAC6>`；
5. `.uvprojx` 里所有 `portable/RVDS/ARM_CM3` → `portable/GCC/ARM_CM3`（共 3 处：2 个 include 路径 + 1 个 port.c 文件引用）。

### 7.5 它**不**管什么

- 不修**全角路径**（问题 1 得手工重命名工程）；
- 不动你 `freertos.c` 里的业务代码；
- 不重新生成 `FreeRTOSConfig.h`。

---

## 8. 收工检查清单

- [ ]  工程路径、工程名、目标名全是英文/数字/下划线
- [ ]  `Options for Target → Target → ARM Compiler` 是 **AC6**
- [ ]  工程树里 FreeRTOS 的 `port.c` 指向 `portable/GCC/ARM_CM3`
- [ ]  `Middlewares/.../portable/GCC/ARM_CM3/port.c` 与 `portmacro.h` 存在（AC6 版）
- [ ]  任务里延时全用 `osDelay()`，没有 `HAL_Delay()`
- [ ]  中断里只调 `FromISR` 版本 API
- [ ]  `Total Heap Size` 够用（加任务后复检一次）
- [ ]  改完 `.uvprojx` 后**重启 Keil**，再 Clean → Rebuild