# ROS2 入门条目：六表 · 可跑版（v2）

> **版本说明**：v1（`ROS2三表_可跑版.md`，公共/机械臂/导航三表）已原样保留作为备份，本文件在其基础上增补。
> v2 新增：**表 D rqt 工具全家桶（14 件）**、**表 E 外设接入（串口 / 2D 雷达 / 深度相机 / IMU 经 STM32 / FishROS 小车）**、**表 F 数据与 bag 处理 + 点云 + 目标跟踪**。
> 本轮目标不变：**跑通一遍、看见链路、搭起框架**。不追求学懂、不追求调好、不改源码。

---

## 0. 三个目标的取舍（先定规则，再列条目）

| 三者关系 | 本轮怎么取 |
|---|---|
| **深度** | 让位。能用官方 demo 就不自己写；能 rviz 就不开 Gazebo；能 CLI 就不写代码 |
| **具体简明** | 优先。每条必须有可复制的命令或 ≤15 行伪代码；写不出命令的条目，说明还没具体到能执行 |
| **第一次成功率** | **最高优先**。试 5 次起不来 = 这条目作废，换更简单的路径 |

四条硬规则：① 能 rviz 就不 Gazebo（VMware 上 Gazebo 卡到没体验）；② 一条命令能起就不许写脚本；③ 跑不通允许跳过，验收表记"跳过"，不许为修它耗一天；④ 每条留一个"探索点"，3 分钟内能用一句话答。

**本轮明确不做**：不改源码、不调 PID/规划器参数到"好"、不手写完整 MoveIt 配置、不追精度、不训练模型（只做推理与前处理）。

环境标记：🟢 = VMware/普通笔记本可跑｜🟡 = 需 Gazebo 仿真（慢但能跑）｜⚪ = 需真设备（402 现场）

---

## 表 A｜公共底座（16 条，约 5 小时，全部 🟢）

| # | 条目 | 具体操作（命令 / 逻辑链） | 探索点 | 判据 | 时长·环境 |
|---|---|---|---|---|---|
| A1 | ROS2 CLI 体检 | `source /opt/ros/humble/setup.bash` → `ros2 --version` → `ros2 pkg list`（看包齐不齐） → `ros2 run demo_nodes_cpp talker`。逻辑链：装包→source→CLI→RMW 初始化 | 为什么必须 `source` 才能用 `ros2` 命令？ | 四条都出结果，talker 每秒打印 | 20 min 🟢 |
| A2 | 两终端 talker/listener | 终端1 `ros2 run demo_nodes_cpp talker`；终端2 `ros2 run demo_nodes_cpp listener`。逻辑链：发布 `/chatter` → DDS 发现 → 订阅回调 | listener 是怎么"找到" talker 的？谁做媒人？ | listener 持续打印 `I heard: [hello world N]` | 15 min 🟢 |
| A3 | rqt_graph 看节点图 | `ros2 run rqt_graph rqt_graph`，取消勾选 hide dead，看两个椭圆一条箭头 | 方框、箭头、箭头方向各代表什么？ | 截图并手标"节点/话题/发布方向" | 15 min 🟢 |
| A4 | DDS 域隔离（实验室必踩） | 两人同一 WiFi，`export ROS_DOMAIN_ID=7` 前后各跑 `ros2 node list`。逻辑链：同域=互相发现，异域=隔离 | 为什么我能看见别人的节点？这算 bug 吗？ | 截图对比 + 一句话解释 | 20 min 🟢 |
| A5 | topic 四连 | `ros2 topic list -t` → `ros2 topic echo /chatter --once` → `ros2 topic hz /chatter` → `ros2 topic info /chatter -v`（看 QoS） | `hz` 显示 10 而 `echo` 一行行刷，差在哪？ | 报出实测频率（约 10 Hz） | 20 min 🟢 |
| A6 | 自己发一条 topic | `ros2 topic pub --rate 1 /chatter std_msgs/msg/String "{data: hi}"`，观察 A2 的 listener | 你没写一行代码却成了发布者，说明什么？ | listener 打印出 `hi` | 15 min 🟢 |
| A7 | service vs action | `ros2 run demo_nodes_cpp add_two_ints_server` → `ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a:3,b:4}"`；再 `ros2 run action_tutorials_cpp fibonacci_action_server` → `ros2 action send_goal /fibonacci action_tutorials_interfaces/action/Fibonacci "{order:5}" --feedback` | 为什么机械臂要用 action 而不是 service？ | 看到 feedback 流；中途 Ctrl+C 后目标消失 | 25 min 🟢 |
| A8 | 参数三连 | `ros2 param list /talker` → `ros2 param get /talker use_sim_time` → `ros2 param set` → `ros2 param dump /talker` 存 yaml | 参数是"启动读一次"还是"改了立刻生效"？ | 导出一份 yaml，说清哪个参数改了有用 | 20 min 🟢 |
| A9 | launch 编排 | 写 `two.launch.py`：两个 `Node(package='demo_nodes_cpp',executable='talker')` + `DeclareLaunchArgument('rate',default_value='2')` | 两个同名节点同时起，会互相顶掉吗？ | `ros2 launch two.launch.py` 一条命令起两个 | 40 min 🟢 |
| A10 | TF 静态变换 | `ros2 run tf2_ros static_transform_publisher 1 2 0 0 0 0 base_link laser` → 另一终端 `ros2 run tf2_ros tf2_echo base_link laser` | 静态变换和动态变换，谁适合装传感器？ | 打印出 (1,2,0)，`view_frames` 里有这条边 | 20 min 🟢 |
| A11 | view_frames 画 TF 树 | `ros2 run tf2_tools view_frames`（需 graphviz）→ 打开 `frames.pdf` | 一棵 TF 树能有几个根？为什么？ | 指出树根节点名与层数 | 15 min 🟢 |
| A12 | URDF 在 rviz 里显示 | 写 12 行 URDF → `ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$(cat my.urdf)"` + `ros2 run joint_state_publisher_gui joint_state_publisher_gui` + `rviz2`（Fixed Frame 设 base_link） | 模型为什么"不动"？谁在改 joint 值？ | 拖滑块，模型跟着转 | 40 min 🟢 |
| A13 | rosbag2 录与放 | `ros2 bag record -o a /chatter`（Ctrl+C 停）→ `ros2 bag info a` → `ros2 bag play a --rate 2`，另开 listener | 回放时"发布者"是谁？它真的存在吗？ | 回放时 listener 又收到消息 | 20 min 🟢 |
| A14 | 时间戳与 sim time | `ros2 topic echo /chatter --field header.stamp`；再 `ros2 bag play a --clock` + `--ros-args -p use_sim_time:=true` 看 rviz 是否卡住 | 为什么回放 bag 时 rviz 要开 sim time？ | 说出一个不这么开会出的具体现象 | 20 min 🟢 |
| A15 | 日志分级 | `ros2 run demo_nodes_cpp talker --ros-args --log-level debug` → `ros2 run rqt_console rqt_console` | `printf` 调试在 ROS2 里为什么不够用？ | 说出两条理由（分级/全局收集） | 20 min 🟢 |
| A16 | 一条命令 + 证据留档 | 写 `run.sh`（3 行）+ `README.md`（3 行：怎么起、看到什么、怎么停）+ 一段 bag；第三人按 README 起 | 别人复现失败，通常是哪一步没写？ | 第三人 5 分钟内独立跑通 | 30 min 🟢 |

---

## 表 D｜rqt 全家桶 14 件（约 3 小时，先装后认，全部 🟢）

**安装**：`sudo apt install ros-humble-rqt*`，装完用 `ros2 pkg list | grep rqt` 自查装到了哪些（不同机器上有差异）。

| # | 工具 / 启动 | 作用 | **最重要的现象（一眼看什么）** | 用在哪 | 坑 |
|---|---|---|---|---|---|
| D1 | `rqt_graph` | 画出节点—话题—方向的全局图 | **本该有的边没有 = 话题名不匹配**；死节点变灰 | A2 A3 C6 B2 | 消息量大时节点太多看不清，先勾 hide dead 与 filter |
| D2 | `rqt_topic` | 不写代码就浏览/展开任意话题的字段值与频率 | 勾一个话题 → 看到**字段实时跳动 + Hz 数字**；点 Publish 能直接发 | A5 A6 E3 E4 | 高频大消息（点云）会把界面拖死，先别勾 |
| D3 | `rqt_publisher` | 图形化构造并发布任意消息 | 用滑条发 `/cmd_vel` 让车动，**不用写一行代码** | A6 C4 | 忘了设 rate 会只发一次，新手以为"没反应" |
| D4 | `rqt_service_caller` | 图形化调用服务，自动生成表单 | 列出服务 → 填参数 → 看到**返回值与耗时** | A7 B12 | 服务名带命名空间时容易选错 |
| D5 | `rqt_plot` | 任意数值字段画实时曲线 | 看到**阶跃响应/收敛过程/抖动**；`/odom/.../x` 会爬坡 | A5 E3 F6 | 时间轴不跟随会以为"卡了"；数组要写 `[index]` |
| D6 | `rqt_console` | 汇总所有节点日志，可按级别/节点过滤 | **一条 FATAL 后面必然跟着真因**；节点崩溃前常有 WARN | A15 E2 F11 | 只显示已连上的节点，节点没起来就什么都看不到 |
| D7 | `rqt_bag` | bag 时间轴浏览器：边拖边看图像/曲线/消息 | 拖动时间轴 → **同步看到图像帧和曲线**，回看数据流最快 | A13 F1 F3 C13 | 大 bag 打开慢，先 `ros2 bag info` 看体量 |
| D8 | `rqt_tf_tree` | 实时 TF 树（可刷新） | **树断了 = 某节点没发 tf**；两个父节点指向同一子节点 = 冲突 | A10 A11 C3 B15 | 与 `view_frames` 区别：这个实时刷新，那个是快照 |
| D9 | `rqt_image_view` | 看任意图像话题 | 看到**画面与时间戳**；切话题对比 RGB / depth / 对齐深度 | E5 F7 | 深度图直接看是灰的，需归一化或看对齐后的彩色化 |
| D10 | `rqt_py_console` | 内嵌 Python + rclpy，直接调 API | 界面里 `node.get_topic_names_and_types()` 立刻出结果 | F6 F11 | 与你的代码共用解释器状态，别在这跑长任务 |
| D11 | `rqt_shell` | 内嵌终端 | 一边看图一边敲命令，不用来回切窗口 | 全部 | 别在这跑交互式程序 |
| D12 | `rqt_robot_steering` | 滑条/手柄发 `/cmd_vel` | 拖动滑条 → **车立刻动**，`/cmd_vel` 频率可见 | C12 C14 E7 | 命名空间不同就无效（发的是 `/cmd_vel`） |
| D13 | `rqt_msg` / `rqt_srv` | 浏览消息/服务的完整字段结构 | **嵌套字段一眼展开**，写 yaml 时照着抄 | A7 F4 F7 | 只读，不能改定义 |
| D14 | `rqt_robot_monitor`（诊断） | 汇总 `/diagnostics` 的各设备健康状态 | 一屏看到**哪个设备红了**（雷达/相机/电池） | E1 E8 | 需要驱动发布 diagnostics，很多驱动不发 |

> **隐藏但最实用**：`ros2 run rqt_gui rqt_gui` → 插件 → 勾选要的 → **Perspectives → Save**，把"调试常用四宫格"存成布局，以后一条命令回到同一视图。

> **同级但非 rqt 的四个工具**：`rviz2`（场景可视化，必开）、`plotjuggler`（`ros-humble-plotjuggler-ros`，比 rqt_plot 强）、`foxglove studio`（远程看话题）、`ros2 bag` CLI（F 表主用）。

---

## 表 B｜机械臂（16 条，约 8 小时，12 条 🟢）

| # | 条目 | 具体操作（命令 / 逻辑链） | 探索点 | 判据 | 时长·环境 |
|---|---|---|---|---|---|
| B1 | 跑官方 MoveIt2 demo | `sudo apt install ros-humble-moveit` → `ros2 launch moveit_resources_panda_moveit_config demo.launch.py` → rviz 拖橙色球 → **Plan** → **Execute** | 你没给任何目标数字，它凭什么能规划？ | 看到轨迹动画且末端到位 | 30 min 🟢 |
| B2 | 看 MoveIt 的节点图 | `rqt_graph`，找 `move_group`、rviz、`fake_joint` 等 | 谁在算轨迹？rviz 只是显示器吗？ | 列出 ≥4 个节点及职责 | 20 min 🟢 |
| B3 | 看 URDF 三个要素 | 打开 `panda.urdf`，找 `<joint type="revolute">`、`<axis>`、`<limit>`、`<origin xyz rpy>`；`check_urdf panda.urdf` | `origin` 的 xyz 是相对谁的？ | 能指出连杆链的头和尾 | 30 min 🟢 |
| B4 | 自己的 2-DOF URDF | 写 30 行：base_link → link1（joint1 revolute, axis z, limit ±90°）→ link2；长度只改 0.2/0.15 | 为什么 joint 要写 limit？不写会怎样？ | rviz 里能拖、`view_frames` 有 3 层 | 60 min 🟢 |
| B5 | FK 手算 vs tf2_echo | `x=l1·cosθ1+l2·cos(θ1+θ2)`，`y=l1·sinθ1+l2·sin(θ1+θ2)`；`tf2_echo base_link link2` 对照 θ=(30°,45°) | 你算的和 tf 差多少？差在公式还是参数？ | 误差 <1 mm，并能解释差异来源 | 45 min 🟢 |
| B6 | IK 手算（两解） | `c2=(x²+y²-l1²-l2²)/(2l1l2)` → `θ2=±acos(c2)` → `θ1=atan2(y,x)-atan2(l2·sinθ2, l1+l2·cosθ2)`；10 行 Python 打印两解并按 limit 剔除 | 为什么有两个解？哪个物理上不可达？ | 与 rviz 拖到的位姿一致 | 60 min 🟢 |
| B7 | 用 Marker 画可达空间 | θ1,θ2 ∈[-90°,90°] 步长 5° → 算末端点 → 打包 `visualization_msgs/MarkerArray`(type=POINTS) → 发布 → rviz 加 Marker 显示 | 那个"扇形"的边界由什么决定？ | rviz 出现扇形点云 | 60 min 🟢 |
| B8 | ros2_control 最小链路 | `ros2 launch ros2_control_demo_example_1 rrbot.launch.py` → `ros2 topic echo /joint_states` → `ros2 control list_controllers` | 谁在改 joint 值？控制器与硬件之间隔着什么？ | `/joint_states` 在动 + 控制器 active | 60 min 🟡 |
| B9 | 手动发一条轨迹 | `ros2 action send_goal /joint_trajectory_controller/follow_joint_trajectory control_msgs/action/FollowJointTrajectory "{trajectory:{joint_names:['joint1','joint2'],points:[{positions:[0.5,0.5],time_from_start:{sec:2}}]}}"` | 轨迹里为什么写时间，不写会怎样？ | 关节 2 秒内走到 0.5 | 45 min 🟡 |
| B10 | Plan 与 Execute 分开 | rviz 只点 Plan → `ros2 topic echo /display_planned_path`；再点 Execute | 规划出的轨迹由谁消费？ | 说清"规划=出路径，执行=发轨迹" | 20 min 🟢 |
| B11 | 读 SRDF 三处 | `panda.srdf` 里找 `<group name="panda_arm"><chain base_link tip_link>`、`<virtual_joint>`、`<disable_collisions>` 各一处 | 为什么需要有 disable_collisions？ | 说出三个标签各自作用 | 45 min 🟢 |
| B12 | 加一个碰撞体 | `ros2 service call /apply_planning_scene moveit_msgs/srv/ApplyPlanningScene` 加 box 到路径上，再规划 | 它拒绝是因为算不出来，还是撞了？ | 规划失败/绕开，能说出原因 | 45 min 🟢 |
| B13 | 脚本化一次规划 | 20 行 `moveit_py`：`MoveItPy(node_name=..)` → `get_planning_component('panda_arm')` → `set_goal_state(...)` → `plan()` → `execute()` | 界面上那三下，在代码里是哪三行？ | 脚本跑通，末端到位 | 60 min 🟢 |
| B14 | 末端 TCP 从哪来 | 加固定 joint（tool0）→ `tf2_echo panda_link8 panda_hand` 与 `tf2_echo panda_link8 tool0` 对比 | TCP 为什么常常不等于最后一个 link？ | 说出 TCP 由哪个文件哪一行决定 | 30 min 🟢 |
| B15 | 换成自己的臂并规划 | `moveit_setup_assistant` 载入 B4 的 URDF → 建 group + 虚拟关节 → 生成 config → `ros2 launch my_moveit_config demo.launch.py` | 生成失败时最先看哪个文件？ | 自己的臂能规划一条无碰撞轨迹 | 120 min 🟡 |
| B16 | 改 limit 看后果 | URDF 里 joint2 的 `<limit lower/upper>` 从 ±90° 改到 ±30°，重启，rviz 拖到超界处 | 超界时是模型停住，还是规划器报错？ | 能描述两种表现差别 | 20 min 🟢 |

---

## 表 C｜导航（15 条，约 8 小时，6 条 🟢）

| # | 条目 | 具体操作（命令 / 逻辑链） | 探索点 | 判据 | 时长·环境 |
|---|---|---|---|---|---|
| C1 | 一条命令起全栈 | `export TURTLEBOT3_MODEL=burger` → `ros2 launch nav2_bringup tb3_simulation_launch.py headless:=False`（VMware 慢就 `headless:=True` 只看 rviz） | 这几十个节点里哪几个必须活着？ | rviz 出现地图 + 车 + 激光点 | 30 min 🟡 |
| C2 | 四个输入各是谁发的 | `ros2 topic info -v /map` `/scan` `/odom` `/tf` 四个各看 publisher | 少了其中一个，导航最先崩的是谁？ | 四个发布者名字全部写出 | 30 min 🟢 |
| C3 | TF 树的中间那一层 | `view_frames` → 找 `map → odom` 是谁发布的 | `odom→base_link` 由谁发？两者区别是什么？ | 画出 4 层树并标发布者 | 30 min 🟢 |
| C4 | 给初始位姿 | rviz 点 **2D Pose Estimate**，`ros2 topic echo /amcl_pose` 看粒子云收敛 | 定位不准时，第一个该动的不是地图，是什么？ | 粒子云收成一团 | 20 min 🟡 |
| C5 | 发一个目标点 | rviz 点 **2D Goal Pose**，同时 `ros2 topic echo /plan --field poses` 只看前两行 | 全局路径和局部路径分别是哪个话题？ | 车到达，`/plan` `/local_plan` 都出现 | 30 min 🟡 |
| C6 | cmd_vel 从哪来 | `ros2 topic info /cmd_vel -v` → publisher 是 `controller_server`；再 `rqt_graph` 看上游 | 为什么是控制器发速度，不是规划器？ | 画出 costmap→controller→cmd_vel 链路 | 30 min 🟢 |
| C7 | 改一个 costmap 参数 | `ros2 param get /local_costmap/local_costmap inflation_radius` → `set` 到 0.8 → 重发目标 | 半径调大后车更保守还是更激进？ | 一句话描述行为差异 | 30 min 🟡 |
| C8 | 换规划器插件 | `ros2 param get /planner_server GridBased`（NavFn）→ 改 `SmacPlanner2D` → 重启重发 | 换插件后路径形状变了吗？为什么？ | 说出两者一个差别 | 40 min 🟡 |
| C9 | 看控制器插件 | `ros2 param get /controller_server FollowPath`（DWB）→ 读 `max_vel_x`、`vx_samples` | DWB 是算最优曲线，还是采样一堆再挑？ | 一句话说清采样思想 | 30 min 🟢 |
| C10 | 触发一次恢复行为 | 目标设在墙里/窄门后，`ros2 topic echo /behavior_tree_log`，看原地转/后退 | 它在重规划还是恢复行为？怎么区分？ | 说出恢复行为触发顺序 | 30 min 🟡 |
| C11 | lifecycle 两步走 | `ros2 lifecycle get /controller_server` → 看 inactive；`ros2 lifecycle set /controller_server activate` | 为什么分 configure / activate 两步？ | 说出一个好处（可预加载/可热切） | 20 min 🟢 |
| C12 | 建图→存图→用图 | `ros2 launch slam_toolbox online_async_launch.py` → `ros2 run teleop_twist_keyboard teleop_twist_keyboard` 走一圈 → `ros2 run nav2_map_server map_saver_cli -f mymap` | 建图时谁发 `map→odom`？导航时又是谁？ | 存出 pgm+yaml 且被 map_server 加载 | 60 min 🟡 |
| C13 | 失败场景录一次 | 窄门必失败场景，`ros2 bag record -a -o fail1`（30 秒）→ `ros2 bag play fail1` 复现 | 复现失败时，你的 bag 里少了什么？ | 能复现同一位置卡住 | 45 min 🟡 |
| C14 | 接自己的底盘接口（伪代码） | 订阅 `/cmd_vel` → 取 `vx,vy,wz` → 逆解成 N 个轮速/舵角 → 打包 CAN → 编码器积分成 `/odom` 并发布 `odom→base_link` tf（约 60 行） | 为什么必须底盘侧发 `odom→base_link`？ | 仿真模型或实车按 `cmd_vel` 动起来 | 120 min ⚪ |
| C15 | 差速 vs 舵轮的语义差 | 给 `cmd_vel=(0.2,0,0)` 与 `(0,0.2,0)`，看两种底盘谁能执行；对照 `05_舵轮组/舵轮组_设计规格_一页版.md` | 为什么舵轮能吃 `vy≠0` 而差速不能？ | 说出运动学自由度差异 | 30 min 🟢 |

---

## 表 E｜外设接入（10 条，约 4 小时，多数 ⚪ 需设备）

> 前提：这些设备**已经有跑通的 ROS 包**（串口模块、2D 雷达、深度相机、IMU 经 STM32 转串口发 ROS 格式、FishROS 小车）。所以本表不教驱动原理，只教"**接上、看见、量到、写进清单**"。

| # | 条目 | 具体操作（命令 / 逻辑链） | 探索点 | 判据 | 时长·环境 |
|---|---|---|---|---|---|
| E1 | 先把"设备清单"建起来 | `ls /dev/ttyUSB* /dev/ttyACM*` → `dmesg -T`（看最后几条插入日志）→ `udevadm info -a -n /dev/ttyUSB0`（找 idVendor / idProduct / serial 三项） → 记表：设备 / 驱动包 / 话题 / frame_id / 频率 | 拔掉再插，设备名变了吗？为什么？ | 一张 5 列表格，五台设备都填满 | 40 min ⚪ |
| E2 | 串口权限与固定名 | `sudo usermod -aG dialout $USER`（重登录）→ 写 `/etc/udev/rules.d/99-robot.rules`：`SUBSYSTEM=="tty", ATTRS{idVendor}=="xxxx", MODE:="0666", SYMLINK+="imu"` → `sudo udevadm control --reload && sudo udevadm trigger` | 为什么每次插拔设备名会变？symlink 解决的是什么？ | `/dev/imu` 稳定存在，重启后不变 | 40 min ⚪ |
| E3 | IMU 经 STM32 → ROS 格式 | 链路：IMU 芯片 →(SPI/I2C)→ STM32 →(串口帧)→ 上位机解析节点 → `sensor_msgs/Imu` → `/imu/data_raw`。检查：`ros2 topic hz /imu/data_raw`（应 100–200 Hz）→ `ros2 topic echo /imu/data_raw --field linear_acceleration` → 静置看 z 是否 ≈9.8 | 单位错、轴向错、时间戳错，哪个最容易让你以为"算法不行"？ | 静置 z≈9.8，`view_frames` 里有 imu 的 tf，频率稳定 | 60 min ⚪ |
| E4 | 2D 激光雷达 | `ros2 launch ydlidar_ros2_driver ydlidar_launch.py`（RPLidar 用 `rplidar_ros rplidar_a1_launch.py`）→ `ros2 topic hz /scan`（应 ≈10 Hz）→ `ros2 topic echo /scan --field angle_min --once` → rviz 加 LaserScan，Fixed Frame 设 `laser` | 为什么把 Fixed Frame 设成 `laser` 而不是 `map` 就能看见？ | `/scan` 10 Hz，rviz 能看到墙的轮廓 | 40 min ⚪ |
| E5 | 深度相机（RealSense） | `ros2 launch realsense2_camera rs_launch.py align_depth.enable:=true` → `ros2 topic list`（找以 `/camera` 开头的） → 应有 `/camera/color/image_raw`、`/camera/depth/image_rect_raw`、`/camera/aligned_depth_to_color/image_raw`、`/camera/depth/color/points` | 不开 `align_depth` 时，RGB 和 depth 能直接对齐吗？ | 四个话题都有，`rqt_image_view` 能切着看 | 40 min ⚪ |
| E6 | USB 相机（对照用） | `v4l2-ctl --list-formats-ext -d /dev/video0` → `ros2 run usb_cam usb_cam_node_exe` → `ros2 topic hz /image_raw` | 为什么同一台相机在不同电脑上帧率不一样？ | 出图，频率符合预期（如 30 Hz） | 30 min ⚪ |
| E7 | FishROS 小车全链路 | 起底盘驱动 → `ros2 topic hz /odom` → 用 `rqt_robot_steering` 或 `teleop_twist_keyboard` 发 `/cmd_vel` → `view_frames` 看 `odom→base_link`；再手动推车看 `/odom` 是否变 | 推车时 odom 变，说明谁在工作？编码器还是驱动？ | 车能动、odom 有数、tf 有 `odom→base_link` | 60 min ⚪ |
| E8 | 外设一致性巡检脚本 | 写 `check_dev.sh`：对每个话题 `timeout 3 ros2 topic hz <topic>` → 输出一行 PASS/FAIL | 哪个设备最容易"看起来起了但其实没数据"？ | 一条命令打印 5 个设备的 PASS/FAIL | 40 min ⚪ |
| E9 | 时间戳对齐体检 | 各取一次 `ros2 topic echo /scan --field header.stamp`、`/camera/color/image_raw --field header.stamp`、`/imu/data_raw --field header.stamp` → 比较是否同一时钟源 | 三个设备时间戳差 0.2 s，会让后面的融合/跟踪出什么现象？ | 写出三个差值，并判断是否同一时钟 | 40 min ⚪ |
| E10 | 带宽与降载 | `ros2 topic bw /camera/depth/color/points`（看 MB/s）→ 对比降采样前后；记录"一条 30 秒 bag 多大" | 为什么录 full 点云一小时能占满硬盘？ | 给出三个话题各自的 MB/s 与降载手段 | 30 min ⚪ |

---

## 表 F｜数据、bag 与目标跟踪（12 条，约 7 小时）

> 两条主线：**① 2D 雷达点上的运动物体检测与持续跟踪**；**② 深度相机 RGB+depth 上的单目标持续跟踪**。

| # | 条目 | 具体操作（命令 / 逻辑链 / 伪代码） | 探索点 | 判据 | 时长·环境 |
|---|---|---|---|---|---|
| F1 | bag 体检三连 | `ros2 bag info xxx`（话题/条数/时长/大小）→ `ros2 bag play xxx --topics /scan /odom` 只回放需要的 → 异常时 `ros2 bag reindex` | 为什么回放时"topic 在但没数据"？ | 报出每个话题的条数与频率 | 25 min 🟢 |
| F2 | 用 rqt_bag 回看现象 | `ros2 run rqt_bag rqt_bag` → 加载 bag → 选话题 → 下方开 plot/image → 拖时间轴 | 时间轴上一段"空白"说明什么？ | 截图一张"图像+曲线同步"的证据 | 30 min 🟢 |
| F3 | 从 bag 里逐帧取数据 | 伪代码：`reader = rosbag2_py.SequentialReader()` → `set_filter(topics=['/scan'])` → `open(storage_options, converter_options)` → `while reader.has_next(): topic,data,t = reader.read_next()` → `msg = deserialize(data)`；简单路线：`ros2 bag play` + 自写订阅节点落盘 | 离线处理和在线处理，哪个更适合调算法？ | 反序列化一帧 `/scan` 并打印 ranges 长度 | 45 min 🟢 |
| F4 | LaserScan → 2D 点 | 伪代码：`for i,r in enumerate(msg.ranges):` `if r>msg.range_max or r<msg.range_min: continue` `a = msg.angle_min + i*msg.angle_increment` `pts.append((r*cos(a), r*sin(a)))` | 为什么必须先滤掉 inf / 0？ | 得到与 rviz 形状一致的点集 | 30 min 🟢 |
| F5 | 运动物体检测（帧差法） | 逻辑链：① 多帧取中值 → 背景 ② 当前帧点集与背景做最近邻距离差 ③ 距离 >0.2 m 标为"前景" ④ 按角度窗一维聚类 → 候选簇（中心角、距离、点数） | 静止的人会被判成前景吗？为什么？ | 有物体走过时输出"角度 xx° 距离 x.x m" | 60 min ⚪ |
| F6 | 持续跟踪 + 保持 ID | 逻辑链：① 取 F5 的簇 ② 与上一帧轨迹贪心最近邻匹配（距离 <0.5 m 且角差 <10°）③ 匹配上 → 沿用 ID 并更新速度（卡尔曼 CV：`x=[p,v]`，`p+=v·dt`，`v+=K·(z-p)`）④ 连续 3 帧未匹配 → 删轨迹 | 两个人交叉走过时，ID 为什么会串？ | 连续 10 秒同一物体 ID 不变，输出 ID/位置/速度 | 75 min ⚪ |
| F7 | 深度相机：RGB 框 + depth 取深 | 逻辑链：① `/camera/aligned_depth_to_color/image_raw`（必须先对齐）② RGB 上给 ROI（手画框或 YOLO 框）③ ROI 内 depth 取**中值**（避开飞点）④ 内参反投影 `X=(u-cx)/fx·Z`、`Y=(v-cy)/fy·Z` → 目标 3D 点 | 为什么用中值不用均值？ROI 混进背景会怎样？ | 输出目标 3D 坐标，物体移动时数值跟着动 | 60 min ⚪ |
| F8 | 点云处理四连 | `ros2 topic bw/hz` 看量 → 降采样（open3d `voxel_down_sample(voxel=0.05)` 或 pcl 组件）→ 直通滤波（保留 z∈[0.2,2.0]）→ 欧式聚类得簇；每步 `ros2 topic echo --once` 看点数变化 | 为什么"先降采样再聚类"比反过来快一个量级？ | 点数从几万降到几千，仍能分出目标簇 | 60 min ⚪ |
| F9 | rviz 里把现象看清 | PointCloud2 显示：`Decay Time`=3（看拖影）、`Color Transformer`=Axis（按 z 上色）、点大小 3；激光单独一个 LaserScan display | Decay Time 设大之后你看到了什么？ | 一张能看出"目标在移动"的截图 | 20 min 🟢 |
| F10 | 记录一次跟踪全过程 | `ros2 bag record -o track1 /scan /odom /camera/color/image_raw /camera/aligned_depth_to_color/image_raw`（**只录这四路**）→ 跑一遍场景 → 回放复现 | 为什么 `-a` 录全量会让后期处理变慢？ | 30 秒 bag，四路齐全，体积可控 | 30 min ⚪ |
| F11 | 把"感觉能跟"变成数字 | 建 5 列表：`场景 / 目标数 / 跟踪成功率 / ID 切换次数 / 说明`。跑 5 个场景（单人直走、单人横穿、两人交叉、部分遮挡、快速移动） | 哪个场景最先崩？崩在检测还是匹配？ | 5 行数据，能指出最差场景与原因 | 45 min ⚪ |
| F12 | 最小可交付 Demo | 在 bag 回放上跑 F5+F6（或 F7）→ 用 `visualization_msgs/Marker`（球 + `TEXT_VIEW_FACING` 写 ID）发布 → rviz 看到"跟着动的 ID 标签" | 如果只保留一个指标，你留什么？ | 回放中连续 10 秒不掉 ID | 90 min ⚪ |

---

## 二、推荐部署的开源项目（各 3 个，按"第一次成功率"排序）

### 机械臂

| 项目 | 一条命令 | 学什么 | 坑 / 评价 |
|---|---|---|---|
| **moveit2_tutorials + moveit_resources_panda**（官方） | `ros2 launch moveit_resources_panda_moveit_config demo.launch.py` | 规划组、场景、plan/execute，全在 rviz 里可视化，**交互反馈最好** | 文档分版本（Humble/Jazzy API 有差），照错版本做会卡在 Python 接口。**综合最推荐** |
| **ros2_control_demos**（ros-controls） | `ros2 launch ros2_control_demo_example_1 rrbot.launch.py` | hardware_interface → controller_manager → `/joint_states` 全链路，example_7 直接接 MoveIt | 部分 example 依赖 Gazebo；`example_1/3` 用 fake 硬件纯 rviz 可跑。**理解控制链最推荐** |
| **Universal Robots ROS2**（`ur_simulation_gz` + `Universal_Robots_ROS2_Description`） | `ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:=ur5e` | 工业级包结构（description / driver / moveit_config 分层） | 依赖多、Gazebo 吃资源，第一次装成功率偏低。**放第二轮** |

> 备选（非 ROS2 中心）：**SO-ARM100 / LeRobot** —— 低成本实体臂 + 现成 URDF 与遥操作；以 Python 为主，接 ROS2 要自己搭桥。**先知道有它，别现在上。**

### 导航

| 项目 | 一条命令 | 学什么 | 坑 / 评价 |
|---|---|---|---|
| **FishROS fishbot**（你们已有该小车） | `ros2 launch fishbot_navigation2 navigation2.launch.py`（按其文档） | 中文文档完整、仿真/实车都有、**VMware 友好**，建图→导航全闭环 | 生态小、地图与参数要按自家车改。**第一次成功率最高，优先用它跑通闭环** |
| **turtlebot3 + nav2_bringup**（官方） | `ros2 launch nav2_bringup tb3_simulation_launch.py` | map/AMCL/planner/controller/BT 全栈标准配置，社区答案最多 | Gazebo 在 VMware 上卡；建议 `headless:=True` 只看 rviz，或到 402 真机做 |
| **slam_toolbox**（SteveMacenski） | `ros2 launch slam_toolbox online_async_launch.py` | 建图→存图→导航闭环，与 Nav2 天然配套 | 需要 `/scan` 与 odom；`use_sim_time` 忘开会白干一小时 |

### 跟踪 / 感知（新增，配合表 F）

| 项目 | 用途 | 评价 |
|---|---|---|
| **YOLOv8 / ultralytics** | 给 F7 提供 ROI，比手画框稳定 | 只推理不训练；CPU 慢，先降分辨率 |
| **`vision_msgs` + 自写节点** | 把检测结果标准化成 `Detection2DArray`，便于跨节点对接 | 结构统一；生态小，先发 Marker 也算合格 |
| **open3d / `pcl_ros`** | F8 点云四连 | open3d 在 Python 里最快出结果；pcl 组件适合做成常驻节点 |

---

## 三、怎么用这六张表（不给新人自由发挥）

**四轮结构，一轮一件事：**

| 轮 | 内容 | 时长 | 通过标准 |
|---|---|---|---|
| 第 1 轮 认知 | A1–A6 + A12 + A13 + **D1–D6** | 约 3 h | 能说出"消息从哪来、被谁消费" |
| 第 2 轮 外设 | **E1–E8**（对着真设备，含 FishROS 车） | 约 4 h | 五台设备各有"话题/频率/frame"一行记录 |
| 第 3 轮 数据 | **D7** + **F1–F6** 或 **F7–F9**（二选一） | 约 5 h | 一段 bag 上跑出"ID 不变"的输出 |
| 第 4 轮 方向 | **B1–B10** 或 **C1–C12**（一人只碰一条） | 约 8 h | 一条链路能自己复现 |

**三条纪律**：① 每条 15–30 分钟，超时跳过并记录"跳过"，不许硬修；② 验收只问三个问题（你看到的链路是什么？失败先看哪个话题？和你想的差在哪？）；③ 一轮只挑 10–12 条，不追求全做。

**总时长**：约 20 小时 = 每周 6–8 小时 × 3 周。

---

## 四、一句话

> 这一轮不是"教会 ROS2"，是让每个人**亲手看见一次链路**：消息从哪来、被谁消费、坏了看哪里。
> 所以每条都必须短、必须能一条命令起、必须允许跳过——**深度这一轮不要，成功率这一轮要高**。
